from actions.action import FinishAction
from agents.loop_state import LoopState
from core.task_result import TaskResult


class CodeAgent:

    def __init__(self, planner, executor, critic_agent, max_steps: int = 10):
        self.planner = planner
        self.executor = executor
        self.max_steps = max_steps
        self._critic_agent = critic_agent
        self._max_reflections = 3

    async def run(self, task, context) -> TaskResult:

        loop_state = LoopState()

        # observation = None

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

            loop_state.last_action = action

            if isinstance(action, FinishAction):

                loop_state.finished = True

                return TaskResult(
                    success=True,
                    answer=action.answer
                )

            observation = await self.executor.execute(action)

            loop_state.observation_history.append(observation)

            loop_state.last_action = action

            loop_state.last_observation = observation

            loop_state.step_count += 1

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

                context.reflections.reflections.append(reflection)

                loop_state.reflection_count += 1

                continue