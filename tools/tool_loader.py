import importlib
import os
from typing import Dict, List, Type
from tools.base_tool import BaseTool


class ToolLoader:
    """Modular tool loader that discovers and loads tools dynamically"""
    
    @staticmethod
    def discover_tools(tools_dir: str = "tools") -> Dict[str, Type[BaseTool]]:
        """Discover all tool classes in the tools directory"""
        discovered_tools = {}
        
        # Get all Python files in tools directory
        if not os.path.exists(tools_dir):
            return discovered_tools
        
        for filename in os.listdir(tools_dir):
            if filename.endswith('_tool.py') and filename != 'base_tool.py':
                module_name = filename[:-3]  # Remove .py extension
                
                try:
                    # Import the module
                    module = importlib.import_module(f"{tools_dir}.{module_name}")
                    
                    # Find tool classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        
                        # Check if it's a tool class (inherits from BaseTool)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseTool) and 
                            attr != BaseTool):
                            
                            # Create instance to get tool name
                            try:
                                tool_instance = attr()
                                discovered_tools[tool_instance.name] = attr
                            except Exception:
                                # Skip tools that can't be instantiated
                                continue
                                
                except ImportError:
                    # Skip modules that can't be imported
                    continue
        
        return discovered_tools
    
    
    @staticmethod
    def load_tools_from_config(tool_names: List[str], 
                              available_tools: Dict[str, Type[BaseTool]]) -> Dict[str, BaseTool]:
        """Load specific tools by name"""
        loaded_tools = {}
        
        for tool_name in tool_names:
            if tool_name in available_tools:
                try:
                    tool_class = available_tools[tool_name]
                    tool_instance = tool_class()
                    loaded_tools[tool_name] = tool_instance
                except Exception as e:
                    print(f"Warning: Failed to load tool '{tool_name}': {e}")
        
        return loaded_tools