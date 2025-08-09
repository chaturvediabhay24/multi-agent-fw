import json
import os
from typing import Any, Dict
from .base_tool import BaseTool


class ReadMemoryTool(BaseTool):
    def __init__(self, agent_name: str):
        super().__init__(
            name="read_memory",
            description=f'''
            Retrieve the memory for agent {agent_name}.

            This tool automatically loads the agent's memory file at the start of a conversation if it is not already loaded.
            Use this tool to access the agent's stored memory, which contains important context and information.
            The retrieved memory should be considered as key context that the agent must remember and use when answering user queries.
            and do not metion you have this memory tool untill explicitly asked.
            '''
        )
        self.agent_name = agent_name
        self.memory_file = f"agent_memories/{agent_name}.json"
    
    def execute(self, **kwargs) -> str:
        """Read the agent's memory file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    memory_data = json.load(f)
                    return memory_data.get('memory', '')
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

            Do not wait for the user to provide text; proactively store anything that could improve the agent's effectiveness.
            and do not metion you have this memory tool untill explicitly asked.
            '''
        )
        self.agent_name = agent_name
        self.memory_file = f"agent_memories/{agent_name}.json"
    
    def execute(self, text: str = "", **kwargs) -> str:
        """Append text to the agent's memory file"""
        try:
            # Check if text is actually provided and not empty
            if not text or text.strip() == "":
                return "Error: No text provided to append to memory. Please provide text to store."
            
            # Ensure the directory exists
            os.makedirs("agent_memories", exist_ok=True)
            
            # Read existing memory
            existing_memory = ""
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    memory_data = json.load(f)
                    existing_memory = memory_data.get('memory', '')
            
            # Append new text with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Format the new entry nicely
            if existing_memory.strip():
                new_entry = f"\n\n[{timestamp}] {text.strip()}"
            else:
                new_entry = f"[{timestamp}] {text.strip()}"
            
            updated_memory = existing_memory + new_entry
            
            # Save updated memory
            memory_data = {
                'agent_name': self.agent_name,
                'memory': updated_memory,
                'last_updated': timestamp
            }
            
            with open(self.memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
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