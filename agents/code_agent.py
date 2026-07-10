import uuid
from datetime import datetime, timezone
from typing import TypeVar, Any, Callable, Awaitable

from actions.observation import Observation
from models.action import FinishAction
from runtime.component import RuntimeComponent
from runtime.context.context_state import ContextState
from runtime.context.runtime_context import RuntimeContext
from runtime.loop.loop_state import LoopState
from runtime.checkpoint import CheckpointStore, Checkpoint
from models.task_request import TaskRequest
from models.task_result import TaskResult
from runtime.middleware.middleware_chain import MiddlewareChain
from runtime.middleware.runtime_operation import RuntimeOperation
from runtime.tracing.trace import Trace
from runtime.tracing.trace_context import TraceContext
from runtime.tracing.trace_recorder import TraceRecorder

T = TypeVar("T")

class CodeAgent(RuntimeComponent):

    def __init__(self, planner, executor, critic_agent, checkpoint_store: CheckpointStore = None,
                 middleware_chain: MiddlewareChain | None = None):
        super().__init__(middleware_chain)

        self.planner = planner
        self.executor = executor
        self.max_steps = 10
        self._critic_agent = critic_agent
        self._max_reflections = 3
        self._checkpoint_store = checkpoint_store

        self.last_runtime_context: RuntimeContext | None = None

    async def run(self, task, runtime_context: RuntimeContext) -> TaskResult | None:

        self.last_runtime_context = runtime_context

        return await self._run_loop(task, runtime_context)

    async def _run_loop(self,
                        task: TaskRequest,
                        runtime_context: RuntimeContext
                        ) -> TaskResult | None:

        context = runtime_context.state
        loop_state = runtime_context.loop

        while True:

            if loop_state.step_count >= self.max_steps:
                return TaskResult(
                    success=False,
                    answer="Max steps reached"
                )

            last_observation = (
                loop_state.observation_history[-1]
                if loop_state.observation_history
                else None
            )
            try:
                action = await self.invoke(
                    RuntimeOperation(
                        name="planner.plan",
                        component="planner",
                        metadata={}
                    ),
                    runtime_context,
                    self.planner.plan,
                    task,
                    runtime_context,
                    last_observation
                )
            except Exception as e:
                return TaskResult(
                    success=False,
                    answer=f"Planner failed: {e}"
                )

            if isinstance(action, FinishAction):
                loop_state.last_action = action

                # Save checkpoint
                await self._save_checkpoint(task, context, loop_state)

                return TaskResult(
                    success=True,
                    answer=action.answer
                )

            try:
                observation = await self.invoke(
                    RuntimeOperation(
                        name="tool.execute",
                        component="executor",
                        metadata={}
                    ),
                    runtime_context,
                    self.executor.execute,
                    action,
                    runtime_context
                )
            except Exception as e:
                observation = Observation(success=False, content=str(e))

            loop_state.observation_history.append(observation)

            loop_state.last_action = action

            loop_state.step_count += 1

            # Save checkpoint
            await self._save_checkpoint(task, context, loop_state)

            # Tool Success
            if observation.success:
                continue

            # Tool Failure
            if loop_state.reflection_count >= self._max_reflections:
                return TaskResult(
                    success=False,
                    answer=(
                        f"Max reflections exceeded "
                        f"({self._max_reflections})"
                    )
                )

            try:
                reflection = await self.invoke(
                    RuntimeOperation(
                        name="reflection.reflect",
                        component="critic",
                        metadata={}
                    ),
                    runtime_context,
                    self._critic_agent.reflect,
                    loop_state.observation_history
                )
            except Exception as e:
                reflection = None

            if reflection:
                context.reflections_state.reflections.append(reflection)
                loop_state.reflection_count += 1

            # Save checkpoint
            await self._save_checkpoint(task, context, loop_state)

    async def resume(self, checkpoint: Checkpoint) -> TaskResult | None:
        if isinstance(checkpoint.loop_state.last_action, FinishAction):

            return TaskResult(
                success=True,
                answer=checkpoint.loop_state.last_action.answer
            )

        runtime_context = self._create_runtime_context(
            checkpoint.context_state,
            checkpoint.loop_state,
        )

        return await self._run_loop(
            checkpoint.task_request,
            runtime_context
        )

    async def _save_checkpoint(self,
                               task_request: TaskRequest,
                               context_state: ContextState,
                               loop_state: LoopState
                               ) -> None:
        if self._checkpoint_store is None:
            return

        checkpoint = Checkpoint(
            task_request=task_request,
            context_state=context_state,
            loop_state=loop_state,
        )
        await self._checkpoint_store.save(task_request.task_id, checkpoint)

    def _create_runtime_context(self, context: ContextState, loop_state: LoopState) -> RuntimeContext:
        trace = Trace(trace_id=str(uuid.uuid4()), start_time=datetime.now(timezone.utc))

        trace_context = TraceContext(recorder=TraceRecorder(), trace=trace)

        return RuntimeContext(
            state=context,
            trace=trace_context,
            loop=loop_state
        )
