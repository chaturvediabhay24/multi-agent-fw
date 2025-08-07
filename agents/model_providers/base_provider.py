import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool


class BaseModelProvider(ABC):
    """Abstract base class for model providers"""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs
        self.bound_tools: List[BaseTool] = []
    
    @abstractmethod
    async def ainvoke(self, messages: List[BaseMessage]) -> Union[str, dict]:
        """Async invoke the model with messages and return response"""
        pass
    
    @abstractmethod
    async def ainvoke_with_tools(self, messages: List[BaseMessage], tools: List[BaseTool]) -> Union[str, dict]:
        """Async invoke the model with tools and return response (could include tool calls)"""
        pass
    
    def invoke(self, messages: List[BaseMessage]) -> Union[str, dict]:
        """Synchronous invoke (for backward compatibility) - runs async version"""
        return asyncio.run(self.ainvoke(messages))
    
    def invoke_with_tools(self, messages: List[BaseMessage], tools: List[BaseTool]) -> Union[str, dict]:
        """Synchronous invoke with tools (for backward compatibility) - runs async version"""
        return asyncio.run(self.ainvoke_with_tools(messages, tools))
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'claude')"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (API key set, etc.)"""
        pass
    
    def bind_tools(self, tools: List[BaseTool]):
        """Bind tools to this provider"""
        self.bound_tools = tools
    
    def supports_tool_calling(self) -> bool:
        """Check if this provider supports structured tool calling"""
        return True