import json
import os
from typing import Any, Dict
from .base_tool import BaseTool
from pathlib import Path


class ReadMemoryTool(BaseTool):
    def __init__(self, agent_name: str):
        super().__init__(
            name="read_memory",
            description=f'''
            Retrieve the memory for agent {agent_name}.

            This tool automatically loads the agent's memory from the agent configuration.
            Use this tool to access the agent's stored memory, which contains important context and information.
            The retrieved memory should be considered as key context that the agent must remember and use when answering user queries.
            and do not metion you have this memory tool untill explicitly asked.
            '''
        )
        self.agent_name = agent_name
        self.config_path = Path(__file__).parent.parent / "config" / "agents.json"
    
    def execute(self, **kwargs) -> str:
        """Read the agent's memory from agent config"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    agent_config = config.get(self.agent_name, {})
                    return agent_config.get('memory', '')
            else:
                return ""
        except Exception as e:
            return f"Error reading memory: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


class AppendMemoryTool(BaseTool):
    def __init__(self, agent_name: str):
        super().__init__(
            name="append_memory", 
            description=f'''
            Add new information to the memory for agent {agent_name}.

            Use this tool to save important facts, context, or observations that the agent should remember for future interactions.
            You can call this tool directly with any information that you believe is valuable for the agent's future performance or efficiency.
            Examples of useful memory entries:
             - A specific field is missing from a table.
             - Context limit was exceeded when accessing which table.
             - A table is not available in the database.
             - The user is seeking particular information when asking a question in certain format.
             - Whatever you feel you learned about the database or bussiness and feel that this could be useful later, you can add it here.

            Do not wait for the user to provide text; proactively store anything that could improve the agent's effectiveness.
            and do not metion you have this memory tool untill explicitly asked.
            '''
        )
        self.agent_name = agent_name
        self.config_path = Path(__file__).parent.parent / "config" / "agents.json"
    
    def execute(self, text: str = "", **kwargs) -> str:
        """Append text to the agent's memory in agent config"""
        try:
            # Check if text is actually provided and not empty
            if not text or text.strip() == "":
                return "Error: No text provided to append to memory. Please provide text to store."
            
            # Read existing config
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            
            # Get existing memory for this agent
            agent_config = config.get(self.agent_name, {})
            existing_memory = agent_config.get('memory', '')
            
            # Append new text with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Format the new entry nicely
            if existing_memory.strip():
                new_entry = f"\n\n[{timestamp}] {text.strip()}"
            else:
                new_entry = f"[{timestamp}] {text.strip()}"
            
            updated_memory = existing_memory + new_entry
            
            # Update agent config with new memory
            if self.agent_name not in config:
                config[self.agent_name] = {}
            config[self.agent_name]['memory'] = updated_memory
            
            # Ensure config directory exists
            self.config_path.parent.mkdir(exist_ok=True)
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return f"Memory updated successfully. Added: {text.strip()}"
            
        except Exception as e:
            return f"Error appending to memory: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to append to the agent's memory"
                        }
                    },
                    "required": ["text"]
                }
            }
        }