import importlib
from typing import Dict, Optional

from agents.base_agent import BaseAgent
from config.config_manager import ConfigManager


class AgentRegistry:
    _instance = None
    _agents: Dict[str, BaseAgent] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
            cls._instance.config_manager = ConfigManager()
        return cls._instance
    
    def register_agent(self, name: str, agent: BaseAgent):
        """Register an agent in the registry"""
        self._agents[name] = agent
    
    def get_agent(self, name: str, conversation_id: Optional[str] = None) -> Optional[BaseAgent]:
        """Get an agent by name, creating a new instance for conversation isolation"""
        # Always create a new instance to avoid conversation interference
        return self.create_fresh_agent_instance(name, conversation_id)
    
    def list_agents(self) -> Dict[str, str]:
        """List all registered agents with their descriptions"""
        # For listing, we can use cached agents or create temporary instances
        if not self._agents:
            # Load agents to registry for listing purposes
            try:
                self.load_agents_from_config()
            except Exception:
                pass
        
        return {name: agent.get_description() for name, agent in self._agents.items()}
    
    def load_agents_from_config(self):
        """Load agents from configuration using ConfigManager"""
        agents_config = self.config_manager.get_all_agent_configs()
        
        for agent_name, agent_config in agents_config.items():
            # Validate configuration
            if not self.config_manager.validate_agent_config(agent_config):
                print(f"Warning: Invalid configuration for agent '{agent_name}', skipping.")
                continue
            
            agent_class_name = agent_config.get('class', 'CustomAgent')
            
            # Try to import the agent class
            try:
                module = importlib.import_module(f"agents.{agent_class_name.lower()}")
                agent_class = getattr(module, agent_class_name)
                
                # Create and register the agent
                agent = agent_class(agent_name, agent_config)
                self.register_agent(agent_name, agent)
                
            except (ImportError, AttributeError) as e:
                # Fallback to CustomAgent if specific class not found
                from agents.custom_agent import CustomAgent
                agent = CustomAgent(agent_name, agent_config)
                self.register_agent(agent_name, agent)
    
    def create_fresh_agent_instance(self, agent_name: str, conversation_id: Optional[str] = None) -> Optional[BaseAgent]:
        """Create a fresh agent instance for conversation isolation"""
        try:
            agents_config = self.config_manager.get_all_agent_configs()
            
            if agent_name not in agents_config:
                return None
            
            config = agents_config[agent_name].copy()  # Copy to avoid modifying original
            
            if not self.config_manager.validate_agent_config(config):
                return None
            
            return self.create_agent_from_config(agent_name, config, conversation_id)
            
        except Exception as e:
            print(f"Error creating fresh agent instance for '{agent_name}': {e}")
            return None
    
    def create_agent_from_config(self, agent_name: str, config: Dict, conversation_id: Optional[str] = None) -> BaseAgent:
        """Create a single agent from configuration"""
        if not self.config_manager.validate_agent_config(config):
            raise ValueError(f"Invalid configuration for agent '{agent_name}'")
        
        agent_class_name = config.get('class', 'CustomAgent')
        
        try:
            module = importlib.import_module(f"agents.{agent_class_name.lower()}")
            agent_class = getattr(module, agent_class_name)
            return agent_class(agent_name, config, conversation_id)
        except (ImportError, AttributeError):
            from agents.custom_agent import CustomAgent
            return CustomAgent(agent_name, config, conversation_id)