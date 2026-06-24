from actions.action import FinishAction
from agents.loop_state import LoopState
from core.task_result import TaskResult


class CodeAgent:

    def __init__(self, planner, executor, max_steps: int = 10):
        self.planner = planner
        self.executor = executor
        self.max_steps = max_steps

    async def run(self, task, context) -> TaskResult:

        loop_state = LoopState()

        observation = None

        while True:

            if loop_state.step_count >= self.max_steps:
                return TaskResult(
                    success=False,
                    observation="Max steps reached"
                )

            action = await self.planner.plan(task, context, observation)

            loop_state.last_action = action

            if isinstance(action, FinishAction):

                loop_state.finished = True

                return TaskResult(
                    success=True,
                    answer=action.answer
                )

            observation = await self.executor.execute(action)

            loop_state.last_observation = observation

            loop_state.step_count += 1