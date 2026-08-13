from __future__ import annotations

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
            task,
            agent_execution_context: AgentExecutionContext
    ) -> AgentResult:
        """
        Execute one Supervisor task.

        The Supervisor decides which downstream Agent
        should execute the task.
        """
        runtime_context = agent_execution_context.runtime_context

        decision = await self._decide_next_action(task, agent_execution_context)

        if decision == "market_research":
            result = await self._agent_runtime.execute(
                agent=self._research_agent,
                task=task,
                runtime_context=runtime_context
            )

            if not result.success:
                return AgentResult(
                    success=False,
                    output=None,
                    observations=result.observations,
                    metadata={
                        "agent_id": self.identity.agent_id,
                        "agent_type": self.identity.agent_type,
                        "delegated_agent": (
                            self._research_agent.identity.agent_id
                        ),
                    },
                )
            return result

        if decision == "final":
            return AgentResult(
                success=True,
                output=(
                    "Supervisor determined that no downstream "
                    "Agent execution is required."
                ),
                metadata={
                    "agent_id": self.identity.agent_id,
                    "agent_type": self.identity.agent_type,
                },
            )
        raise RuntimeError(
            f"Unsupported Supervisor decision: {decision}"
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
                    "Your responsibility is to decide whether "
                    "the current user task requires a ResearchAgent.\n"
                    "\n"
                    "Available decisions:\n"
                    "\n"
                    "research\n"
                    "Use ResearchAgent to perform investment research.\n"
                    "\n"
                    "final\n"
                    "The task does not require ResearchAgent.\n"
                    "\n"
                    "Return exactly one of:\n"
                    "research\n"
                    "final"
                ),
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
            "market_research",
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