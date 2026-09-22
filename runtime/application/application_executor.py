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
from runtime.orchestration import (
    Orchestrator,
    SingleAgentOrchestrator,
)


class ApplicationExecutor:
    """
    Internal execution adapter for AgentApplication.

    Responsibilities:
        - create the logical Execution object
        - persist ExecutionState
        - persist TaskRequest
        - create ExecutionHandle through ExecutionRuntime
        - delegate normal execution to Orchestrator
        - reconstruct durable Execution during recovery
        - reconstruct TaskRequest during recovery
        - delegate recovery to Orchestrator
        - close ExecutionHandle after execution

    ApplicationExecutor does NOT own:

        - Checkpoint persistence
        - AgentContext
        - MemoryRuntime
        - AgentRuntime implementation
        - Workflow decisions
        - concrete Agent orchestration logic

    The Orchestrator owns orchestration decisions.

    Execution remains the logical execution object.

    ExecutionHandle remains the live runtime handle.
    """

    def __init__(
        self,
        application,
        execution_runtime: ExecutionRuntime,
        orchestrator: Orchestrator | None = None,
    ) -> None:
        self._application = application
        self._execution_runtime = execution_runtime

        self._orchestrator = orchestrator or SingleAgentOrchestrator(
            application=application,
        )

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
            Orchestration Entry Agent
                ↓
            Execution
                ↓
            ExecutionStore
                ↓
            ExecutionRuntime
                ↓
            Orchestrator
                ↓
            AgentRuntime

        The orchestration entry Agent identity is persisted in
        Execution.metadata before the live execution starts.

        This allows Recovery to reconstruct the same orchestration
        entry point without selecting a new default Agent.
        """

        await self._persist_task(task)

        entry_agent = self._orchestrator.resolve_entry_agent()

        execution = self._create_execution(
            task=task,
            entry_agent_id=entry_agent.identity.agent_id,
        )

        await self._persist_execution(execution)

        execution_handle = self._execution_runtime.create_execution(execution)

        try:
            execution.start()

            await self._persist_execution(execution)

            orchestration_result = await self._orchestrator.execute(
                task=task,
                execution_handle=execution_handle,
            )

            result = self._to_task_result(
                task=task,
                agent=orchestration_result.agent,
                agent_result=orchestration_result.agent_result,
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
            checkpoint: Checkpoint,
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
                "Checkpoint runtime_id does not match Execution "
                f"runtime_id: execution={execution_handle.runtime_id}, "
                f"checkpoint={checkpoint.runtime_id}"
            )

        await self._application.checkpoint_store.save(
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint=checkpoint,
        )

        execution.set_checkpoint(checkpoint_id=checkpoint.checkpoint_id)

        await self._persist_execution(execution)

    async def recover_execution(
            self,
            checkpoint: Checkpoint,
    ) -> ExecutionHandle:
        """
        Recover a low-level ExecutionHandle directly from a Checkpoint.

        This method is intentionally retained as a low-level compatibility
        API.

        It does NOT represent durable Application-level recovery because
        the Checkpoint alone does not contain the logical Execution ID.
        """

        execution = self._create_execution_from_checkpoint(checkpoint)

        return self._execution_runtime.resume_execution(
            execution=execution,
            checkpoint=checkpoint
        )

    async def recover_persisted_execution(self,execution_id: str) -> ExecutionHandle:
        """
        Reconstruct a live ExecutionHandle from durable state.

        This method restores:

            ExecutionState
                ↓
            Execution
                ↓
            Checkpoint
                ↓
            RuntimeContext

        It does not execute the orchestration.

        The returned handle is owned by the caller.
        """
        execution = await self._load_persisted_execution(execution_id)

        checkpoint = await self._load_execution_checkpoint(execution)

        return self._execution_runtime.resume_execution(
            execution=execution,
            checkpoint=checkpoint,
        )

    async def resume_persisted_execution(
        self,
        execution_id: str,
    ) -> TaskResult:
        """
        Resume a durable Application Execution.

        Recovery flow:

            ExecutionStore
                ↓
            Execution
                ↓
            TaskStore
                ↓
            TaskRequest
                ↓
            CheckpointStore
                ↓
            Checkpoint
                ↓
            ExecutionRuntime
                ↓
            Orchestrator.resume()
                ↓
            AgentRuntime
                ↓
            TaskResult

        The orchestration entry Agent is recovered from
        Execution.metadata["orchestrator_agent_id"].

        Recovery never selects a new default Agent.
        """

        execution = await self._load_persisted_execution(
            execution_id
        )

        task = await self._load_execution_task(
            execution
        )

        checkpoint = await self._load_execution_checkpoint(
            execution
        )

        entry_agent_id = execution.metadata.get(
            SingleAgentOrchestrator.ENTRY_AGENT_METADATA_KEY
        )

        if not entry_agent_id:
            raise ApplicationLifecycleError(
                "Persisted Execution does not contain an "
                "orchestration entry Agent: "
                f"{execution.execution_id}"
            )

        if entry_agent_id not in checkpoint.agents:
            raise ApplicationLifecycleError(
                "Checkpoint does not contain the persisted "
                "orchestration entry Agent: "
                f"{entry_agent_id}"
            )

        if execution.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }:
            raise ApplicationLifecycleError(
                "Cannot resume a terminal Execution: "
                f"{execution.execution_id}, "
                f"status={execution.status.value}"
            )

        execution_handle = self._execution_runtime.resume_execution(
            execution=execution,
            checkpoint=checkpoint,
        )

        try:
            if execution.status == ExecutionStatus.PAUSED:
                execution.resume()
                await self._persist_execution(execution)

            elif execution.status != ExecutionStatus.RUNNING:
                raise ApplicationLifecycleError(
                    "Execution is not resumable: "
                    f"{execution.execution_id}, "
                    f"status={execution.status.value}"
                )

            orchestration_result = await self._orchestrator.resume(
                task=task,
                execution_handle=execution_handle,
                checkpoint=checkpoint,
                entry_agent_id=str(entry_agent_id),
            )

            result = self._to_task_result(
                task=task,
                agent=orchestration_result.agent,
                agent_result=orchestration_result.agent_result,
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

    async def recover_agent_execution(
        self,
        checkpoint: Checkpoint,
        agent_id: str,
        task: TaskRequest,
    ) -> AgentResult:
        """
        Resume one Agent directly from a Checkpoint.

        This remains a low-level compatibility API.

        Durable Application recovery should use
        resume_persisted_execution().
        """

        execution_handle = await self.recover_execution(
            checkpoint=checkpoint,
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

    async def _load_persisted_execution(
        self,
        execution_id: str,
    ) -> Execution:
        state = await self._application.execution_store.load(
            execution_id
        )

        if state is None:
            raise ApplicationLifecycleError(
                f"Execution not found: {execution_id}"
            )

        execution = Execution.from_state(state)

        if execution.current_checkpoint_id is None:
            raise ApplicationLifecycleError(
                "Execution does not have a recovery checkpoint: "
                f"{execution_id}"
            )

        return execution

    async def _load_execution_task(
        self,
        execution: Execution,
    ) -> TaskRequest:
        if execution.task_id is None:
            raise ApplicationLifecycleError(
                "Execution does not contain a task_id: "
                f"{execution.execution_id}"
            )

        task = await self._application.task_store.load(
            execution.task_id
        )

        if task is None:
            raise ApplicationLifecycleError(
                "Task not found for Execution: "
                f"execution={execution.execution_id}, "
                f"task={execution.task_id}"
            )

        if task.task_id != execution.task_id:
            raise ApplicationLifecycleError(
                "Loaded TaskRequest does not match Execution task_id: "
                f"execution={execution.task_id}, "
                f"task={task.task_id}"
            )

        return task

    async def _load_execution_checkpoint(
        self,
        execution: Execution,
    ) -> Checkpoint:
        checkpoint_id = execution.current_checkpoint_id

        if checkpoint_id is None:
            raise ApplicationLifecycleError(
                "Execution does not have a recovery checkpoint: "
                f"{execution.execution_id}"
            )

        checkpoint = await self._application.checkpoint_store.load(
            checkpoint_id
        )

        if checkpoint is None:
            raise ApplicationLifecycleError(
                "Checkpoint not found for Execution: "
                f"{execution.execution_id}: {checkpoint_id}"
            )

        if (
            checkpoint.task_id is not None
            and checkpoint.task_id != execution.task_id
        ):
            raise ApplicationLifecycleError(
                "Checkpoint task_id does not match Execution task_id: "
                f"execution={execution.task_id}, "
                f"checkpoint={checkpoint.task_id}"
            )

        return checkpoint

    def _create_execution(
        self,
        task: TaskRequest,
        entry_agent_id: str,
    ) -> Execution:
        """
        Create the logical Execution object.

        The orchestration entry Agent identity is part of durable
        Execution metadata.

        It is deliberately NOT stored in Checkpoint.
        """

        return Execution(
            execution_id=str(uuid4()),
            task_id=task.task_id,
            session_id=task.session_id,
            metadata={
                SingleAgentOrchestrator.ENTRY_AGENT_METADATA_KEY:
                    entry_agent_id,
            },
        )

    def _create_execution_from_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> Execution:
        """
        Deprecated low-level recovery helper.

        A direct Checkpoint does not contain the logical Execution
        identity, therefore this method creates a synthetic Execution.

        Application-level recovery must use
        resume_persisted_execution().
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