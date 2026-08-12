from __future__ import annotations

from agents import BaseAgent, AgentResult
from agents.identity import AgentIdentity
from agents.research.domain.report import ResearchReport
from agents.research.domain.task import ResearchTask
from models.task_request import TaskRequest
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

    def __init__(self, identity: AgentIdentity, tool_executor: ToolExecutor) -> None:
        super().__init__(identity)
        self._tool_executor = tool_executor

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

        tool_result = await self._execute_research_tool(
            research_task,
            agent_execution_context,
        )

        if not tool_result.success:
            return AgentResult(
                success=False,
                output=None,
                metadata={
                    "agent_id": self.identity.agent_id,
                    "agent_type": self.identity.agent_type,
                }
            )

        report = self._build_report(
            research_task,
            tool_result.output,
        )

        return AgentResult(
            success=True,
            output=report,
            observations=[tool_result],
            metadata={
                "agent_id": self.identity.agent_id,
                "agent_type": self.identity.agent_type,
            },
        )

    async def _execute_research_tool(self, task: ResearchTask, agent_execution_context: AgentExecutionContext):
        """
        Execute the tool required for the current research task.

        ResearchAgent decides WHAT it needs.
        ToolExecutor decides HOW the Tool is executed.
        """
        request = ToolRequest(
            tool_name="market_research",
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
    def _build_report(task: ResearchTask, tool_output) -> ResearchReport:
        return ResearchReport(
            task_id=task.task_id,
            subject=task.subject,
            summary=str(tool_output),
            findings=(
                f"The research subject is {task.subject}.",
                f"The research objective is: {task.objective}.",
            ),
            risks=(),
            evidence=(),
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