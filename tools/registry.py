from tools.base import AbstractTool
from tools.exceptions import ToolNotFoundError


class ToolRegistry:
    """
    A registry for single_tools.
    """

    def __init__(self):
        self._tools: dict[str, AbstractTool] = {}

    def register(self, tool: AbstractTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> AbstractTool:
        tool = self._tools.get(name)

        if tool is None:
            raise ToolNotFoundError(name)

        return tool

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())