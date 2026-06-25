from actions.action import FinishAction
from agents import loop_state
from agents.loop_state import LoopState
from checkpoint import CheckpointStore, Checkpoint
from context.context_state import ContextState
from core.task_request import TaskRequest
from core.task_result import TaskResult


class CodeAgent:

    def __init__(self, planner, executor, critic_agent, checkpoint_store: CheckpointStore = None):
        self.planner = planner
        self.executor = executor
        self.max_steps = 10
        self._critic_agent = critic_agent
        self._max_reflections = 3
        self._checkpoint_store = checkpoint_store

    async def run(self, task, context) -> TaskResult:

        loop_state = LoopState()

        return await self._run_loop(task, context, loop_state)


    async def _run_loop(self,
                        task: TaskRequest,
                        context: ContextState,
                        loop_state: LoopState
                        ) -> TaskResult:
        while True:

            if loop_state.step_count >= self.max_steps:
                return TaskResult(
                    success=False,
                    observation="Max steps reached"
                )

            last_observation = (
                loop_state.observation_history[-1]
                if loop_state.observation_history
                else None
            )

            action = await self.planner.plan(task, context, last_observation)

            if isinstance(action, FinishAction):
                loop_state.last_action = action

                # Save checkpoint
                await self._save_checkpoint(task, context, loop_state)

                return TaskResult(
                    success=True,
                    answer=action.answer
                )

            observation = await self.executor.execute(action)

            loop_state.observation_history.append(observation)

            loop_state.last_action = action

            loop_state.step_count += 1

            # Save checkpoint
            await self._save_checkpoint(task, context, loop_state)

            if not observation.success:

                if loop_state.reflection_count >= self._max_reflections:
                    return TaskResult(
                        success=False,
                        observation=(
                            f"Max reflections exceeded "
                            f"({self._max_reflections})"
                        )
                    )

                reflection = await self._critic_agent.reflect(
                    loop_state.observation_history
                )

                context.reflections_state.reflections.append(reflection)

                loop_state.reflection_count += 1

                # Save checkpoint
                await self._save_checkpoint(task, context, loop_state)

                continue

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

    async def resume(self, checkpoint: Checkpoint) -> TaskResult:
        if isinstance(checkpoint.loop_state.last_action, FinishAction):

            return TaskResult(
                success=True,
                answer=checkpoint.loop_state.last_action.answer
            )

        return await self._run_loop(
            checkpoint.task_request,
            checkpoint.context_state,
            checkpoint.loop_state
        )