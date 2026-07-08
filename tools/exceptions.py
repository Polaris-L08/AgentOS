class ToolNotFoundError(Exception):

    def __init__(self, tool_name: str):

        super().__init__(f"Tool {tool_name} not found")

        self.tool_name = tool_name

class ToolExecutionError(Exception):
    pass