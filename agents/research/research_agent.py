from __future__ import annotations

from actions.observation import Observation
from agents import BaseAgent, AgentResult
from agents.identity import AgentIdentity
from agents.research.domain.report import ResearchReport
from agents.research.domain.task import ResearchTask
from models.task_request import TaskRequest
from providers.llm_provider import LLMProvider
from providers.llm_response import LLMResponse
from providers.prompt_message import PromptMessage
from runtime.context import AgentExecutionContext
from tools.request import ToolRequest
from tools.tool_executor import ToolExecutor


class ResearchAgent(BaseAgent):
    """
    Investment research Agent.

    ResearchAgent is a domain-level Agent.

    Responsibilities:
        - understand a ResearchTask
        - perform research-related Agent logic
        - produce a ResearchReport
        - return the report through AgentResult

    It does NOT own:
        - Agent invocation
        - Agent scheduling
        - Middleware execution
        - Tracing
        - Checkpoint management
        - Event publishing
        - Runtime lifecycle

    Those responsibilities belong to AgentOS Runtime.
    """

    def __init__(self,
                 identity: AgentIdentity,
                 tool_executor: ToolExecutor,
                 llm_provider: LLMProvider
                 ) -> None:
        super().__init__(identity)
        self._tool_executor = tool_executor
        self._llm_provider = llm_provider

    async def run(
            self,
            task: TaskRequest,
            agent_execution_context: AgentExecutionContext
    ) -> AgentResult:
        """
        Execute one research task.

        Args:
            task:
                TaskRequest submitted to this Agent.

            agent_execution_context:
                Isolated execution context belonging to this
                invocation of ResearchAgent.

        Returns:
            AgentResult:
                Result of this research execution.
        """
        research_task = self._create_research_task(task)

        max_steps = 5

        while(agent_execution_context.loop.step_count < max_steps):
            agent_execution_context.loop.step_count += 1

            decision = await self._select_tool(research_task, agent_execution_context)

            if decision == "final":
                return self._build_final_result(research_task, agent_execution_context)


            tool_result = await self._execute_research_tool(
                research_task,
                decision,
                agent_execution_context,
            )

            observation = self._create_observation(tool_result)

            agent_execution_context.loop.observation_history.append(observation)


            if not tool_result.success:
                return AgentResult(
                    success=False,
                    output=None,
                    observations=[observation],
                    metadata={
                        "agent_id": self.identity.agent_id,
                        "agent_type": self.identity.agent_type,
                    },
                )

        raise RuntimeError("ResearchAgent exceeded maximum execution steps.")

    async def _execute_research_tool(self, task: ResearchTask, tool_name: str, agent_execution_context: AgentExecutionContext):
        """
        Execute the tool required for the current research task.

        ResearchAgent decides WHAT it needs.
        ToolExecutor decides HOW the Tool is executed.
        """

        request = ToolRequest(
            tool_name=tool_name,
            arguments={
                "subject": task.subject,
                "objective": task.objective,
            }
        )
        return await self._tool_executor.execute(
            request=request,
            context=agent_execution_context,
        )

    @staticmethod
    def _create_research_task(task: TaskRequest) -> ResearchTask:
        """
        Convert a generic runtime request into an
        Investment Research domain task.

        Current implementation uses a simple deterministic
        interpretation.

        A later version may use an LLM-based task interpreter.
        """
        if not task.user_input.strip():
            raise ValueError("Research request cannot be empty.")

        return ResearchTask(
            task_id=task.task_id,
            subject=ResearchAgent._extract_subject(task.user_input),
            objective=task.user_input,
        )

    @staticmethod
    def _extract_subject(user_input: str) -> str:
        """
        Extract the research subject from a user request.

        This is intentionally simple for the current lesson.
        Real task interpretation will be introduced later.
        """
        if not user_input.strip():
            raise ValueError("Research request cannot be empty.")
        return "NVIDIA"

    async def _select_tool(
            self,
            task: ResearchTask,
            agent_execution_context: AgentExecutionContext,
    ) -> str:
        """
        Ask the LLM to determine which research Tool
        should be used for the current task.

        The LLM only provides a decision.

        ResearchAgent remains responsible for validating
        the decision and creating ToolRequest.
        """

        messages = [
            PromptMessage(
                role="system",
                content=(
                    "You are an investment research agent.\n"
                    "\n"
                    "You have two possible decisions:\n"
                    "\n"
                    "1. market_research\n"
                    "   Use the market research tool to obtain "
                    "additional information.\n"
                    "\n"
                    "2. final\n"
                    "   The available information is sufficient "
                    "to complete the research task.\n"
                    "\n"
                    "Return exactly one of:\n"
                    "market_research\n"
                    "final"
                ),
            ),
            PromptMessage(
                role="user",
                content=self._build_decision_prompt(
                    task,
                    agent_execution_context,
                ),
            ),
        ]

        response = await self._llm_provider.generate(
            messages
        )

        return self._validate_decision(
            response
        )

    @staticmethod
    def _validate_decision(response: LLMResponse) -> str:
        """
        Validate an LLM-generated Tool decision.

        The LLM is not trusted to directly control ToolExecutor.
        """

        decision = response.content.strip()

        allowed_decisions = {
            "market_research",
            "final",
        }

        if decision not in allowed_decisions:
            raise ValueError(
                f"LLM selected unsupported decision: "
                f"{decision}"
            )

        return decision

    @staticmethod
    def _create_observation(tool_result) -> Observation:
        """
        Convert a ToolResult into an Agent-level Observation.

        ToolResult belongs to Tool Runtime.
        Observation belongs to Agent execution.

        The Agent should not expose the Tool Runtime's
        internal result model as its own observation.
        """

        return Observation(
            success=tool_result.success,
            content=str(tool_result.output)
            if tool_result.output is not None
            else (
                str(tool_result.error)
                if tool_result.error is not None
                else ""
            ),
            metadata={
                key: str(value)
                for key, value in tool_result.metadata.items()
            },
        )

    @staticmethod
    def _build_decision_prompt(task: ResearchTask, agent_execution_context: AgentExecutionContext) -> str:
        """
        Build the decision prompt for the current Agent loop iteration.

        The prompt contains:
            - original research task
            - observations collected so far
        """

        lines = [
            f"Research subject: {task.subject}",
            f"Research objective: {task.objective}",
            "",
            "Previous observations:",
        ]

        observations = agent_execution_context.loop.observation_history

        if not  observations:
            lines.append("None")
        else:
            for index, observation in enumerate(observations, start=1):
                lines.append(
                    f"{index}."
                    f"success={observation.success};"
                    f"content={observation.content}"
                )

        return "\n".join(lines)

    def _build_final_result(self, research_task, agent_execution_context):
        """
        Build the final AgentResult from the accumulated
        Agent observations.
        """
        observations = agent_execution_context.loop.observation_history

        report = ResearchReport(
            task_id=research_task.task_id,
            subject=research_task.subject,
            summary=self._build_summary(observations),
            findings=tuple(
                observation.content
                for observation in observations
                if observation.success
            ),
            risks=(),
            evidence=(),
        )

        return AgentResult(
            success=True,
            output=report,
            observations=list(observations),
            metadata={
                "agent_id": self.identity.agent_id,
                "agent_type": self.identity.agent_type,
                "step_count": str(agent_execution_context.loop.step_count),
            }
        )

    @staticmethod
    def _build_summary(observations):
        """
        Build a minimal summary from collected observations.

        Sophisticated report synthesis will be introduced later.
        """
        successful_observations = [
            observation
            for observation in observations
            if observation.success
        ]

        if not successful_observations:
            return "No successful research observations."

        return "Research completed successfully."