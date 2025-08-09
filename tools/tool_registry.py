from typing import Dict, Optional, List

from tools.base_tool import BaseTool
from tools.tool_loader import ToolLoader


class ToolRegistry:
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    _available_tools: Dict[str, type] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._discover_available_tools()
            cls._instance._initialize_default_tools()
        return cls._instance
    
    def _discover_available_tools(self):
        """Discover all available tools dynamically"""
        # Discover tools from tools directory (now includes all tools)
        tools_discovered = ToolLoader.discover_tools("tools")
        self._available_tools.update(tools_discovered)
    
    def _initialize_default_tools(self):
        """Initialize commonly used tools"""
        default_tools = ['calculator', 'postgres_query']
        
        for tool_name in default_tools:
            if tool_name in self._available_tools:
                try:
                    tool_class = self._available_tools[tool_name]
                    tool_instance = tool_class()
                    self.register_tool(tool_name, tool_instance)
                except Exception as e:
                    print(f"Warning: Failed to initialize default tool '{tool_name}': {e}")
    
    def register_tool(self, name: str, tool: BaseTool):
        """Register a tool in the registry"""
        self._tools[name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, str]:
        """List all registered tools with their descriptions"""
        return {name: tool.description for name, tool in self._tools.items()}
    
    def execute_tool(self, name: str, **kwargs):
        """Execute a tool by name"""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        
        return tool.execute(**kwargs)
    
    def load_tools_for_agent(self, tool_names: List[str], agent_name: str = None):
        """Load specific tools for an agent, including dynamic agent proxy tools and memory tools"""
        for tool_name in tool_names:
            if tool_name not in self._tools:
                # Handle memory tools specially (they need agent_name)
                if tool_name in ['read_memory', 'append_memory'] and agent_name:
                    try:
                        from tools.memory_tools import ReadMemoryTool, AppendMemoryTool
                        if tool_name == 'read_memory':
                            tool_instance = ReadMemoryTool(agent_name)
                        else:  # append_memory
                            tool_instance = AppendMemoryTool(agent_name)
                        self.register_tool(tool_name, tool_instance)
                    except Exception as e:
                        print(f"Warning: Failed to load memory tool '{tool_name}': {e}")
                elif tool_name in self._available_tools:
                    # Load regular tool
                    try:
                        tool_class = self._available_tools[tool_name]
                        tool_instance = tool_class()
                        self.register_tool(tool_name, tool_instance)
                    except Exception as e:
                        print(f"Warning: Failed to load tool '{tool_name}': {e}")
                else:
                    # Check if this might be an agent name - create proxy tool
                    if self._is_agent_name(tool_name):
                        try:
                            from tools.agent_proxy_tool import AgentProxyTool
                            agent_proxy = AgentProxyTool(tool_name)
                            self.register_tool(tool_name, agent_proxy)
                            # Only print once when actually creating
                            # print(f"Created agent proxy tool for '{tool_name}'")
                        except Exception as e:
                            print(f"Warning: Failed to create agent proxy for '{tool_name}': {e}")
    
    def _is_agent_name(self, tool_name: str) -> bool:
        """Check if a tool name might be an agent name"""
        # Import here to avoid circular imports
        from config.config_manager import ConfigManager
        
        try:
            # Check if it exists in agent configuration
            config_manager = ConfigManager()
            agent_configs = config_manager.get_all_agent_configs()
            return tool_name in agent_configs
        except Exception:
            return False
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get all available tools (not just registered ones)"""
        available = {}
        for tool_name, tool_class in self._available_tools.items():
            try:
                tool_instance = tool_class()
                available[tool_name] = tool_instance.description
            except Exception:
                available[tool_name] = "Tool unavailable"
        return available