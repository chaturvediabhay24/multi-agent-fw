import asyncio
import re
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from tools.tool_registry import ToolRegistry
from tools.langchain_tool_adapter import LangChainToolAdapter
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage


class CustomAgent(BaseAgent):
    def __init__(self, name: str, config: Dict[str, Any], conversation_id: str = None):
        super().__init__(name, config, conversation_id)
        self.tool_registry = ToolRegistry()
        self.debug_mode = config.get('debug', False)
        self.tool_calls_made = []
        self.parallel_execution = config.get('parallel_tools', True)  # Enable parallel execution by default
        self.max_parallel_tools = config.get('max_parallel_tools', 2)  # Limit concurrent tools
        self._last_had_tool_calls = False  # Track tool call usage for fallback logic
        self._conversation_managed_by_provider = False  # Track if provider managed conversation history
        
        # Load agent-specific tools
        agent_tools = self.get_available_tools()
        if agent_tools:
            self.tool_registry.load_tools_for_agent(agent_tools)
        
    def get_description(self) -> str:
        """Return a description of what this agent does"""
        return self.config.get('description', f'Custom agent: {self.name}')
    
    async def _aprocess_message(self, message: str) -> str:
        """Async process message with structured tool calling"""
        available_tools = self.get_available_tools()
        self.tool_calls_made = []  # Reset tool calls for this message
        self._conversation_managed_by_provider = False  # Reset flag
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Available tools: {available_tools}")
        
        # Get tools for structured calling first (preferred method for parallel execution)
        if available_tools and self.model_provider.supports_tool_calling():
            # Try structured calling first to enable parallel execution
            structured_result = await self._aprocess_with_structured_tools(message, available_tools)
            
            return structured_result
        else:
            # Fallback to regular processing without tools
            return await super()._aprocess_message(message)
    
    def _process_message(self, message: str) -> str:
        """Synchronous process message (for backward compatibility)"""
        return asyncio.run(self._aprocess_message(message))
    
    async def _aprocess_with_structured_tools(self, message: str, available_tool_names: List[str]) -> str:
        """Async process message using structured tool calling"""
        # Get tool instances
        tools = []
        for tool_name in available_tool_names:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool)
        
        if not tools:
            return await super()._aprocess_message(message)
        
        # Convert to LangChain tools
        langchain_tools = LangChainToolAdapter.convert_tools(tools)
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Converted {len(langchain_tools)} tools for structured calling")
        
        # Async invoke model with tools
        response = await self.model_provider.ainvoke_with_tools(
            self.conversation_history, 
            langchain_tools
        )
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Model response type: {type(response)}")
        
        # Handle structured response
        if isinstance(response, dict):
            if 'tool_calls' in response:
                return await self._ahandle_structured_tool_calls(response)
            elif 'messages' in response:
                # Handle BedrockBearerProvider response with conversation history
                updated_messages = response['messages']
                content = response.get('content', '')
                
                # Update conversation history with the messages from provider
                # Remove current messages and replace with updated ones from provider
                original_count = len(self.conversation_history)
                self.conversation_history = updated_messages
                
                if self.debug_mode:
                    print(f"🔧 DEBUG: Updated conversation history from {original_count} to {len(self.conversation_history)} messages")
                
                # Signal that conversation history is already managed
                self._conversation_managed_by_provider = True
                return content
        
        # No tool calls, return regular response
        self._last_had_tool_calls = False
        return str(response)
    
    def _process_with_structured_tools(self, message: str, available_tool_names: List[str]) -> str:
        """Synchronous process with structured tools (for backward compatibility)"""
        return asyncio.run(self._aprocess_with_structured_tools(message, available_tool_names))
    
    async def _ahandle_structured_tool_calls(self, response: Dict[str, Any]) -> str:
        """Async handle structured tool calls from the model"""
        content = response.get('content', '')
        tool_calls = response.get('tool_calls', [])
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Processing {len(tool_calls)} structured tool calls")
        
        tool_results = []
        tool_messages = []
        
        # First, add the AI message with tool calls to conversation history
        ai_message_with_tools = AIMessage(
            content=content or "",
            tool_calls=tool_calls
        )
        self.conversation_history.append(ai_message_with_tools)
        
        # Track whether we had tool calls for fallback logic
        self._last_had_tool_calls = len(tool_calls) > 0
        
        # Execute tools (parallel or sequential based on configuration)
        if self.parallel_execution and len(tool_calls) > 1:
            tool_messages, tool_results = await self._aexecute_tools_parallel(tool_calls)
        else:
            tool_messages, tool_results = await self._aexecute_tools_sequential(tool_calls)
        
        # Add all tool messages to conversation history
        self.conversation_history.extend(tool_messages)
        
        # Combine content and tool results for display
        if tool_results:
            if content:
                return f"{content}\n\n" + "\n".join(tool_results)
            else:
                return "\n".join(tool_results)
        else:
            return content or "No tool results available."
    
    def _handle_structured_tool_calls(self, response: Dict[str, Any]) -> str:
        """Synchronous handle structured tool calls (for backward compatibility)"""
        return asyncio.run(self._ahandle_structured_tool_calls(response))
    
    async def _aexecute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Async execute a single tool call and return the result info"""
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_call_id = tool_call.get('id', '')
        
        try:
            if self.debug_mode:
                print(f"🔧 DEBUG: Executing tool {tool_name} with args: {tool_args}")
            
            # Execute the tool (run in thread pool if it's not async)
            # Use a lambda to handle kwargs properly
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.tool_registry.execute_tool(tool_name, **tool_args)
            )
            
            # Store tool call info
            tool_call_info = {
                'tool_name': tool_name,
                'params': tool_args,
                'result': result,
                'success': True
            }
            
            # Create tool message for conversation history
            tool_message = ToolMessage(
                content=str(result),
                tool_call_id=tool_call_id
            )
            
            # Format result for display
            if isinstance(result, dict) and 'success' in result:
                if result['success']:
                    formatted_result = result.get('formatted_result', result.get('result', result))
                    formatted_display = f"**{tool_name}**: {formatted_result}"
                else:
                    formatted_display = f"**{tool_name} Error**: {result.get('error', 'Unknown error')}"
            else:
                formatted_display = f"**{tool_name}**: {result}"
            
            return {
                'tool_call_info': tool_call_info,
                'tool_message': tool_message,
                'formatted_display': formatted_display
            }
            
        except Exception as e:
            if self.debug_mode:
                print(f"🔧 DEBUG: Tool execution error: {str(e)}")
            
            # Store failed tool call
            tool_call_info = {
                'tool_name': tool_name,
                'params': tool_args,
                'result': str(e),
                'success': False
            }
            
            # Create tool message for failed call
            tool_message = ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=tool_call_id
            )
            
            return {
                'tool_call_info': tool_call_info,
                'tool_message': tool_message,
                'formatted_display': f"**Tool Error**: {str(e)}"
            }
    
    def _execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous execute single tool (for backward compatibility)"""
        return asyncio.run(self._aexecute_single_tool(tool_call))
    
    async def _aexecute_tools_sequential(self, tool_calls: List[Dict[str, Any]]) -> tuple:
        """Async execute tools sequentially"""
        tool_messages = []
        tool_results = []
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Executing {len(tool_calls)} tools sequentially")
        
        for tool_call in tool_calls:
            result_info = await self._aexecute_single_tool(tool_call)
            self.tool_calls_made.append(result_info['tool_call_info'])
            tool_messages.append(result_info['tool_message'])
            tool_results.append(result_info['formatted_display'])
        
        return tool_messages, tool_results
    
    def _execute_tools_sequential(self, tool_calls: List[Dict[str, Any]]) -> tuple:
        """Synchronous execute tools sequentially (for backward compatibility)"""
        return asyncio.run(self._aexecute_tools_sequential(tool_calls))
    
    async def _aexecute_tools_parallel(self, tool_calls: List[Dict[str, Any]]) -> tuple:
        """Async execute tools in parallel using asyncio.gather"""
        tool_messages = []
        tool_results = []
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Executing {len(tool_calls)} tools in parallel asynchronously")
        
        try:
            # Execute all tools concurrently using asyncio.gather
            results = await asyncio.gather(
                *[self._aexecute_single_tool(tool_call) for tool_call in tool_calls],
                return_exceptions=True
            )
            
            # Process results in order
            for i, result_info in enumerate(results):
                if isinstance(result_info, Exception):
                    # Handle exception result
                    tool_call = tool_calls[i]
                    if self.debug_mode:
                        print(f"🔧 DEBUG: Parallel execution error for {tool_call.get('name', 'unknown')}: {str(result_info)}")
                    
                    error_result = {
                        'tool_call_info': {
                            'tool_name': tool_call.get('name', 'unknown'),
                            'params': tool_call.get('args', {}),
                            'result': str(result_info),
                            'success': False
                        },
                        'tool_message': ToolMessage(
                            content=f"Parallel execution error: {str(result_info)}",
                            tool_call_id=tool_call.get('id', '')
                        ),
                        'formatted_display': f"**Parallel Error**: {str(result_info)}"
                    }
                    result_info = error_result
                
                # Add successful or error results
                self.tool_calls_made.append(result_info['tool_call_info'])
                tool_messages.append(result_info['tool_message'])
                tool_results.append(result_info['formatted_display'])
                
                if self.debug_mode and not isinstance(results[i], Exception):
                    print(f"🔧 DEBUG: Completed tool {tool_calls[i]['name']}")
        
        except Exception as e:
            if self.debug_mode:
                print(f"🔧 DEBUG: Fatal error in parallel execution: {str(e)}")
            raise
        
        return tool_messages, tool_results
    
    def _execute_tools_parallel(self, tool_calls: List[Dict[str, Any]]) -> tuple:
        """Synchronous execute tools in parallel (for backward compatibility)"""
        return asyncio.run(self._aexecute_tools_parallel(tool_calls))
    
    def _create_tool_enhanced_prompt(self, message: str, available_tools: list) -> str:
        """Create an enhanced prompt that includes available tools"""
        if not available_tools:
            return message
        
        tool_descriptions = []
        for tool_name in available_tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tool_descriptions.append(f"- {tool_name}: {tool.description}")
        
        if not tool_descriptions:
            return message
        
        enhanced_prompt = f"""
User request: {message}"""
        
        return enhanced_prompt
    
    def _handle_tool_calls_regex(self, response: str) -> str:
        """Handle any tool calls in the response (DEPRECATED - kept for backward compatibility)"""
        # Pattern to match tool calls
        tool_call_pattern = r'\[TOOL_CALL:\s*(\w+)\((.*?)\)\]'
        
        def execute_tool_call(match):
            tool_name = match.group(1)
            params_str = match.group(2)
            
            try:
                # Parse parameters
                params = self._parse_tool_params(params_str)
                
                if self.debug_mode:
                    print(f"🔧 DEBUG: Executing tool {tool_name} with params: {params}")
                
                # Execute the tool
                result = self.tool_registry.execute_tool(tool_name, **params)
                
                # Store tool call info
                tool_call_info = {
                    'tool_name': tool_name,
                    'params': params,
                    'result': result,
                    'success': True
                }
                
                # Create tool call message for conversation history (using AIMessage for compatibility)
                success = isinstance(result, dict) and result.get('success', True)
                from langchain_core.messages import AIMessage
                
                tool_content = f"[TOOL_EXECUTION: {tool_name}({params}) -> {result}]"
                tool_message = AIMessage(content=tool_content)
                
                # Add to conversation history
                self.conversation_history.append(tool_message)
                
                tool_call_info['success'] = success
                self.tool_calls_made.append(tool_call_info)
                
                # Format the result
                if isinstance(result, dict) and 'success' in result:
                    if result['success']:
                        if 'formatted_result' in result:
                            return f"**Tool Result ({tool_name})**: {result['formatted_result']}"
                        elif 'result' in result:
                            return f"**Tool Result ({tool_name})**: {result['result']}"
                        elif 'data' in result:
                            return f"**Tool Result ({tool_name})**: {result['data']}"
                        else:
                            return f"**Tool Result ({tool_name})**: {result}"
                    else:
                        return f"**Tool Error ({tool_name})**: {result.get('error', 'Unknown error')}"
                else:
                    return f"**Tool Result ({tool_name})**: {result}"
                    
            except Exception as e:
                # Store failed tool call info
                tool_call_info = {
                    'tool_name': tool_name,
                    'params': params_str,
                    'result': str(e),
                    'success': False
                }
                self.tool_calls_made.append(tool_call_info)
                
                # Create tool call message for conversation history (using AIMessage for compatibility)  
                from langchain_core.messages import AIMessage
                
                tool_content = f"[TOOL_EXECUTION_ERROR: {tool_name}({params_str}) -> {str(e)}]"
                tool_message = AIMessage(content=tool_content)
                self.conversation_history.append(tool_message)
                
                return f"**Tool Error ({tool_name})**: {str(e)}"
        
        # Replace all tool calls with their results
        processed_response = re.sub(tool_call_pattern, execute_tool_call, response)
        
        return processed_response
    
    def _parse_tool_params(self, params_str: str) -> dict:
        """Parse tool parameters from string format"""
        params = {}
        
        # Simple parameter parsing (key="value" or key=value)
        param_pattern = r'(\w+)=(?:"([^"]*)"|([^,\)]+))'
        matches = re.findall(param_pattern, params_str)
        
        for match in matches:
            key = match[0]
            value = match[1] if match[1] else match[2]
            # Try to convert to appropriate type
            try:
                # Try to evaluate as Python literal (for numbers, booleans, etc.)
                params[key] = eval(value) if value not in ['true', 'false'] else value == 'true'
            except:
                # Keep as string if evaluation fails
                params[key] = value.strip()
        
        return params
    
    def _parse_math_expression(self, expression: str) -> dict:
        """Parse a mathematical expression into param1, param2, operator format"""
        import re
        
        expression = expression.strip()
        
        # Handle single parameter functions first
        single_param_funcs = {
            'sqrt': 'sqrt',
            'sin': 'sin', 
            'cos': 'cos',
            'tan': 'tan',
            'log': 'log',
            'ln': 'log'
        }
        
        for func_name, operator in single_param_funcs.items():
            pattern = rf'{func_name}\s*\(\s*([0-9.]+)\s*\)'
            match = re.search(pattern, expression)
            if match:
                param1 = float(match.group(1))
                return {'param1': param1, 'operator': operator}
        
        # Handle two parameter operations
        # Look for patterns like "23582345*3245", "123 + 456", etc.
        two_param_patterns = [
            (r'([0-9.]+)\s*\*\s*([0-9.]+)', 'multiply'),
            (r'([0-9.]+)\s*\+\s*([0-9.]+)', 'add'),
            (r'([0-9.]+)\s*-\s*([0-9.]+)', 'subtract'),
            (r'([0-9.]+)\s*/\s*([0-9.]+)', 'divide'),
            (r'([0-9.]+)\s*\^\s*([0-9.]+)', 'power'),
            (r'([0-9.]+)\s*\*\*\s*([0-9.]+)', 'power'),
        ]
        
        for pattern, operator in two_param_patterns:
            match = re.search(pattern, expression)
            if match:
                param1 = float(match.group(1))
                param2 = float(match.group(2))
                return {'param1': param1, 'param2': param2, 'operator': operator}
        
        # Handle percentage calculations like "15% of 200"
        percentage_pattern = r'([0-9.]+)%\s*of\s*([0-9.]+)'
        match = re.search(percentage_pattern, expression)
        if match:
            percentage = float(match.group(1)) / 100
            base_value = float(match.group(2))
            return {'param1': base_value, 'param2': percentage, 'operator': 'multiply'}
        
        # If we can't parse, return None
        return None
    
    async def _aexecute_forced_tool_call(self, tool_call_info: dict) -> str:
        """Async execute a forced tool call and format the response"""
        tool_name = tool_call_info['tool_name']
        params = tool_call_info['params']
        
        try:
            # Execute the tool
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.tool_registry.execute_tool(tool_name, **params)
            )
            
            # Store tool call info
            tool_call_record = {
                'tool_name': tool_name,
                'params': params,
                'result': result,
                'success': True
            }
            
            # Create tool call message for conversation history (using AIMessage for compatibility)
            success = isinstance(result, dict) and result.get('success', True)
            from langchain_core.messages import AIMessage
            
            tool_content = f"[TOOL_EXECUTION: {tool_name}({params}) -> {result}]"
            tool_message = AIMessage(content=tool_content)
            
            # Add to conversation history
            self.conversation_history.append(tool_message)
            
            tool_call_record['success'] = success
            self.tool_calls_made.append(tool_call_record)
            
            # Format response
            if isinstance(result, dict) and 'success' in result:
                if result['success']:
                    operation = result.get('operation', 'calculation')
                    answer = result.get('formatted_result', result.get('result', 'N/A'))
                    
                    return f"I'll calculate that for you.\n\n**{operation} = {answer}**"
                else:
                    return f"I tried to calculate that but encountered an error: {result.get('error', 'Unknown error')}"
            else:
                return f"**Calculator Result**: {result}"
                
        except Exception as e:
            # Store failed tool call
            tool_call_record = {
                'tool_name': tool_name,
                'params': params,
                'result': str(e),
                'success': False
            }
            self.tool_calls_made.append(tool_call_record)
            
            return f"I tried to calculate that but encountered an error: {str(e)}"
    
    def _execute_forced_tool_call(self, tool_call_info: dict) -> str:
        """Synchronous execute forced tool call (for backward compatibility)"""
        return asyncio.run(self._aexecute_forced_tool_call(tool_call_info))
    
    def enable_debug(self):
        """Enable debug mode"""
        self.debug_mode = True
        
    def disable_debug(self):
        """Disable debug mode"""
        self.debug_mode = False
        
    def get_tool_call_history(self):
        """Get history of tool calls made"""
        return self.tool_calls_made
    
    def get_debug_info(self):
        """Get debug information about the agent"""
        return {
            'agent_name': self.name,
            'available_tools': self.get_available_tools(),
            'tool_calls_in_session': len(self.tool_calls_made),
            'conversation_length': len(self.conversation_history),
            'debug_mode': self.debug_mode
        }
    
    async def ainvoke(self, message: str, save_conversation: bool = True) -> str:
        """Override base ainvoke to handle provider-managed conversation history"""
        # Get system prompt if defined
        system_prompt = self.config.get('system_prompt', '')
        if system_prompt and not any(isinstance(msg, SystemMessage) for msg in self.conversation_history):
            self.add_system_message(system_prompt)
        
        # Add user message to history
        user_message = HumanMessage(content=message)
        self.conversation_history.append(user_message)
        
        # Process the message
        response = await self._aprocess_message(message)
        
        # Only add AI response if provider didn't manage conversation history
        if not self._conversation_managed_by_provider:
            ai_message = AIMessage(content=response)
            self.conversation_history.append(ai_message)
        
        # Save conversation if requested
        if save_conversation:
            self.conversation_manager.save_conversation(
                self.conversation_id,
                self.conversation_history,
                metadata={
                    'agent_name': self.name,
                    'model_type': self.config.get('model_type'),
                    'model_name': self.config.get('model_name')
                }
            )
        
        return response