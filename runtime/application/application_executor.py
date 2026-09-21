from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agents import AgentResult
from agents.base_agent import BaseAgent
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.application.application_lifecycle import (
    ApplicationLifecycleError,
)
from runtime.checkpoint import Checkpoint
from runtime.execution import ExecutionHandle
from runtime.execution.execution_runtime import ExecutionRuntime
from runtime.execution.execution import Execution
from runtime.execution.execution_state import ExecutionState
from runtime.execution.execution_state import ExecutionStatus


class ApplicationExecutor:
    """
    Internal execution adapter for AgentApplication.

    This class hides low-level execution lifecycle details from the
    public Application API.

    Responsibilities:
        - create the logical Execution object
        - persist ExecutionState
        - create ExecutionHandle through ExecutionRuntime
        - recover ExecutionHandle from Checkpoint
        - resume a specific Agent execution from Checkpoint
        - close ExecutionHandle after normal execution

    ApplicationExecutor does NOT own:

        - Checkpoint persistence
        - AgentContext
        - MemoryRuntime
        - Agent scheduling
        - Workflow decisions

    Execution is the logical execution object.

    ExecutionHandle remains the live runtime handle created by
    ExecutionRuntime.
    """

    def __init__(
        self,
        application,
        execution_runtime: ExecutionRuntime,
    ) -> None:
        self._application = application
        self._execution_runtime = execution_runtime

    async def execute(
        self,
        task: TaskRequest,
    ) -> TaskResult:
        """
        Execute a new Application task.

        Durable initialization order:

            TaskRequest
                ↓
            TaskStore
                ↓
            Execution
                ↓
            ExecutionStore

        Execution lifecycle:

            CREATED
                ↓
            RUNNING
                ↓
            COMPLETED

        When Agent execution fails:

            CREATED
                ↓
            RUNNING
                ↓
            FAILED

        The logical Execution and its durable state are independent
        from the live ExecutionHandle.
        """
        await self._persist_task(task)

        execution = self._create_execution(task)

        await self._persist_execution(execution)

        execution_handle = self._execution_runtime.create_execution(execution)

        try:
            execution.start()

            await self._persist_execution(execution)

            agent = self._select_default_agent()

            agent_result = await self._application.invoke_agent(
                agent_id=agent.identity.agent_id,
                task=task,
                execution_handle=execution_handle,
            )

            result = self._to_task_result(
                task,
                agent,
                agent_result,
            )

            execution.complete()

            await self._persist_execution(execution)

            return result

        except BaseException:
            if not execution.is_terminal:
                execution.fail()

                await self._persist_execution(execution)

            raise

        finally:
            await execution_handle.close()

    async def persist_checkpoint(
            self,
            execution_handle: ExecutionHandle,
            checkpoint: Checkpoint
    ) -> None:
        """
        Persist a Checkpoint and bind it to its logical Execution.

        Persistence order:

            CheckpointStore.save()
                    ↓
            Execution.set_checkpoint()
                    ↓
            ExecutionStore.save()

        The checkpoint is persisted before the Execution references it.
        """
        execution = execution_handle.execution
        if checkpoint.task_id is not None:
            if checkpoint.task_id != execution.task_id:
                raise ApplicationLifecycleError(
                    "Checkpoint task_id does not match Execution task_id: "
                    f"execution={execution.task_id}, "
                    f"checkpoint={checkpoint.task_id}"
                )

        if checkpoint.runtime_id != execution_handle.runtime_id:
            raise ApplicationLifecycleError(
                "Checkpoint runtime_id does not match Execution runtime_id: "
                f"execution={execution_handle.runtime_id}, "
                f"checkpoint={checkpoint.runtime_id}"
            )

        await self._application.checkpoint_store.save(
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint=checkpoint
        )

        execution.set_checkpoint(checkpoint_id=checkpoint.checkpoint_id)

        await self._persist_execution(execution)

    async def recover_execution(
            self,
            checkpoint: Checkpoint,
    ) -> ExecutionHandle:
        """
        Recover an existing Execution from a Checkpoint.

        This method reconstructs the ExecutionHandle but does not
        execute an Agent.

        The caller owns the returned handle and is responsible
        for closing it.

        This is the low-level Application recovery primitive.
        """
        execution = self._create_execution_from_checkpoint(checkpoint)
        return self._execution_runtime.resume_execution(
            execution=execution,
            checkpoint=checkpoint
        )

    async def recover_persisted_execution(self, execution_id: str) -> ExecutionHandle:
        """
        Recover an Execution from durable ExecutionState and its
        persisted Checkpoint.

        The TaskRequest is intentionally not reconstructed here yet.

        TaskStore is now responsible for durable TaskRequest storage,
        while Task reconstruction and Agent resumption will be completed
        in the subsequent recovery integration lesson.
        """
        state = await self._application.execution_store.load(execution_id)

        if state is None:
            raise ApplicationLifecycleError(
                f"Execution not found: {execution_id}"
            )

        execution = Execution.from_state(state)

        checkpoint_id = execution.current_checkpoint_id

        if checkpoint_id is None:
            raise ApplicationLifecycleError(
                f"Execution does not have a recovery checkpoint: {execution_id}"
            )

        checkpoint = await self._application.checkpoint_store.load(checkpoint_id)

        if checkpoint is None:
            raise ApplicationLifecycleError(
                f"Checkpoint not found for Execution {execution_id}: {checkpoint_id}"
            )

        if (checkpoint.task_id is not None
                and checkpoint.task_id != execution.task_id):
            raise ApplicationLifecycleError(
                "Checkpoint task_id does not match Execution task_id: "
                f"execution={execution.task_id}, "
                f"checkpoint={checkpoint.task_id}"
            )

        return self._execution_runtime.resume_execution(
            execution=execution,
            checkpoint=checkpoint
        )

    async def recover_agent_execution(
            self,
            checkpoint: Checkpoint,
            agent_id: str,
            task: TaskRequest,
    ) -> AgentResult:
        """
        Resume one Agent execution from a Checkpoint.
        """

        execution_handle = await self.recover_execution(
            checkpoint=checkpoint
        )

        try:
            agent = self._application.get_agent(agent_id)

            agent_checkpoint = checkpoint.agents.get(
                agent.identity.agent_id
            )

            if agent_checkpoint is None:
                raise ApplicationLifecycleError(
                    "Checkpoint does not contain an AgentCheckpoint "
                    f"for Agent: {agent_id}"
                )

            agent_execution_context = (
                self._application.agent_runtime.restore_execution_context(
                    runtime_context=execution_handle.runtime_context,
                    agent=agent,
                    checkpoint=agent_checkpoint,
                )
            )

            return await self._application.agent_runtime.execute(
                agent,
                task,
                execution_handle.runtime_context,
                agent_execution_context,
            )
        finally:
            await execution_handle.close()

    def _create_execution(
            self,
            task: TaskRequest,
    ) -> Execution:
        """
        Create the logical Execution object.

        Execution is reconstructed from its durable initial state.

        The logical Execution identity is independent from the
        RuntimeContext.runtime_id owned by ExecutionRuntime.
        """
        return Execution(
            execution_id=str(uuid4()),
            task_id=task.task_id,
            session_id=task.session_id,
        )

    def _create_execution_from_checkpoint(self, checkpoint: Checkpoint) -> Execution:
        """
        Deprecated low-level recovery helper.

        This path exists for direct Checkpoint recovery.

        Full TaskRequest reconstruction belongs to the durable
        recovery path and will use TaskStore.
        """
        now = datetime.now(timezone.utc)

        state = ExecutionState(
            execution_id=str(uuid4()),
            status=ExecutionStatus.PAUSED,
            task_id=checkpoint.task_id,
            created_at=now,
            updated_at=now,
        )

        return Execution.from_state(state)

    async def _persist_execution(
            self,
            execution: Execution,
    ) -> None:
        """
        Persist the durable representation of a logical Execution.

        The Persistence layer receives ExecutionState only.
        """
        await self._application.execution_store.save(
            execution.snapshot()
        )

    async def _persist_task(
            self,
            task: TaskRequest,
    ) -> None:
        """
        Persist the durable input of the logical Execution.
        """
        await self._application.task_store.save(task)

    def _select_default_agent(self) -> BaseAgent:
        agents = self._application.agents

        if not agents:
            raise ApplicationLifecycleError(
                "Application cannot execute a task because no Agent "
                "is registered."
            )

        if len(agents) > 1:
            raise ApplicationLifecycleError(
                "Application cannot select a default Agent because "
                "multiple Agents are registered."
            )

        return agents[0]

    def _to_task_result(
            self,
            task: TaskRequest,
            agent: BaseAgent,
            agent_result: AgentResult,
    ) -> TaskResult:
        return TaskResult(
            success=agent_result.success,
            answer=agent_result.output or "",
            metadata={
                "task_id": task.task_id,
                "agent_id": agent.identity.agent_id,
                "agent_type": agent.identity.agent_type,
            },
        )