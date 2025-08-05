import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from conversations.tool_message import ToolCallMessage


class ConversationManager:
    def __init__(self, conversations_dir: str = "conversations"):
        self.conversations_dir = conversations_dir
        self.sessions_dir = os.path.join(conversations_dir, "sessions")
        os.makedirs(self.conversations_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    def save_conversation(self, 
                         conversation_id: str, 
                         messages: List[BaseMessage], 
                         metadata: Optional[Dict[str, Any]] = None):
        """Save conversation to file"""
        conversation_data = {
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
            'messages': []
        }
        
        # Convert messages to serializable format
        for message in messages:
            msg_data = {
                'type': message.__class__.__name__,
                'content': message.content,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add tool-specific metadata if it's a ToolCallMessage
            if isinstance(message, ToolCallMessage):
                msg_data.update({
                    'tool_name': message.tool_name,
                    'parameters': message.parameters,
                    'result': message.result,
                    'success': message.success
                })
            
            # Add tool_calls if it's an AIMessage with tool calls
            if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
                msg_data['tool_calls'] = [
                    {
                        'name': tc.get('name', ''),
                        'args': tc.get('args', {}),
                        'id': tc.get('id', '')
                    } for tc in message.tool_calls
                ]
            
            conversation_data['messages'].append(msg_data)
        
        # Save to sessions folder with organized structure
        file_path = os.path.join(self.sessions_dir, f"{conversation_id}.json")
        with open(file_path, 'w') as f:
            json.dump(conversation_data, f, indent=2)
    
    def load_conversation(self, conversation_id: str) -> List[BaseMessage]:
        """Load conversation from file"""
        # Find the conversation file (could be in date subfolders)
        file_path = self._find_conversation_file(conversation_id)
        
        if not file_path or not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r') as f:
            conversation_data = json.load(f)
        
        messages = []
        for msg_data in conversation_data.get('messages', []):
            msg_type = msg_data['type']
            content = msg_data['content']
            
            if msg_type == 'HumanMessage':
                messages.append(HumanMessage(content=content))
            elif msg_type == 'AIMessage':
                messages.append(AIMessage(content=content))
            elif msg_type == 'SystemMessage':
                messages.append(SystemMessage(content=content))
            elif msg_type == 'ToolCallMessage':
                messages.append(ToolCallMessage(
                    tool_name=msg_data['tool_name'],
                    parameters=msg_data['parameters'],
                    result=msg_data['result'],
                    success=msg_data['success']
                ))
        
        return messages
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all available conversations"""
        conversations = []
        
        # Check both sessions folder and old location
        search_dirs = [self.sessions_dir, self.conversations_dir]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            
            # Recursively search for conversation files (including date subfolders)
            self._scan_directory_for_conversations(search_dir, conversations, search_dir)
        
        return sorted(conversations, key=lambda x: x['timestamp'], reverse=True)
    
    def _scan_directory_for_conversations(self, directory: str, conversations: List, base_dir: str):
        """Recursively scan directory for conversation files"""
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            if os.path.isdir(item_path):
                # Recursively scan subdirectories
                self._scan_directory_for_conversations(item_path, conversations, base_dir)
            elif item.endswith('.json') and item not in ['__init__.py']:
                try:
                    with open(item_path, 'r') as f:
                        conversation_data = json.load(f)
                    
                    # Avoid duplicates
                    conv_id = conversation_data.get('conversation_id')
                    if conv_id and not any(c['conversation_id'] == conv_id for c in conversations):
                        conversations.append({
                            'conversation_id': conv_id,
                            'timestamp': conversation_data.get('timestamp', ''),
                            'metadata': conversation_data.get('metadata', {}),
                            'message_count': len(conversation_data.get('messages', [])),
                            'location': 'sessions' if base_dir == self.sessions_dir else 'old',
                            'file_path': item_path
                        })
                except (json.JSONDecodeError, KeyError):
                    # Skip invalid files
                    continue
    
    def _find_conversation_file(self, conversation_id: str) -> str:
        """Find conversation file by ID (searches recursively)"""
        filename = f"{conversation_id}.json"
        
        # Search in sessions directory (including subdirectories)
        def search_directory(directory):
            if not os.path.exists(directory):
                return None
                
            for root, dirs, files in os.walk(directory):
                if filename in files:
                    return os.path.join(root, filename)
            return None
        
        # First try sessions directory
        file_path = search_directory(self.sessions_dir)
        if file_path:
            return file_path
        
        # Fallback to old location
        old_path = os.path.join(self.conversations_dir, filename)
        if os.path.exists(old_path):
            return old_path
        
        return None
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        file_path = self._find_conversation_file(conversation_id)
        
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        
        return False
    
    def migrate_conversations(self):
        """Migrate old conversations to sessions folder"""
        migrated_count = 0
        
        if not os.path.exists(self.conversations_dir):
            return migrated_count
        
        for filename in os.listdir(self.conversations_dir):
            if filename.endswith('.json') and filename not in ['__init__.py']:
                old_path = os.path.join(self.conversations_dir, filename)
                new_path = os.path.join(self.sessions_dir, filename)
                
                # Skip if it's not a conversation file or already exists in sessions
                if os.path.exists(new_path):
                    continue
                
                try:
                    # Verify it's a valid conversation file
                    with open(old_path, 'r') as f:
                        data = json.load(f)
                    
                    if 'conversation_id' in data and 'messages' in data:
                        # Move to sessions folder
                        os.rename(old_path, new_path)
                        migrated_count += 1
                        
                except (json.JSONDecodeError, KeyError, OSError):
                    # Skip invalid files
                    continue
        
        return migrated_count
    
    def organize_conversations_by_date(self):
        """Organize conversations into date-based subfolders"""
        from datetime import datetime
        
        if not os.path.exists(self.sessions_dir):
            return 0
        
        organized_count = 0
        
        for filename in os.listdir(self.sessions_dir):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(self.sessions_dir, filename)
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', '')
                if timestamp:
                    # Parse timestamp and create date folder
                    date_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    date_folder = date_obj.strftime('%Y-%m-%d')
                    
                    # Create date subfolder
                    date_dir = os.path.join(self.sessions_dir, date_folder)
                    os.makedirs(date_dir, exist_ok=True)
                    
                    # Move file to date folder
                    new_path = os.path.join(date_dir, filename)
                    if not os.path.exists(new_path):
                        os.rename(file_path, new_path)
                        organized_count += 1
                        
            except (json.JSONDecodeError, ValueError, OSError):
                # Skip problematic files
                continue
        
        return organized_count
    
    def get_conversations_by_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get conversations for a specific agent"""
        all_conversations = self.list_conversations()
        agent_conversations = []
        
        for conv in all_conversations:
            metadata = conv.get('metadata', {})
            if metadata.get('agent_name') == agent_name:
                agent_conversations.append(conv)
        
        return agent_conversations
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all conversations"""
        conversations = self.list_conversations()
        
        summary = {
            'total_conversations': len(conversations),
            'total_messages': sum(c['message_count'] for c in conversations),
            'agents_used': set(),
            'models_used': set(),
            'date_range': {'earliest': None, 'latest': None}
        }
        
        timestamps = []
        for conv in conversations:
            metadata = conv.get('metadata', {})
            if 'agent_name' in metadata:
                summary['agents_used'].add(metadata['agent_name'])
            if 'model_type' in metadata:
                summary['models_used'].add(f"{metadata['model_type']}-{metadata.get('model_name', '')}")
            
            if conv['timestamp']:
                timestamps.append(conv['timestamp'])
        
        if timestamps:
            timestamps.sort()
            summary['date_range']['earliest'] = timestamps[0]
            summary['date_range']['latest'] = timestamps[-1]
        
        # Convert sets to lists for JSON serialization
        summary['agents_used'] = list(summary['agents_used'])
        summary['models_used'] = list(summary['models_used'])
        
        return summary