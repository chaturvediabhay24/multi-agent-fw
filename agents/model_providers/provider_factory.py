from typing import Dict, Type
from .base_provider import BaseModelProvider
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider


class ModelProviderFactory:
    """Factory for creating model providers"""
    
    _providers: Dict[str, Type[BaseModelProvider]] = {
        'openai': OpenAIProvider,
        'claude': ClaudeProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, model_name: str, **kwargs) -> BaseModelProvider:
        """Create a model provider instance"""
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider type: {provider_type}. Available: {list(cls._providers.keys())}")
        
        provider_class = cls._providers[provider_type]
        return provider_class(model_name=model_name, **kwargs)
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[BaseModelProvider]):
        """Register a new provider type"""
        cls._providers[provider_type] = provider_class
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, bool]:
        """Get available providers and their availability status"""
        available = {}
        for provider_type, provider_class in cls._providers.items():
            try:
                provider = provider_class(model_name="test")
                available[provider_type] = provider.is_available()
            except Exception:
                available[provider_type] = False
        return available