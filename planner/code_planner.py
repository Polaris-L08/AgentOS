import json

from actions.action import FinishAction, ToolAction
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

        # text = resp.content.strip()
        data = json.loads(resp.content)

        # if text.startswith("FINISH"):
        #     return FinishAction(answer=text.split(":")[1])
        #
        # if text.startswith("TOOL"):
        #     _, tool, arg = text.split(":")
        #
        #     return ToolAction(
        #         tool_name=tool,
        #         arguments={"msg": arg}
        #     )
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