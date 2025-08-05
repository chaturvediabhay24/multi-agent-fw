from typing import Dict, Any, Literal
from langchain_core.messages import BaseMessage


class ToolCallMessage(BaseMessage):
    """Message representing a tool call"""
    
    def __init__(self, tool_name: str, parameters: Dict[str, Any], result: Any, success: bool, **kwargs):
        self.tool_name = tool_name
        self.parameters = parameters
        self.result = result
        self.success = success
        
        # Create content string for display
        content = f"Tool Call: {tool_name}({', '.join(f'{k}={v}' for k, v in parameters.items())})"
        if success:
            content += f" -> {result}"
        else:
            content += f" -> ERROR: {result}"
        
        super().__init__(content=content, **kwargs)
    
    @property
    def type(self) -> Literal["tool_call"]:
        return "tool_call"