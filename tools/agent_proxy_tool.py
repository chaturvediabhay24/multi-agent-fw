from typing import Dict, Any
from tools.base_tool import BaseTool
from agents.agent_registry import AgentRegistry


class AgentProxyTool(BaseTool):
    """Dynamic proxy tool that represents a specific agent"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.agent_registry = AgentRegistry()
        
        # Get description from agent's system prompt in config
        description = self._get_agent_description_from_config()
        
        super().__init__(
            name=agent_name,
            description=description
        )
    
    def _get_target_agent(self, conversation_id: str = None):
        """Get a fresh target agent instance for conversation isolation"""
        import uuid
        
        # Generate unique conversation ID for this tool call to ensure isolation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        # Always get a fresh instance to avoid conversation interference
        target_agent = self.agent_registry.get_agent(self.agent_name, conversation_id)
        
        if not target_agent:
            try:
                self.agent_registry.load_agents_from_config()
                target_agent = self.agent_registry.get_agent(self.agent_name, conversation_id)
            except Exception:
                pass
        
        return target_agent
    
    def _get_agent_description_from_config(self) -> str:
        """Get description from agent's system prompt in configuration"""
        try:
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            agent_configs = config_manager.get_all_agent_configs()
            
            if self.agent_name in agent_configs:
                agent_config = agent_configs[self.agent_name]
                system_prompt_raw = agent_config.get('system_prompt', '')
                
                # Handle both str and list of str for system_prompt
                if isinstance(system_prompt_raw, list):
                    system_prompt = '\n'.join(system_prompt_raw)
                else:
                    system_prompt = system_prompt_raw
                
                # Extract first sentence or first 100 characters as description
                if system_prompt:
                    # Get first sentence or first 100 chars
                    first_sentence = system_prompt.split('.')[0]
                    if len(first_sentence) > 100:
                        description = first_sentence[:100] + "..."
                    else:
                        description = first_sentence
                    
                    return f"Agent: {description}"
                else:
                    return f"Call the {self.agent_name} agent for specialized assistance"
            else:
                return f"Call the {self.agent_name} agent for specialized assistance"
                
        except Exception:
            return f"Call the {self.agent_name} agent for specialized assistance"
    
    async def aexecute(self, message=None, **kwargs) -> Dict[str, Any]:
        """
        Async execute a call to the target agent
        
        Args:
            message (str, optional): The message/task to send to the agent
            **kwargs: Additional parameters (may contain message in different forms)
        
        Returns:
            Dict containing the response and metadata
        """
        try:
            # Handle different ways the message might be passed
            if message is None:
                # Check if message is in kwargs
                message = kwargs.get('message')
                
            if message is None:
                # Check for other common parameter names
                message = kwargs.get('query') or kwargs.get('input') or kwargs.get('text')
            
            if message is None:
                # If still no message, check if kwargs has any string values
                for value in kwargs.values():
                    if isinstance(value, str) and len(value.strip()) > 0:
                        message = value
                        break
            
            if message is None or not message.strip():
                # If no specific message, provide a default greeting/query
                message = f"Hello, can you tell me what you can do and how you can help?"
            
            target_agent = self._get_target_agent()
            
            if not target_agent:
                return {
                    'success': False,
                    'error': f"Agent '{self.agent_name}' not found or not configured",
                    'formatted_result': f"Error: {self.agent_name} agent is not available"
                }
            
            # Call the target agent asynchronously with conversation isolation
            # Disable conversation saving to prevent cross-contamination
            response = await target_agent.ainvoke(str(message), save_conversation=False)
            
            # Get agent info for metadata
            agent_info = {
                'name': self.agent_name,
                'description': target_agent.get_description(),
                'model_type': target_agent.config.get('model_type', 'unknown'),
                'model_name': target_agent.config.get('model_name', 'unknown')
            }
            
            return {
                'success': True,
                'response': response,
                'agent_info': agent_info,
                'formatted_result': f"[{self.agent_name}]: {response}"
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                'success': False,
                'error': f"Error calling {self.agent_name}: {str(e)}",
                'formatted_result': f"Error calling {self.agent_name}: {str(e)}",
                'debug_info': error_details
            }
    
    def execute(self, message=None, **kwargs) -> Dict[str, Any]:
        """
        Synchronous execute (for backward compatibility) - runs async version
        """
        import asyncio
        return asyncio.run(self.aexecute(message, **kwargs))
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the schema for this agent proxy tool"""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string", 
                    "description": f"The specific question, task, or request to send to the {self.agent_name} agent. Be clear and specific about what you want the agent to do."
                }
            },
            "required": ["message"]
        }