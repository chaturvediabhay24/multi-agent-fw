import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional

from tools.base_tool import BaseTool


class PostgresTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="postgres_query",
            description="Execute PostgreSQL queries and return results"
        )
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'postgres'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
    
    def execute(self, query: str, params: Optional[List] = None) -> Dict[str, Any]:
        """Execute a PostgreSQL query"""
        try:
            with psycopg2.connect(**self.connection_params) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params or [])
                    
                    if query.strip().upper().startswith('SELECT'):
                        results = cursor.fetchall()
                        return {
                            'success': True,
                            'data': [dict(row) for row in results],
                            'row_count': len(results)
                        }
                    else:
                        conn.commit()
                        return {
                            'success': True,
                            'affected_rows': cursor.rowcount,
                            'message': 'Query executed successfully'
                        }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the schema for PostgreSQL tool parameters"""
        return {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'SQL query to execute'
                },
                'params': {
                    'type': 'array',
                    'description': 'Optional parameters for parameterized queries',
                    'items': {'type': 'string'}
                }
            },
            'required': ['query']
        }
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
        result = self.execute(query)
        if result['success']:
            return [row['table_name'] for row in result['data']]
        return []
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        result = self.execute(query, [table_name])
        if result['success']:
            return result['data']
        return []