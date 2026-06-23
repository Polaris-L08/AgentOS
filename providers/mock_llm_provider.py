from providers.llm_response import LLMResponse


class MockLLMProvider:

    async def generate(
        self,
        messages
    ) -> LLMResponse:

        if "Observation:" in messages[-1].content:

            return LLMResponse(
                content="""
{
  "type": "tool",
  "tool_name": "echo",
  "arguments": {
    "msg": "hello"
  }
}
"""
            )

        return LLMResponse(
            content="""
{
  "type": "finish",
  "answer": "done"
}
"""
        )