import os
from typing import List, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from .base_provider import BaseModelProvider


class OpenAIProvider(BaseModelProvider):
    """OpenAI model provider"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", **kwargs):
        super().__init__(model_name, **kwargs)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client"""
        if self.is_available():
            self.client = ChatOpenAI(
                model=self.model_name,
                api_key=os.getenv('OPENAI_API_KEY'),
                **self.config
            )
    
    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Async invoke OpenAI model without tools"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Check API key.")
        
        response = await self.client.ainvoke(messages)
        return response.content
    
    async def ainvoke_with_tools(self, messages: List[BaseMessage], tools: List[BaseTool]) -> Union[str, dict]:
        """Async invoke OpenAI model with tools"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Check API key.")
        
        if not tools:
            return await self.ainvoke(messages)
        
        # Bind tools to the client
        client_with_tools = self.client.bind_tools(tools)
        
        # Async invoke with tools
        response = await client_with_tools.ainvoke(messages)
        
        # Check if response contains tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return {
                'content': response.content,
                'tool_calls': response.tool_calls
            }
        else:
            return response.content
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "openai"
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is available"""
        return bool(os.getenv('OPENAI_API_KEY'))