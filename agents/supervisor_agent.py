from __future__ import annotations

from actions.observation import Observation
from agents import BaseAgent, AgentResult
from agents.identity import AgentIdentity
from agents.research.research_agent import ResearchAgent
from models.task_request import TaskRequest
from providers.llm_provider import LLMProvider
from providers.prompt_message import PromptMessage
from runtime.context import AgentExecutionContext
from runtime.execution import AgentRuntime


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent.

    Supervisor is responsible for deciding which Agent
    should participate in the current task.

    Responsibilities:
        - understand the overall user task
        - decide Agent invocation
        - invoke Agents through AgentRuntime
        - inspect AgentResult
        - decide whether to continue or finish

    It does NOT:
        - execute Tools directly
        - execute ResearchAgent directly
        - manage Middleware
        - manage Tracing
        - manage AgentExecutionContext
        - manage Agent lifecycle

    Agent execution is delegated to AgentRuntime.
    """
    def __init__(
            self,
            identity: AgentIdentity,
            agent_runtime: AgentRuntime,
            research_agent: ResearchAgent,
            llm_provider: LLMProvider
    ) -> None:
        super().__init__(identity)

        self._agent_runtime = agent_runtime
        self._research_agent = research_agent
        self._llm_provider = llm_provider

    async def run(
            self,
            task: TaskRequest,
            agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        """
        Execute one Supervisor task.

        The Supervisor repeatedly decides whether another
        Agent should be invoked or whether the overall task
        can be completed.

        The Supervisor owns the orchestration decision.

        AgentRuntime owns the actual Agent invocation.
        """

        max_steps = 5

        while agent_execution_context.loop.step_count < max_steps:

            agent_execution_context.loop.step_count += 1

            decision = await self._decide_next_action(
                task,
                agent_execution_context,
            )

            if decision == "final":
                return self._build_final_result(
                    task,
                    agent_execution_context,
                )

            if decision == "research":
                result = await self._agent_runtime.execute(
                    agent=self._research_agent,
                    task=task,
                    runtime_context=agent_execution_context.runtime_context,
                )

                observation = self._create_agent_observation(
                    result
                )

                agent_execution_context.loop.observation_history.append(
                    observation
                )

                if not result.success:
                    return AgentResult(
                        success=False,
                        output=None,
                        observations=[
                            observation
                        ],
                        metadata={
                            "agent_id": self.identity.agent_id,
                            "agent_type": self.identity.agent_type,
                            "delegated_agent": (
                                self._research_agent.identity.agent_id
                            ),
                        },
                    )

                continue

            raise RuntimeError(
                f"Unsupported Supervisor decision: {decision}"
            )

        raise RuntimeError(
            "SupervisorAgent exceeded maximum execution steps."
        )

    async def _decide_next_action(
            self,
            task: TaskRequest,
            agent_execution_context: AgentExecutionContext
    ) -> str:
        """
        Decide which downstream Agent should execute next.

        The LLM only produces a decision.
        Supervisor validates the decision before execution.
        """
        messages = [
            PromptMessage(
                role="system",
                content=(
                    "You are a Supervisor Agent.\n"
                    "\n"
                    "Your responsibility is to coordinate "
                    "downstream Agents to complete the user task.\n"
                    "\n"
                    "Available decisions:\n"
                    "\n"
                    "research\n"
                    "Invoke ResearchAgent to perform investment research.\n"
                    "\n"
                    "final\n"
                    "The available research information is sufficient "
                    "to complete the current task.\n"
                    "\n"
                    "Important:\n"
                    "You may choose research multiple times if additional "
                    "research is necessary.\n"
                    "\n"
                    "Return exactly one of:\n"
                    "research\n"
                    "final"
                )
            ),
            PromptMessage(
                role="user",
                content=(
                    f"User task:\n{task.user_input}\n\n"
                    f"Previous Supervisor observations:\n"
                    f"{self._format_observations(agent_execution_context)}"
                ),
            ),
        ]

        response = await self._llm_provider.generate(messages)

        return self._validate_decision(response.content)

    @staticmethod
    def _validate_decision(content: str) -> str:
        """
        Validate an LLM-generated Supervisor decision.
        """

        decision = content.strip()

        allowed_decisions = {
            "research",
            "final",
        }

        if decision not in allowed_decisions:
            raise ValueError(
                f"Unsupported Supervisor decision: {decision}"
            )

        return decision

    @staticmethod
    def _format_observations(
        agent_execution_context: AgentExecutionContext,
    ) -> str:
        """
        Format observations collected during this
        Supervisor execution.
        """

        observations = agent_execution_context.loop.observation_history

        if not observations:
            return "None"

        lines: list[str] = []

        for index, observation in enumerate(
            observations,
            start=1,
        ):
            lines.append(
                f"{index}. "
                f"success={observation.success}; "
                f"content={observation.content}"
            )

        return "\n".join(lines)

    @staticmethod
    def _create_agent_observation(result: AgentResult) -> Observation:
        """
        Convert an AgentResult into a Supervisor-level Observation.

        AgentResult belongs to Agent-to-Agent communication.

        Observation belongs to the current Agent's
        private execution loop.

        Therefore the Supervisor must not directly store
        AgentResult inside LoopState.
        """
        output = result.output

        if output is None:
            content = ""

        elif isinstance(output, str):
            content = output

        else:
            content = str(output)

        return Observation(
            success=result.success,
            content=content,
            metadata={
                key: str(value)
                for key, value in result.metadata.items()
            }
        )

    @staticmethod
    def _build_final_result(
            task: TaskRequest,
            agent_execution_context: AgentExecutionContext,
    ) -> AgentResult:
        """
        Build the final result of the Supervisor execution.

        The Supervisor returns the accumulated downstream
        Agent observations as part of its AgentResult.
        """

        observations = (
            agent_execution_context.loop.observation_history
        )

        successful_observations = [
            observation
            for observation in observations
            if observation.success
        ]

        if successful_observations:
            output = "\n\n".join(
                observation.content
                for observation in successful_observations
            )
        else:
            output = (
                "Supervisor completed without "
                "successful downstream Agent execution."
            )

        return AgentResult(
            success=True,
            output=output,
            observations=list(observations),
            metadata={
                "task_id": task.task_id,
                "execution_steps": str(
                    agent_execution_context.loop.step_count
                ),
            },
        )