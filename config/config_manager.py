import json
import os
from typing import Dict, Any, List, Optional


class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all configuration files"""
        if not os.path.exists(self.config_dir):
            return
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                config_name = filename[:-5]  # Remove .json extension
                config_path = os.path.join(self.config_dir, filename)
                
                try:
                    with open(config_path, 'r') as f:
                        self._configs[config_name] = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load config '{filename}': {e}")
        
        # Load agents from agents directory if it exists
        self._load_agents_from_directory()
    
    def _load_agents_from_directory(self):
        """Load individual agent configs from agents directory"""
        agents_dir = os.path.join(self.config_dir, "agents")
        if not os.path.exists(agents_dir):
            return
        
        # Initialize agents config if not exists
        if 'agents' not in self._configs:
            self._configs['agents'] = {}
        
        # Load each agent file
        for filename in os.listdir(agents_dir):
            if filename.endswith('.json'):
                agent_name = filename[:-5]  # Remove .json extension
                agent_path = os.path.join(agents_dir, filename)
                
                try:
                    with open(agent_path, 'r') as f:
                        agent_config = json.load(f)
                        self._configs['agents'][agent_name] = agent_config
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load agent config '{filename}': {e}")
    
    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent"""
        agents_config = self._configs.get('agents', {})
        return agents_config.get(agent_name)
    
    def get_all_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all agent configurations"""
        return self._configs.get('agents', {})
    
    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific tool"""
        tools_config = self._configs.get('tools', {})
        return tools_config.get(tool_name)
    
    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model"""
        models_config = self._configs.get('models', {})
        return models_config.get(model_name)
    
    def get_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get any configuration by name"""
        return self._configs.get(config_name)
    
    def reload_configs(self):
        """Reload all configurations"""
        self._configs.clear()
        self._load_configs()
    
    def add_agent_config(self, agent_name: str, config: Dict[str, Any]):
        """Add or update agent configuration and save to individual file"""
        if 'agents' not in self._configs:
            self._configs['agents'] = {}
        self._configs['agents'][agent_name] = config
        
        # Save to individual agent file
        self._save_agent_config(agent_name, config)
    
    def _save_agent_config(self, agent_name: str, config: Dict[str, Any]):
        """Save individual agent config to file"""
        agents_dir = os.path.join(self.config_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        agent_file_path = os.path.join(agents_dir, f"{agent_name}.json")
        try:
            with open(agent_file_path, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save agent config '{agent_name}': {e}")
    
    def remove_agent_config(self, agent_name: str):
        """Remove agent configuration from memory and file"""
        # Remove from memory
        if 'agents' in self._configs and agent_name in self._configs['agents']:
            del self._configs['agents'][agent_name]
        
        # Remove file
        agents_dir = os.path.join(self.config_dir, "agents")
        agent_file_path = os.path.join(agents_dir, f"{agent_name}.json")
        
        try:
            if os.path.exists(agent_file_path):
                os.remove(agent_file_path)
        except OSError as e:
            print(f"Warning: Failed to remove agent config file '{agent_name}': {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available model providers"""
        from agents.model_providers.provider_factory import ModelProviderFactory
        return list(ModelProviderFactory.get_available_providers().keys())
    
    def validate_agent_config(self, config: Dict[str, Any]) -> bool:
        """Validate agent configuration"""
        required_fields = ['model_type', 'model_name']
        
        for field in required_fields:
            if field not in config:
                return False
        
        # Check if model type is available
        available_models = self.get_available_models()
        if config['model_type'] not in available_models:
            return False
        
        return True