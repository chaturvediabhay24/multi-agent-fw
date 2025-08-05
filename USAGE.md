# Multi-Agent Framework

A simple, modular multi-agent framework supporting OpenAI and Claude models with conversation persistence and agent-to-agent communication.

## Features

- **Multiple Model Support**: Switch between OpenAI and Claude models easily
- **Agent-to-Agent Communication**: Agents can call other agents as tools
- **Conversation Persistence**: All conversations are stored and can be resumed
- **Modular Architecture**: Separate modules for agents, tools, and database operations
- **PostgreSQL Integration**: Built-in PostgreSQL tool for database operations
- **Configurable Agents**: JSON-based agent configuration

## Quick Setup

1. **Create virtual environment and install dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

3. **Run an agent:**
```bash
# Basic usage
python main.py --agent data_analyst --message "Show me all tables in the database"

# List available agents
python main.py --list-agents

# Continue existing conversation
python main.py --agent research_assistant --message "Continue our discussion" --conversation-id abc-123

# Override model
python main.py --agent task_coordinator --message "Plan a project" --model-type claude --model-name claude-3-sonnet-20240229
```

## Agent Configuration

Edit `config/agents.json` to configure agents:

```json
{
  "agent_name": {
    "class": "CustomAgent",
    "description": "What this agent does",
    "model_type": "openai",
    "model_name": "gpt-4",
    "system_prompt": "Agent behavior instructions",
    "tools": ["postgres_query"]
  }
}
```

## Agent-to-Agent Communication

Agents can call other agents using the `call_agent()` method:

```python
# In agent code
response = self.call_agent("data_analyst", "Analyze sales data for Q4")
```

## Calculator Tool

The Calculator tool performs mathematical operations with separate parameters:

**Parameters:**
- `param1`: First number/parameter
- `param2`: Second number (optional for single-param operations)
- `operator`: Mathematical operation

**Supported Operators:**
- `add`, `subtract`, `multiply`, `divide`, `power`
- `sqrt`, `sin`, `cos`, `tan`, `log`, `log10`

**Examples:**
```python
from tools.tool_registry import ToolRegistry

registry = ToolRegistry()

# Basic arithmetic
result = registry.execute_tool("calculator", param1=25, param2=4, operator="multiply")
# Returns: {'success': True, 'result': 100, 'operation': '25 × 4', 'formatted_result': '100'}

# Single parameter functions
result = registry.execute_tool("calculator", param1=144, operator="sqrt")  
# Returns: {'success': True, 'result': 12.0, 'operation': '√144', 'formatted_result': '12'}
```

## Database Operations

The PostgreSQL tool provides database access:

```python
from tools.tool_registry import ToolRegistry

registry = ToolRegistry()
result = registry.execute_tool("postgres_query", 
                              query="SELECT * FROM users LIMIT 10")
```

## Directory Structure

```
multi-agent/
├── agents/          # Agent implementations
├── tools/           # All tool implementations (including database tools)
├── conversations/   # Conversation storage
├── config/          # Agent configurations
├── main.py          # CLI interface
└── requirements.txt # Dependencies
```

## Usage Examples

### Interactive Mode (NEW! 🎉)
```bash
# Start interactive chat with an agent
python main.py -a research_assistant -i

# Start interactive mode without specifying -i (auto-detected)
python main.py -a data_analyst

# Continue existing conversation interactively
python main.py -a research_assistant -c conversation-uuid -i
```

**Interactive Mode Commands:**
- `/help` - Show available commands
- `/info` - Show agent information
- `/debug` - Toggle debug mode to see tool calls
- `/tools` - View tool call history
- `/switch openai gpt-4` - Switch models mid-conversation
- `/history` - View conversation history
- `quit/exit/bye` - End session

**Calculator Usage Examples:**
```bash
🧑 You: Calculate 23582345 * 3245
🤖 data_analyst: I'll calculate that for you.
**23582345.0 × 3245.0 = 76524709525**

🧑 You: What's the square root of 144?
🤖 data_analyst: I'll calculate that for you.
**√144.0 = 12**

🧑 You: /tools
Tool Call History (2 calls):
  1. ✅ calculator({'param1': 23582345.0, 'param2': 3245.0, 'operator': 'multiply'})
  2. ✅ calculator({'param1': 144.0, 'operator': 'sqrt'})
```

### Single Message Mode
```bash
# Send one message and exit
python main.py -a research_assistant -m "Research latest AI trends"

# Database query
python main.py -a data_analyst -m "Show me user registration trends"
```

### Model Switching
```bash
# Switch to Claude for creative tasks
python main.py -a research_assistant -m "Write a creative story" --model-type claude

# Use specific GPT model
python main.py -a data_analyst --model-name gpt-4-turbo -i
```

### Conversation Management
```bash
# List all conversations
python main.py --list-conversations

# Continue specific conversation
python main.py -a research_assistant -c conversation-uuid -i
```

## Environment Variables

Required in `.env` file:

```bash
# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Database (optional)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

## Adding Custom Agents

1. Create agent class in `agents/` directory
2. Inherit from `BaseAgent` or `CustomAgent`
3. Add configuration to `config/agents.json`
4. Implement `get_description()` method

## Adding Custom Tools

1. Create tool class in `tools/` directory
2. Inherit from `BaseTool`
3. Implement `execute()` and `get_schema()` methods
4. Register in `ToolRegistry`

That's it! The framework handles conversation persistence, model switching, and agent communication automatically.