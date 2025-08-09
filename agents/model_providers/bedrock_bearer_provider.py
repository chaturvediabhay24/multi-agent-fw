import os
import json
import aiohttp
from typing import List, Union, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from .base_provider import BaseModelProvider


class BedrockBearerProvider(BaseModelProvider):
    """AWS Bedrock Claude provider using bearer token authentication"""
    
    def __init__(self, model_name: str = "anthropic.claude-3-sonnet-20240229-v1:0", **kwargs):
        super().__init__(model_name, **kwargs)
        self.region = os.getenv('AWS_BEDROCK_REGION', 'eu-west-2')
        self.endpoint = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{model_name}/invoke"
        self.bearer_token = os.getenv('AWS_BEARER_TOKEN_BEDROCK')
        
    def _format_messages_for_bedrock(self, messages: List[BaseMessage]) -> dict:
        """Format messages for Bedrock Claude API"""
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_message = msg.content
            elif isinstance(msg, HumanMessage):
                user_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                user_messages.append({"role": "assistant", "content": msg.content})
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.get('max_tokens', 4096),
            "temperature": self.config.get('temperature', 0.7),
            "messages": user_messages
        }
        
        if system_message:
            payload["system"] = system_message
            
        return payload
    
    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Async invoke Bedrock Claude model without tools"""
        if not self.is_available():
            raise RuntimeError("Bedrock bearer token not available. Set AWS_BEARER_TOKEN_BEDROCK in your .env file.")
        
        payload = self._format_messages_for_bedrock(messages)
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'Accept': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint, 
                                       json=payload, 
                                       headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    if response.status == 403:
                        error_text = await response.text()
                        if "not authorized to perform: bedrock:InvokeModel" in error_text:
                            raise RuntimeError(
                                f"AWS Bedrock permissions error: The AWS account associated with your bearer token "
                                f"does not have permission to invoke Claude models. Please contact your AWS "
                                f"administrator to grant 'bedrock:InvokeModel' permissions for Anthropic Claude models. "
                                f"Full error: {error_text[:200]}..."
                            )
                        else:
                            raise RuntimeError(f"Bedrock access denied (403): {error_text[:200]}...")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Bedrock API error {response.status}: {error_text[:200]}...")
                    
                    result = await response.json()
                    
                    # Extract content from Bedrock response
                    if 'content' in result and len(result['content']) > 0:
                        return result['content'][0]['text']
                    else:
                        raise RuntimeError(f"Unexpected response format: {result}")
                        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse response JSON: {e}")
    
    async def ainvoke_with_tools(self, messages: List[BaseMessage], tools: List[BaseTool]) -> Union[str, dict]:
        """Async invoke Bedrock Claude model with tools"""
        if not tools:
            return await self.ainvoke(messages)
        
        # For now, just invoke without tools since tool support requires more complex formatting
        # TODO: Implement tool support for Bedrock format
        return await self.ainvoke(messages)
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "bedrock_bearer"
    
    def is_available(self) -> bool:
        """Check if AWS Bedrock bearer token is available"""
        return bool(os.getenv('AWS_BEARER_TOKEN_BEDROCK'))
    
    async def list_available_models(self, region: str = None) -> Dict[str, Any]:
        """List all available foundation models in the specified AWS region"""
        if not self.is_available():
            raise RuntimeError("Bedrock bearer token not available.")
        
        # Use provided region or fall back to instance region
        region = region or self.region
        list_endpoint = f"https://bedrock.{region}.amazonaws.com/foundation-models"
        
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(list_endpoint,
                                     headers=headers,
                                     timeout=aiohttp.ClientTimeout(total=30)) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Failed to list models (status {response.status}): {error_text}")
                    
                    result = await response.json()
                    
                    # Extract and organize model information
                    models_info = {
                        'region': region,
                        'total_models': 0,
                        'anthropic_models': [],
                        'other_models': []
                    }
                    
                    if 'modelSummaries' in result:
                        models = result['modelSummaries']
                        models_info['total_models'] = len(models)
                        
                        for model in models:
                            model_info = {
                                'id': model.get('modelId', 'Unknown'),
                                'name': model.get('modelName', 'Unknown'),
                                'provider': model.get('providerName', 'Unknown'),
                                'status': model.get('modelLifecycle', {}).get('status', 'Unknown'),
                                'input_modalities': model.get('inputModalities', []),
                                'output_modalities': model.get('outputModalities', [])
                            }
                            
                            if 'anthropic' in model_info['id'].lower():
                                models_info['anthropic_models'].append(model_info)
                            else:
                                models_info['other_models'].append(model_info)
                    
                    return models_info
                    
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse response JSON: {e}")
    
    async def test_model_access(self, model_ids: List[str], region: str = None) -> Dict[str, str]:
        """Test access to specific model IDs"""
        if not self.is_available():
            raise RuntimeError("Bedrock bearer token not available.")
        
        # Use provided region or fall back to instance region
        region = region or self.region
        results = {}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'Accept': 'application/json'
        }
        
        test_payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "test"}]
        }
        
        for model_id in model_ids:
            endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(endpoint,
                                           json=test_payload,
                                           headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=15)) as response:
                        
                        if response.status == 200:
                            results[model_id] = "ACCESSIBLE ✅"
                        elif response.status == 403:
                            results[model_id] = "NO ACCESS (403) ❌"
                        else:
                            error_text = await response.text()
                            results[model_id] = f"ERROR ({response.status}): {error_text[:100]}"
                            
            except Exception as e:
                results[model_id] = f"EXCEPTION: {str(e)[:100]}"
        
        return results