"""
API Router for Multi-Agent Framework

This module contains all the API endpoints for agent management, configuration, and chat functionality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import sys
from pathlib import Path

# Add the project root to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.agent_registry import AgentRegistry
from agents.custom_agent import CustomAgent
from conversations.conversation_manager import ConversationManager

# Create API router
router = APIRouter(prefix="/api", tags=["API"])

# Data models
class AgentConfig(BaseModel):
    class_name: str = "CustomAgent"
    description: str
    model_type: str
    model_name: str
    system_prompt: str
    tools: List[str] = []
    parallel_tools: bool = True
    max_parallel_tools: int = 3
    debug: bool = False

class CreateAgentRequest(BaseModel):
    agent_name: str
    config: AgentConfig

class ChatMessage(BaseModel):
    agent_name: str
    message: str
    conversation_id: Optional[str] = None
    debug: bool = False

class SwitchModelRequest(BaseModel):
    agent_name: str
    model_type: str
    model_name: str
    conversation_id: Optional[str] = None

# Configuration paths
AGENTS_CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.json"
PROVIDERS_CONFIG_PATH = Path(__file__).parent.parent / "config" / "model_providers.json"

# Global registry for chat functionality
registry = AgentRegistry()
conversation_manager = ConversationManager()

def load_agents_config():
    """Load existing agents configuration"""
    try:
        if AGENTS_CONFIG_PATH.exists():
            with open(AGENTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading config: {str(e)}")

def save_agents_config(config_data):
    """Save agents configuration to file"""
    try:
        # Ensure config directory exists
        AGENTS_CONFIG_PATH.parent.mkdir(exist_ok=True)
        
        with open(AGENTS_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving config: {str(e)}")

def load_providers_config():
    """Load model providers configuration"""
    try:
        if PROVIDERS_CONFIG_PATH.exists():
            with open(PROVIDERS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Return default config if file doesn't exist
        return {
            "providers": {
                "openai": ["gpt-4o", "gpt-4"]
            },
            "default_provider": "openai",
            "default_model": "gpt-4o"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading providers config: {str(e)}")

# API Endpoints

@router.post("/reload-agents")
async def reload_agents():
    """Reload agents from configuration (useful after config changes)"""
    try:
        # Clear existing agents
        registry._agents.clear()
        
        # Reload from config
        registry.load_agents_from_config()
        
        agent_count = len(registry._agents)
        agent_names = list(registry._agents.keys())
        
        return {
            "message": f"Successfully reloaded {agent_count} agents",
            "agents": agent_names
        }
    except Exception as e:
        import traceback
        print(f"Error reloading agents: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error reloading agents: {str(e)}")

@router.get("/agents")
async def get_agents():
    """Get all existing agents"""
    config = load_agents_config()
    return {"agents": config}

@router.post("/agents")
async def create_agent(request: CreateAgentRequest):
    """Create a new agent and add it to the configuration"""
    
    # Validate agent name
    if not request.agent_name or not request.agent_name.strip():
        raise HTTPException(status_code=400, detail="Agent name is required")
    
    agent_name = request.agent_name.strip()
    
    # Load existing configuration
    config = load_agents_config()
    
    # Check if agent already exists
    if agent_name in config:
        raise HTTPException(status_code=409, detail=f"Agent '{agent_name}' already exists")
    
    # Convert Pydantic model to dict and format for agents.json
    agent_config = {
        "class": request.config.class_name,
        "description": request.config.description,
        "model_type": request.config.model_type,
        "model_name": request.config.model_name,
        "system_prompt": request.config.system_prompt,
        "tools": request.config.tools,
        "parallel_tools": request.config.parallel_tools,
        "max_parallel_tools": request.config.max_parallel_tools
    }
    
    # Add debug field only if it's True
    if request.config.debug:
        agent_config["debug"] = True
    
    # Add new agent to configuration
    config[agent_name] = agent_config
    
    # Save updated configuration
    save_agents_config(config)
    
    return {
        "message": f"Agent '{agent_name}' created successfully",
        "agent": {agent_name: agent_config}
    }

@router.put("/agents/{agent_name}")
async def update_agent(agent_name: str, config: AgentConfig):
    """Update an existing agent configuration"""
    
    # Load existing configuration
    agents_config = load_agents_config()
    
    # Check if agent exists
    if agent_name not in agents_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Update agent configuration
    agent_config = {
        "class": config.class_name,
        "description": config.description,
        "model_type": config.model_type,
        "model_name": config.model_name,
        "system_prompt": config.system_prompt,
        "tools": config.tools,
        "parallel_tools": config.parallel_tools,
        "max_parallel_tools": config.max_parallel_tools
    }
    
    # Add debug field only if it's True
    if config.debug:
        agent_config["debug"] = True
    
    agents_config[agent_name] = agent_config
    
    # Save updated configuration
    save_agents_config(agents_config)
    
    return {
        "message": f"Agent '{agent_name}' updated successfully",
        "agent": {agent_name: agent_config}
    }

@router.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str):
    """Delete an agent from the configuration"""
    
    # Load existing configuration
    config = load_agents_config()
    
    # Check if agent exists
    if agent_name not in config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Remove agent from configuration
    del config[agent_name]
    
    # Save updated configuration
    save_agents_config(config)
    
    return {"message": f"Agent '{agent_name}' deleted successfully"}

@router.get("/providers")
async def get_providers():
    """Get available model providers and their models"""
    providers_config = load_providers_config()
    return providers_config

@router.get("/tools")
async def get_available_tools():
    """Get list of available tools from the tools directory"""
    tools_dir = Path(__file__).parent.parent / "tools"
    available_tools = []
    
    if tools_dir.exists():
        for tool_file in tools_dir.glob("*_tool.py"):
            tool_name = tool_file.stem.replace("_tool", "")
            available_tools.append(tool_name)
    
    return {"tools": available_tools}

# Chat functionality endpoints

@router.post("/chat")
async def chat_with_agent(message: ChatMessage):
    """Send a message to an agent and get response"""
    try:
        # Load agents if not already loaded
        if not registry._agents:
            print(f"Loading agents from config...")
            registry.load_agents_from_config()
            print(f"Loaded {len(registry._agents)} agents: {list(registry._agents.keys())}")
        
        # Get the agent
        agent = registry.get_agent(message.agent_name)
        if not agent:
            available_agents = list(registry._agents.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{message.agent_name}' not found. Available agents: {available_agents}"
            )
        
        # Set conversation ID if provided
        if message.conversation_id:
            agent.conversation_id = message.conversation_id
            # Load existing conversation history
            try:
                agent.conversation_history = agent.conversation_manager.load_conversation(message.conversation_id)
            except Exception as e:
                print(f"Could not load conversation {message.conversation_id}: {e}")
                pass  # If conversation doesn't exist, start fresh
        
        # Set debug mode if requested
        if hasattr(agent, 'debug_mode'):
            if message.debug and not agent.debug_mode:
                agent.enable_debug()
            elif not message.debug and agent.debug_mode:
                agent.disable_debug()
        
        # Send message and get response
        response = await agent.ainvoke(message.message)
        
        # Extract tool calls if available
        tool_calls = []
        if hasattr(agent, 'get_tool_call_history'):
            recent_calls = agent.get_tool_call_history()
            # Get only the most recent tool calls from this invocation
            if recent_calls:
                tool_calls = recent_calls[-3:]  # Last 3 calls as example
        
        return {
            "response": response,
            "conversation_id": agent.conversation_id,
            "tool_calls": tool_calls
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        print(f"Error in chat_with_agent: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.post("/switch-model")
async def switch_agent_model(request: SwitchModelRequest):
    """Switch the model for an agent"""
    try:
        # Load agents if not already loaded
        if not registry._agents:
            registry.load_agents_from_config()
        
        # Get the agent
        agent = registry.get_agent(request.agent_name)
        if not agent:
            available_agents = list(registry._agents.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{request.agent_name}' not found. Available agents: {available_agents}"
            )
        
        # Set conversation ID if provided
        if request.conversation_id:
            agent.conversation_id = request.conversation_id
        
        # Switch model
        agent.switch_model(request.model_type, request.model_name)
        
        return {
            "message": f"Switched {request.agent_name} to {request.model_type} - {request.model_name}",
            "agent": request.agent_name,
            "model_type": request.model_type,
            "model_name": request.model_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in switch_agent_model: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error switching model: {str(e)}")

@router.get("/conversations/{agent_name}")
async def get_agent_conversations(agent_name: str):
    """Get conversations for a specific agent"""
    try:
        conversations = conversation_manager.get_conversations_by_agent(agent_name)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading conversations: {str(e)}")

@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    try:
        conversation = conversation_manager.load_conversation(conversation_id)
        return {"conversation": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading conversation: {str(e)}")