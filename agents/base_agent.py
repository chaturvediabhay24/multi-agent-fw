import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from conversations.conversation_manager import ConversationManager
from agents.model_providers.provider_factory import ModelProviderFactory


class BaseAgent(ABC):
    def __init__(self, 
                 name: str,
                 config: Dict[str, Any],
                 conversation_id: Optional[str] = None):
        self.name = name
        self.config = config
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.conversation_manager = ConversationManager()
        
        # Initialize model provider based on config
        self.model_provider = self._initialize_model_provider()
        
        # Load conversation history if exists
        self.conversation_history = self.conversation_manager.load_conversation(
            self.conversation_id
        )
        
    def _initialize_model_provider(self):
        """Initialize model provider using factory"""
        model_type = self.config.get('model_type', 'openai')
        model_name = self.config.get('model_name', 'gpt-3.5-turbo')
        
        return ModelProviderFactory.create_provider(
            provider_type=model_type,
            model_name=model_name
        )
    
    def switch_model(self, model_type: str, model_name: str):
        """Switch to a different model while maintaining conversation history"""
        self.config['model_type'] = model_type
        self.config['model_name'] = model_name
        self.model_provider = self._initialize_model_provider()
    
    def add_system_message(self, content: str):
        """Add a system message to the conversation"""
        message = SystemMessage(content=content)
        self.conversation_history.append(message)
        
    def invoke(self, message: str, save_conversation: bool = True) -> str:
        """Main method to invoke the agent with a message"""
        # Add user message to history
        user_message = HumanMessage(content=message)
        self.conversation_history.append(user_message)
        
        # Get system prompt if defined
        system_prompt = self.config.get('system_prompt', '')
        if system_prompt and not any(isinstance(msg, SystemMessage) for msg in self.conversation_history):
            self.add_system_message(system_prompt)
        
        # Process the message (can be overridden by subclasses)
        response = self._process_message(message)
        
        # Add AI response to history
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
    
    def _process_message(self, message: str) -> str:
        """Process the message using the configured model provider"""
        response = self.model_provider.invoke(self.conversation_history)
        return response
    
    def call_agent(self, agent_name: str, message: str) -> str:
        """Call another agent as a tool"""
        from agents.agent_registry import AgentRegistry
        
        registry = AgentRegistry()
        other_agent = registry.get_agent(agent_name)
        
        if not other_agent:
            return f"Agent '{agent_name}' not found"
        
        response = other_agent.invoke(message)
        return response
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools for this agent"""
        return self.config.get('tools', [])
    
    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what this agent does"""
        pass