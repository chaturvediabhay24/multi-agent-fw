import os
import json
import aiohttp
from typing import List, Union, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from .base_provider import BaseModelProvider


class BedrockBearerProvider(BaseModelProvider):
    """AWS Bedrock Claude provider using bearer token authentication"""
    
    def __init__(self, model_name: str = "anthropic.claude-3-sonnet-20240229-v1:0", **kwargs):
        super().__init__(model_name, **kwargs)
        self.region = os.getenv('AWS_BEDROCK_REGION', 'eu-west-2')
        self.endpoint = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{model_name}/invoke"
        self.bearer_token = os.getenv('AWS_BEARER_TOKEN_BEDROCK')
        
    def _format_messages_for_bedrock(self, messages: List[BaseMessage], tools: List[BaseTool] = None) -> dict:
        """Format messages for Bedrock Claude API"""
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_message = msg.content
            elif isinstance(msg, HumanMessage):
                user_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                # Handle AI messages with tool calls
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # Convert tool calls to Bedrock format
                    content_blocks = []
                    if msg.content:
                        content_blocks.append({"type": "text", "text": msg.content})
                    
                    for tool_call in msg.tool_calls:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tool_call.get('id', ''),
                            "name": tool_call.get('name', ''),
                            "input": tool_call.get('args', {})
                        })
                    
                    user_messages.append({"role": "assistant", "content": content_blocks})
                else:
                    user_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                # Handle tool result messages
                user_messages.append({
                    "role": "user", 
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content
                        }
                    ]
                })
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
        }
        
        if system_message:
            payload["system"] = system_message
            
        payload.update({
            "max_tokens": self.config.get('max_tokens', 4096),
            "temperature": self.config.get('temperature', 0.7),
            "messages": user_messages
        })
        
        # Add tools if provided
        if tools:
            payload["tools"] = self._format_tools_for_bedrock(tools)
            
        return payload
    
    def _format_tools_for_bedrock(self, tools: List[BaseTool]) -> List[dict]:
        """Format tools for Bedrock Claude API"""
        formatted_tools = []
        
        for tool in tools:
            # Get the tool schema
            tool_schema = {
                "name": tool.name,
                "description": tool.description
            }
            
            # Add input schema if available
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    # Convert Pydantic model to JSON schema
                    input_schema = tool.args_schema.model_json_schema()
                    tool_schema["input_schema"] = input_schema
                except Exception:
                    # Fallback if schema extraction fails
                    tool_schema["input_schema"] = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
            else:
                tool_schema["input_schema"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            
            formatted_tools.append(tool_schema)
        
        return formatted_tools
    
    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Async invoke Bedrock Claude model without tools"""
        if not self.is_available():
            raise RuntimeError("Bedrock bearer token not available. Set AWS_BEARER_TOKEN_BEDROCK in your .env file.")
        
        payload = self._format_messages_for_bedrock(messages)
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'Accept': 'application/json'
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint, 
                                       json=payload, 
                                       headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        self._handle_bedrock_error(response.status, error_text)
                    
                    result = await response.json()
                    
                    # Extract content from Bedrock response
                    if 'content' in result and len(result['content']) > 0:
                        return result['content'][0]['text']
                    else:
                        raise RuntimeError(f"Unexpected response format: {result}")
                        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse response JSON: {e}")
    
    async def ainvoke_with_tools(self, messages: List[BaseMessage], tools: List[BaseTool]) -> Union[str, dict]:
        """Async invoke Bedrock Claude model with tools and handle complete execution cycle"""
        if not self.is_available():
            raise RuntimeError("Bedrock bearer token not available. Set AWS_BEARER_TOKEN_BEDROCK in your .env file.")
        
        if not tools:
            return await self.ainvoke(messages)
        
        # Create a working copy of messages to avoid modifying the original
        working_messages = messages.copy()
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call the model with current messages and tools
            response = await self._make_bedrock_call(working_messages, tools)
            
            if not response:
                return "Error: No response from Bedrock"
                
            # Parse the response
            content_blocks = response.get('content', [])
            tool_calls = []
            text_content = []
            
            for block in content_blocks:
                if block.get('type') == 'tool_use':
                    tool_call = {
                        'name': block.get('name'),
                        'args': block.get('input', {}),
                        'id': block.get('id')
                    }
                    tool_calls.append(tool_call)
                    print(f"🔧 Tool Request - Name: {tool_call['name']}, ID: {tool_call['id']}")
                    print(f"📋 Tool Parameters: {json.dumps(tool_call['args'], indent=2)}")
                elif block.get('type') == 'text':
                    text_content.append(block.get('text', ''))
            
            # If no tool calls, we're done - return the text response with conversation history
            if not tool_calls:
                final_response = ''.join(text_content)
                # Add the final AI response to working messages
                final_ai_message = AIMessage(content=final_response)
                working_messages.append(final_ai_message)
                return {
                    'content': final_response,
                    'messages': working_messages
                }
            
            # Add the AI message with tool calls to working messages
            ai_message = AIMessage(
                content=''.join(text_content),
                tool_calls=[{
                    'id': tc['id'],
                    'name': tc['name'], 
                    'args': tc['args']
                } for tc in tool_calls]
            )
            working_messages.append(ai_message)
            
            # Execute each tool and add results to working messages
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
                
                # Find the tool by name
                tool_to_execute = None
                for tool in tools:
                    if tool.name == tool_name:
                        tool_to_execute = tool
                        break
                
                if tool_to_execute:
                    try:
                        print(f"⚡ Executing tool: {tool_name}")
                        # Execute the tool using the correct LangChain method
                        # LangChain tools expect a single input parameter or JSON string
                        if hasattr(tool_to_execute, 'ainvoke'):
                            # Use ainvoke if available (newer LangChain)
                            result = await tool_to_execute.ainvoke(tool_args)
                        else:
                            # Fall back to arun with proper parameter handling
                            if len(tool_args) == 1:
                                # Single parameter - pass the value directly
                                result = await tool_to_execute.arun(list(tool_args.values())[0])
                            else:
                                # Multiple parameters - pass as JSON string
                                result = await tool_to_execute.arun(json.dumps(tool_args))
                        
                        tool_result = str(result)
                        print(f"✅ Tool Response ({tool_name}): {tool_result[:200]}{'...' if len(tool_result) > 200 else ''}")
                    except Exception as e:
                        tool_result = f"Error executing tool {tool_name}: {str(e)}"
                        print(f"❌ Tool Error ({tool_name}): {tool_result}")
                else:
                    tool_result = f"Tool {tool_name} not found"
                
                # Add tool result to working messages
                tool_message = ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_id
                )
                working_messages.append(tool_message)
        
        # If we reach max iterations, return the final response with conversation history
        return {
            'content': "Error: Maximum tool execution iterations reached",
            'messages': working_messages
        }
    
    async def _make_bedrock_call(self, messages: List[BaseMessage], tools: List[BaseTool] = None) -> Dict[str, Any]:
        """Make a single call to Bedrock API"""
        payload = self._format_messages_for_bedrock(messages, tools)
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'Accept': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint, 
                                       json=payload, 
                                       headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        self._handle_bedrock_error(response.status, error_text)
                    
                    result = await response.json()
                    return result
                        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse response JSON: {e}")
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "bedrock_bearer"
    
    def is_available(self) -> bool:
        """Check if AWS Bedrock bearer token is available"""
        return bool(os.getenv('AWS_BEARER_TOKEN_BEDROCK'))
    
    def _handle_bedrock_error(self, status: int, error_text: str):
        """Handle common Bedrock API errors"""
        if status == 403:
            if "not authorized to perform: bedrock:InvokeModel" in error_text:
                raise RuntimeError(
                    f"AWS Bedrock permissions error: The AWS account associated with your bearer token "
                    f"does not have permission to invoke Claude models. Please contact your AWS "
                    f"administrator to grant 'bedrock:InvokeModel' permissions for Anthropic Claude models. "
                    f"Full error: {error_text[:200]}..."
                )
            else:
                raise RuntimeError(f"Bedrock access denied (403): {error_text[:200]}...")
        else:
            raise RuntimeError(f"Bedrock API error {status}: {error_text[:200]}...")
    
