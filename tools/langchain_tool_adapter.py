from typing import Any, Dict, List, Optional, Type, Union
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from tools.base_tool import BaseTool


class LangChainToolAdapter:
    """Adapter to convert custom BaseTool instances to LangChain tools"""
    
    @staticmethod
    def convert_tool(base_tool: BaseTool) -> StructuredTool:
        """Convert a BaseTool instance to a LangChain StructuredTool"""
        schema = base_tool.get_schema()
        
        # Create Pydantic model from schema
        pydantic_model = LangChainToolAdapter._create_pydantic_model_from_schema(
            schema, base_tool.name
        )
        
        # Create the structured tool
        def tool_func(**kwargs):
            return base_tool.execute(**kwargs)
        
        return StructuredTool(
            name=base_tool.name,
            description=base_tool.description,
            args_schema=pydantic_model,
            func=tool_func
        )
    
    @staticmethod
    def convert_tools(base_tools: List[BaseTool]) -> List[StructuredTool]:
        """Convert multiple BaseTool instances to LangChain tools"""
        return [LangChainToolAdapter.convert_tool(tool) for tool in base_tools]
    
    @staticmethod
    def _create_pydantic_model_from_schema(schema: Dict[str, Any], model_name: str) -> Type[BaseModel]:
        """Create a Pydantic model from a JSON schema"""
        # Handle both direct schema format and function wrapper format
        if 'function' in schema and 'parameters' in schema['function']:
            # Function wrapper format (like OpenAI function calling)
            params = schema['function']['parameters']
            properties = params.get('properties', {})
            required = params.get('required', [])
        else:
            # Direct schema format
            properties = schema.get('properties', {})
            required = schema.get('required', [])
        
        fields = {}
        
        for prop_name, prop_schema in properties.items():
            prop_type = LangChainToolAdapter._get_python_type_from_schema(prop_schema)
            
            # Determine if field is required
            is_required = prop_name in required
            default_value = ... if is_required else None
            
            # Create Field with description
            field = Field(
                default=default_value,
                description=prop_schema.get('description', '')
            )
            
            fields[prop_name] = (prop_type, field)
        
        # Create the Pydantic model dynamically
        return create_model(f"{model_name}Args", **fields)
    
    @staticmethod
    def _get_python_type_from_schema(prop_schema: Dict[str, Any]) -> Type:
        """Convert JSON schema type to Python type"""
        schema_type = prop_schema.get('type', 'string')
        
        type_map = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        
        python_type = type_map.get(schema_type, str)
        
        # Handle optional fields (not in required list)
        return Optional[python_type]