"""
API Router for Multi-Agent Framework

This module contains all the API endpoints for agent management, configuration, and chat functionality.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.agent_registry import AgentRegistry
from config.config_manager import ConfigManager

# Memory-efficient tool call streaming using weak references and automatic cleanup
import weakref
from collections import defaultdict
import time

# Only keep active SSE connections, auto-cleanup on disconnect
active_streams = weakref.WeakValueDictionary()  # conversation_id -> SSEStream instance

class ToolCallStream:
    """Memory-efficient tool call stream handler"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.queue = asyncio.Queue(maxsize=10)  # Small buffer
        self.last_activity = time.time()
        self.is_active = True
        
        # Register this stream
        active_streams[conversation_id] = self
        
    async def send_event(self, event: dict):
        """Send event to stream if active"""
        if not self.is_active:
            return
            
        self.last_activity = time.time()
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest event to make room
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(event)
            except asyncio.QueueEmpty:
                pass
    
    async def get_events(self):
        """Generator for SSE events"""
        try:
            while self.is_active:
                try:
                    # Wait for event with timeout for cleanup
                    event = await asyncio.wait_for(self.queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    self.last_activity = time.time()
                except asyncio.TimeoutError:
                    # Send keepalive and check if client is still connected
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                    
                    # Auto-cleanup old inactive streams
                    if time.time() - self.last_activity > 300:  # 5 minutes
                        break
                        
        except asyncio.CancelledError:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.is_active = False
        # Queue will be garbage collected automatically

def broadcast_tool_call_event(conversation_id: str, event: dict):
    """Efficiently broadcast to active stream only"""
    stream = active_streams.get(conversation_id)
    if stream:
        asyncio.create_task(stream.send_event(event))

def get_or_create_stream(conversation_id: str) -> ToolCallStream:
    """Get existing stream or create new one"""
    stream = active_streams.get(conversation_id)
    if stream is None or not stream.is_active:
        stream = ToolCallStream(conversation_id)
        # Start cleanup task when first stream is created
        start_cleanup_task()
    return stream

# Automatic cleanup task
async def cleanup_inactive_streams():
    """Periodic cleanup of inactive streams"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            current_time = time.time()
            
            # Find inactive streams (using list() to avoid dict size change during iteration)
            inactive_ids = []
            for conv_id, stream in list(active_streams.items()):
                if not stream.is_active or current_time - stream.last_activity > 300:  # 5 minutes
                    inactive_ids.append(conv_id)
            
            # Clean up inactive streams
            for conv_id in inactive_ids:
                stream = active_streams.get(conv_id)
                if stream:
                    stream.cleanup()
                    
        except Exception as e:
            print(f"Error in cleanup task: {e}")

# Start cleanup task when module loads
cleanup_task = None

def start_cleanup_task():
    """Start the cleanup task"""
    global cleanup_task
    if cleanup_task is None or cleanup_task.done():
        cleanup_task = asyncio.create_task(cleanup_inactive_streams())

# Cleanup task will be started lazily when first stream is created

from agents.custom_agent import CustomAgent
from conversations.conversation_manager import ConversationManager

# Create API router
router = APIRouter(prefix="/api", tags=["API"])

# Note: Cleanup task will start when first stream is created

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
    memory: str = ""

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

# Global configuration manager
config_manager = ConfigManager(str(Path(__file__).parent.parent / "config"))

# Global registry for chat functionality
registry = AgentRegistry()
conversation_manager = ConversationManager()

# Import authentication functions
from auth import is_session_valid

def is_authenticated(request: Request):
    """Check if user is authenticated"""
    session_id = request.headers.get("x-session-id") or request.cookies.get("session-id")
    print(f"DEBUG API: Headers received: {dict(request.headers)}")
    print(f"DEBUG API: Session ID from headers: {request.headers.get('x-session-id')}")
    print(f"DEBUG API: Session ID from cookies: {request.cookies.get('session-id')}")
    print(f"DEBUG API: Final session ID: {session_id}")
    result = session_id and is_session_valid(session_id)
    print(f"DEBUG API: Authentication result: {result}")
    return result

def require_auth(request: Request):
    """Dependency to require authentication for config operations"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True

def load_agents_config():
    """Load existing agents configuration"""
    try:
        return config_manager.get_all_agent_configs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading config: {str(e)}")


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

@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get a specific agent configuration"""
    config = load_agents_config()
    
    # Check if agent exists
    if agent_name not in config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    return {"agent": {agent_name: config[agent_name]}}

@router.post("/agents")
async def create_agent(request: CreateAgentRequest, auth: bool = Depends(require_auth)):
    """Create a new agent and add it to the configuration"""
    
    # Validate agent name
    if not request.agent_name or not request.agent_name.strip():
        raise HTTPException(status_code=400, detail="Agent name is required")
    
    agent_name = request.agent_name.strip()
    
    # Check if agent already exists
    existing_config = config_manager.get_agent_config(agent_name)
    if existing_config:
        raise HTTPException(status_code=409, detail=f"Agent '{agent_name}' already exists")
    
    # Convert Pydantic model to dict and format for agent config
    agent_config = {
        "class": request.config.class_name,
        "description": request.config.description,
        "model_type": request.config.model_type,
        "model_name": request.config.model_name,
        "system_prompt": request.config.system_prompt,
        "tools": request.config.tools,
        "parallel_tools": request.config.parallel_tools,
        "max_parallel_tools": request.config.max_parallel_tools,
        "memory": request.config.memory
    }
    
    # Add debug field only if it's True
    if request.config.debug:
        agent_config["debug"] = True
    
    # Save agent configuration using ConfigManager
    config_manager.add_agent_config(agent_name, agent_config)
    
    return {
        "message": f"Agent '{agent_name}' created successfully",
        "agent": {agent_name: agent_config}
    }

@router.put("/agents/{agent_name}")
async def update_agent(agent_name: str, config: AgentConfig, auth: bool = Depends(require_auth)):
    """Update an existing agent configuration"""
    
    # Check if agent exists
    existing_config = config_manager.get_agent_config(agent_name)
    if not existing_config:
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
        "max_parallel_tools": config.max_parallel_tools,
        "memory": config.memory
    }
    
    # Add debug field only if it's True
    if config.debug:
        agent_config["debug"] = True
    
    # Save updated agent configuration using ConfigManager
    config_manager.add_agent_config(agent_name, agent_config)
    
    return {
        "message": f"Agent '{agent_name}' updated successfully",
        "agent": {agent_name: agent_config}
    }

@router.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str, auth: bool = Depends(require_auth)):
    """Delete an agent from the configuration"""
    
    # Check if agent exists
    existing_config = config_manager.get_agent_config(agent_name)
    if not existing_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Remove agent configuration using ConfigManager
    config_manager.remove_agent_config(agent_name)
    
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
        
        # Set conversation ID if provided and it's not an auth session
        if message.conversation_id and not message.conversation_id.startswith('auth_'):
            agent.conversation_id = message.conversation_id
            # Load existing conversation history
            try:
                agent.conversation_history = agent.conversation_manager.load_conversation(message.conversation_id)
            except Exception as e:
                print(f"Could not load conversation {message.conversation_id}: {e}")
                pass  # If conversation doesn't exist, start fresh
        else:
            # Generate a new conversation ID for new conversations
            import uuid
            agent.conversation_id = f"conv_{uuid.uuid4().hex[:8]}_{message.agent_name}"
            agent.conversation_history = []
        
        # Set debug mode if requested
        if hasattr(agent, 'debug_mode'):
            if message.debug and not agent.debug_mode:
                agent.enable_debug()
            elif not message.debug and agent.debug_mode:
                agent.disable_debug()
        
        # Send message and get response
        response = await agent.ainvoke(message.message)
        
        # Tool calls are now handled in real-time via SSE events
        # No need to extract them here
        
        return {
            "response": response,
            "conversation_id": agent.conversation_id
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
        
        # Set conversation ID if provided and it's not an auth session
        if request.conversation_id and not request.conversation_id.startswith('auth_'):
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

@router.get("/tool-calls/stream/{conversation_id}")
async def stream_tool_calls(conversation_id: str):
    """Memory-efficient tool call streaming using SSE"""
    
    stream = get_or_create_stream(conversation_id)
    
    return StreamingResponse(
        stream.get_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.post("/kill-conversation/{conversation_id}")
async def kill_conversation(conversation_id: str):
    """Kill/stop an active conversation and agent processing"""
    try:
        # Get the active stream for this conversation
        stream = active_streams.get(conversation_id)
        if stream:
            # Send kill signal to the stream
            await stream.send_event({
                "type": "conversation_killed", 
                "conversation_id": conversation_id,
                "message": "Conversation terminated by user"
            })
            # Mark stream as inactive to stop processing
            stream.cleanup()
        
        # Look for any active agent processing for this conversation
        # and signal termination if the agent supports it
        agent = None
        if registry._agents:
            for agent_name, agent_instance in registry._agents.items():
                if hasattr(agent_instance, 'conversation_id') and agent_instance.conversation_id == conversation_id:
                    agent = agent_instance
                    break
        
        if agent and hasattr(agent, 'cancel_processing'):
            agent.cancel_processing()
        
        return {
            "message": f"Conversation {conversation_id} terminated successfully",
            "conversation_id": conversation_id,
            "status": "killed"
        }
        
    except Exception as e:
        import traceback
        print(f"Error killing conversation {conversation_id}: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error killing conversation: {str(e)}")