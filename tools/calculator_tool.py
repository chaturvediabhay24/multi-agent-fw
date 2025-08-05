import math
import re
from typing import Any, Dict

from tools.base_tool import BaseTool


class CalculatorTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations with two parameters and an operator (add, subtract, multiply, divide, power, sqrt, sin, cos, tan)"
        )
    
    def execute(self, param1: float, param2: float = None, operator: str = "add") -> Dict[str, Any]:
        """Execute a mathematical operation with parameters"""
        try:
            # Convert string numbers to float if needed
            if isinstance(param1, str):
                param1 = float(param1)
            if param2 is not None and isinstance(param2, str):
                param2 = float(param2)
            
            # Perform calculation based on operator
            if operator.lower() in ['add', '+', 'plus']:
                if param2 is None:
                    return {'success': False, 'error': 'Addition requires two parameters'}
                result = param1 + param2
                operation = f"{param1} + {param2}"
                
            elif operator.lower() in ['subtract', '-', 'minus']:
                if param2 is None:
                    return {'success': False, 'error': 'Subtraction requires two parameters'}
                result = param1 - param2
                operation = f"{param1} - {param2}"
                
            elif operator.lower() in ['multiply', '*', 'times']:
                if param2 is None:
                    return {'success': False, 'error': 'Multiplication requires two parameters'}
                result = param1 * param2
                operation = f"{param1} × {param2}"
                
            elif operator.lower() in ['divide', '/', 'div']:
                if param2 is None:
                    return {'success': False, 'error': 'Division requires two parameters'}
                if param2 == 0:
                    return {'success': False, 'error': 'Division by zero'}
                result = param1 / param2
                operation = f"{param1} ÷ {param2}"
                
            elif operator.lower() in ['power', '^', '**', 'pow']:
                if param2 is None:
                    return {'success': False, 'error': 'Power operation requires two parameters'}
                result = param1 ** param2
                operation = f"{param1} ^ {param2}"
                
            elif operator.lower() in ['sqrt', 'square_root']:
                result = math.sqrt(param1)
                operation = f"√{param1}"
                
            elif operator.lower() in ['sin', 'sine']:
                result = math.sin(param1)
                operation = f"sin({param1})"
                
            elif operator.lower() in ['cos', 'cosine']:
                result = math.cos(param1)
                operation = f"cos({param1})"
                
            elif operator.lower() in ['tan', 'tangent']:
                result = math.tan(param1)
                operation = f"tan({param1})"
                
            elif operator.lower() in ['log', 'logarithm']:
                if param1 <= 0:
                    return {'success': False, 'error': 'Logarithm requires positive number'}
                result = math.log(param1)
                operation = f"ln({param1})"
                
            elif operator.lower() in ['log10']:
                if param1 <= 0:
                    return {'success': False, 'error': 'Logarithm requires positive number'}
                result = math.log10(param1)
                operation = f"log₁₀({param1})"
                
            else:
                return {
                    'success': False,
                    'error': f'Unknown operator: {operator}. Supported: add, subtract, multiply, divide, power, sqrt, sin, cos, tan, log, log10'
                }
            
            return {
                'success': True,
                'result': result,
                'operation': operation,
                'formatted_result': self._format_result(result)
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid number format: {str(e)}'
            }
        except OverflowError:
            return {
                'success': False,
                'error': 'Result too large to compute'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Calculation error: {str(e)}'
            }
    
    def _format_result(self, result) -> str:
        """Format the result for display"""
        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            else:
                # Round to 10 decimal places to avoid floating point precision issues
                return f"{result:.10f}".rstrip('0').rstrip('.')
        else:
            return str(result)
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the schema for calculator tool parameters"""
        return {
            'type': 'object',
            'properties': {
                'param1': {
                    'type': 'number',
                    'description': 'First number/parameter for the calculation'
                },
                'param2': {
                    'type': 'number',  
                    'description': 'Second number/parameter (optional for single-param operations like sqrt, sin, cos)'
                },
                'operator': {
                    'type': 'string',
                    'description': 'Mathematical operator: add, subtract, multiply, divide, power, sqrt, sin, cos, tan, log, log10',
                    'enum': ['add', 'subtract', 'multiply', 'divide', 'power', 'sqrt', 'sin', 'cos', 'tan', 'log', 'log10']
                }
            },
            'required': ['param1', 'operator']
        }