import json

from models.action import FinishAction, ToolAction
from runtime.context import ContextState
from planner.base_planner import BasePlanner
from providers.llm_provider import PromptMessage


class CodePlanner(BasePlanner):

    # def __init__(self, provider: LLMProvider):
    #     self.provider = provider
    def __init__(self, llm):
        self.llm = llm

    async def plan(self, task, context, observation):

        messages = [
            PromptMessage(
                role="system",
                content="""
        You are an agent planner.

        You MUST return ONLY valid JSON:

        {
          "type": "tool" | "finish",
          "tool_name": string | null,
          "arguments": object,
          "answer": string | null
        }
        """
            ),

            PromptMessage(
                role="user",
                content=f"""
                Task: {task.objective}
                Observation: {observation}
"""
            )
        ]

        resp = await self.llm.generate(messages)

        data = json.loads(resp.content)

        if data["type"] == "tool":
            return ToolAction(
                tool_name=data["tool_name"],
                arguments=data["arguments"]
            )

        if data["type"] == "finish":
            return FinishAction(
                answer=data["answer"]
            )

        return FinishAction(answer="unknown")

    def _build_reflection_section(
            self,
            context_state: ContextState
    ) -> str:

        reflections = (
            context_state
            .reflections_state
            .reflections
        )

        if not reflections:
            return "None"

        sections = []

        for index, reflection in enumerate(
                reflections,
                start=1
        ):
            suggestions = "\n".join(
                f"- {item}"
                for item in reflection.suggestions
            )

            sections.append(
                f"""
    Reflection {index}

    Summary:
    {reflection.summary}

    Suggestions:
    {suggestions}
    """
            )

        return "\n".join(sections)