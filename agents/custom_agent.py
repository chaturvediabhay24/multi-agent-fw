import re
from typing import Dict, Any, List, Union
from agents.base_agent import BaseAgent
from tools.tool_registry import ToolRegistry
from tools.langchain_tool_adapter import LangChainToolAdapter
from conversations.tool_message import ToolCallMessage
from langchain_core.messages import ToolMessage, AIMessage


class CustomAgent(BaseAgent):
    def __init__(self, name: str, config: Dict[str, Any], conversation_id: str = None):
        super().__init__(name, config, conversation_id)
        self.tool_registry = ToolRegistry()
        self.debug_mode = False
        self.tool_calls_made = []
        
        # Load agent-specific tools
        agent_tools = self.get_available_tools()
        if agent_tools:
            self.tool_registry.load_tools_for_agent(agent_tools)
        
    def get_description(self) -> str:
        """Return a description of what this agent does"""
        return self.config.get('description', f'Custom agent: {self.name}')
    
    def _process_message(self, message: str) -> str:
        """Process message with structured tool calling"""
        available_tools = self.get_available_tools()
        self.tool_calls_made = []  # Reset tool calls for this message
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Available tools: {available_tools}")
        
        # Check if we should force tool usage (backward compatibility)
        forced_tool_call = self._detect_forced_tool_usage(message, available_tools)
        if forced_tool_call:
            if self.debug_mode:
                print(f"🔧 DEBUG: Forcing tool call: {forced_tool_call}")
            return self._execute_forced_tool_call(forced_tool_call, message)
        
        # Get tools for structured calling
        if available_tools and self.model_provider.supports_tool_calling():
            return self._process_with_structured_tools(message, available_tools)
        else:
            # Fallback to regular processing without tools
            return super()._process_message(message)
    
    def _process_with_structured_tools(self, message: str, available_tool_names: List[str]) -> str:
        """Process message using structured tool calling"""
        # Get tool instances
        tools = []
        for tool_name in available_tool_names:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool)
        
        if not tools:
            return super()._process_message(message)
        
        # Convert to LangChain tools
        langchain_tools = LangChainToolAdapter.convert_tools(tools)
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Converted {len(langchain_tools)} tools for structured calling")
        
        # Invoke model with tools
        response = self.model_provider.invoke_with_tools(
            self.conversation_history, 
            langchain_tools
        )
        
        if self.debug_mode:
            print(f"🔧 DEBUG: Model response type: {type(response)}")
        
        # Handle structured response
        if isinstance(response, dict) and 'tool_calls' in response:
            return self._handle_structured_tool_calls(response)
        else:
            # No tool calls, return regular response
            return str(response)
    
    def _handle_structured_tool_calls(self, response: Dict[str, Any]) -> str:
        """Handle structured tool calls from the model"""
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
        
        # Then process each tool call and create tool messages
        for tool_call in tool_calls:
            try:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_call_id = tool_call.get('id', '')
                
                if self.debug_mode:
                    print(f"🔧 DEBUG: Executing tool {tool_name} with args: {tool_args}")
                
                # Execute the tool
                result = self.tool_registry.execute_tool(tool_name, **tool_args)
                
                # Store tool call info
                tool_call_info = {
                    'tool_name': tool_name,
                    'params': tool_args,
                    'result': result,
                    'success': True
                }
                self.tool_calls_made.append(tool_call_info)
                
                # Create tool message for conversation history
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id
                )
                tool_messages.append(tool_message)
                
                # Format result for display
                if isinstance(result, dict) and 'success' in result:
                    if result['success']:
                        formatted_result = result.get('formatted_result', result.get('result', result))
                        tool_results.append(f"**{tool_name}**: {formatted_result}")
                    else:
                        tool_results.append(f"**{tool_name} Error**: {result.get('error', 'Unknown error')}")
                else:
                    tool_results.append(f"**{tool_name}**: {result}")
                    
            except Exception as e:
                if self.debug_mode:
                    print(f"🔧 DEBUG: Tool execution error: {str(e)}")
                
                # Store failed tool call
                tool_call_info = {
                    'tool_name': tool_call.get('name', 'unknown'),
                    'params': tool_call.get('args', {}),
                    'result': str(e),
                    'success': False
                }
                self.tool_calls_made.append(tool_call_info)
                
                # Create tool message for failed call
                tool_message = ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=tool_call.get('id', '')
                )
                tool_messages.append(tool_message)
                
                tool_results.append(f"**Tool Error**: {str(e)}")
        
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
    
    def _detect_forced_tool_usage(self, message: str, available_tools: list) -> dict:
        """Detect if we should force tool usage based on message content"""
        message_lower = message.lower()
        
        # Check for calculator tool usage
        if 'calculator' in available_tools:
            # Look for calculation keywords
            calc_keywords = ['calculate', 'compute', 'what is', 'what\'s', '*', '+', '-', '/', '^', 'sqrt', 'sin', 'cos', 'tan', '%']
            if any(keyword in message_lower for keyword in calc_keywords):
                # Try to extract mathematical expression
                # Simple patterns for common calculations
                import re
                
                # Pattern for "calculate X * Y" or "what is X + Y"
                calc_patterns = [
                    r'calculate\s+(.+)',
                    r'compute\s+(.+)', 
                    r'what\s+is\s+(.+)',
                    r'what\'s\s+(.+)',
                    r'execute\s+calculater?\s+to\s+find\s+(.+)',  # Handle "execute calculator to find"
                    r'find\s+(.+)',  # Handle "find X * Y"
                    r'^(.+)$'  # Fallback - treat entire message as expression if it contains math operators
                ]
                
                for pattern in calc_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        expression = match.group(1).strip()
                        # Clean up the expression
                        expression = expression.replace('?', '').strip()
                        if any(op in expression for op in ['*', '+', '-', '/', '^', '(', ')', 'sqrt', 'sin', 'cos']):
                            # Parse the expression into param1, param2, operator
                            parsed_params = self._parse_math_expression(expression)
                            if parsed_params:
                                if self.debug_mode:
                                    print(f"🔧 DEBUG: Parsed expression '{expression}' -> {parsed_params}")
                                return {
                                    'tool_name': 'calculator',
                                    'params': parsed_params,
                                    'original_message': message
                                }
                            else:
                                if self.debug_mode:
                                    print(f"🔧 DEBUG: Failed to parse expression: '{expression}'")
                                return None
        
        return None
    
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
    
    def _execute_forced_tool_call(self, tool_call_info: dict, original_message: str = None) -> str:
        """Execute a forced tool call and format the response"""
        tool_name = tool_call_info['tool_name']
        params = tool_call_info['params']
        
        try:
            # Execute the tool
            result = self.tool_registry.execute_tool(tool_name, **params)
            
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