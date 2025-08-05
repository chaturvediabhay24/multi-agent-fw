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
        """Add or update agent configuration (runtime only)"""
        if 'agents' not in self._configs:
            self._configs['agents'] = {}
        self._configs['agents'][agent_name] = config
    
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