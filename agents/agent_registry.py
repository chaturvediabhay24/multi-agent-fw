import importlib
import json
import os
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
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self._agents.get(name)
    
    def list_agents(self) -> Dict[str, str]:
        """List all registered agents with their descriptions"""
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
    
    def create_agent_from_config(self, agent_name: str, config: Dict) -> BaseAgent:
        """Create a single agent from configuration"""
        if not self.config_manager.validate_agent_config(config):
            raise ValueError(f"Invalid configuration for agent '{agent_name}'")
        
        agent_class_name = config.get('class', 'CustomAgent')
        
        try:
            module = importlib.import_module(f"agents.{agent_class_name.lower()}")
            agent_class = getattr(module, agent_class_name)
            return agent_class(agent_name, config)
        except (ImportError, AttributeError):
            from agents.custom_agent import CustomAgent
            return CustomAgent(agent_name, config)