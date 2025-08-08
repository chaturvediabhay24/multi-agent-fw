# 🏗️ Multi-Agent Framework - Project Structure

A professional, modular FastAPI-based multi-agent system with clean architecture.

## 📁 **Project Structure**

```
multi-agent/
├── 🖥️ server.py                    # Main FastAPI application entry point
├── 🚀 start_ui.py                  # Easy startup script
├── 📋 requirements.txt              # All project dependencies
├── 🤖 main.py                      # CLI interface
│
├── 📱 ui/                          # Web UI Module
│   ├── __init__.py
│   ├── router.py                   # UI routes (/, /chat, /health)
│   ├── assets/
│   │   ├── css/
│   │   │   ├── base.css           # Common styles & utilities
│   │   │   ├── config.css         # Agent configuration styles
│   │   │   └── chat.css           # Chat interface styles
│   │   └── js/
│   │       ├── api.js             # API service layer
│   │       ├── utils.js           # Utility functions
│   │       ├── config.js          # Configuration page logic
│   │       └── chat.js            # Chat interface logic
│   └── pages/
│       ├── config.html            # Agent configuration page
│       └── chat.html              # Chat interface page
│
├── 🔌 api/                         # API Module
│   ├── __init__.py
│   └── router.py                   # API routes (/api/*)
│
├── 🤖 agents/                      # Agent System
│   ├── __init__.py
│   ├── agent_registry.py
│   ├── base_agent.py
│   ├── custom_agent.py
│   └── model_providers/
│
├── ⚙️ config/                       # Configuration
│   ├── __init__.py
│   ├── agents.json                # Agent configurations
│   ├── model_providers.json       # Model provider settings
│   └── config_manager.py
│
├── 💬 conversations/               # Chat History
│   ├── __init__.py
│   ├── conversation_manager.py
│   └── sessions/
│
└── 🔧 tools/                       # Agent Tools
    ├── __init__.py
    ├── base_tool.py
    ├── calculator_tool.py
    ├── postgres_tool.py
    └── tool_registry.py
```

## 🎯 **Architecture Principles**

### **📦 Modular Design**
- **UI Module** (`ui/`): Complete web interface with assets
- **API Module** (`api/`): RESTful API endpoints
- **Server** (`server.py`): Clean FastAPI application bootstrap

### **🏗️ FastAPI Best Practices**
- **Router-based organization**: Logical route grouping
- **Dependency injection**: Clean separation of concerns  
- **Pydantic models**: Type-safe request/response handling
- **Static file serving**: Professional asset management

### **💻 Frontend Architecture**
- **ES6 Modules**: Modern JavaScript organization
- **CSS Modules**: Maintainable styling system
- **Component-based**: Reusable UI elements
- **API Service Layer**: Centralized backend communication

## 🚀 **Entry Points**

### **Web Interface**
```bash
# Easy startup
python start_ui.py

# Manual startup  
python server.py
# or
uvicorn server:app --reload
```

**URLs:**
- 🏠 **Configuration**: `http://localhost:8000/`
- 💬 **Chat**: `http://localhost:8000/chat`
- 📚 **API Docs**: `http://localhost:8000/docs`
- 🏥 **Health Check**: `http://localhost:8000/health`

### **CLI Interface**
```bash
# Interactive mode
python main.py --agent data_analyst --interactive

# Single message
python main.py --agent data_analyst --message "Calculate 2+2"
```

## 🔌 **API Endpoints**

### **UI Routes** (`ui.router`)
| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Agent configuration page |
| `/chat` | GET | Chat interface page |
| `/health` | GET | UI health check |

### **API Routes** (`api.router`)
| Route | Method | Description |
|-------|--------|-------------|
| `/api/agents` | GET, POST | List/create agents |
| `/api/agents/{name}` | PUT, DELETE | Update/delete agents |
| `/api/providers` | GET | Available model providers |
| `/api/tools` | GET | Available tools |
| `/api/chat` | POST | Send chat messages |
| `/api/switch-model` | POST | Switch agent models |
| `/api/reload-agents` | POST | Reload agent configurations |
| `/api/conversations/{agent}` | GET | Get conversation history |

## 🎨 **Key Benefits**

### **🛠️ Developer Experience**
- **Clean separation**: UI, API, and business logic separated
- **Easy navigation**: Logical file organization
- **Hot reload**: Development-friendly setup
- **Type safety**: Full Pydantic integration

### **📈 Scalability**  
- **Modular routers**: Easy to add new features
- **Static assets**: CDN-ready structure
- **Database-ready**: Prepared for scaling
- **Microservice-friendly**: Clear boundaries

### **🔒 Maintainability**
- **Single responsibility**: Each module has clear purpose
- **Dependency isolation**: Minimal coupling
- **Test-friendly**: Easy to unit test
- **Version control**: Clean diffs and conflicts

## 🚀 **Quick Start**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server:**
   ```bash
   python start_ui.py
   ```

3. **Open browser:**
   - Configuration: http://localhost:8000
   - Chat: http://localhost:8000/chat

## 🔮 **Future Extensions**

The modular structure makes it easy to add:
- **Authentication module** (`auth/`)
- **Database integration** (`db/`)  
- **WebSocket support** (`websocket/`)
- **Testing suite** (`tests/`)
- **Deployment configs** (`deploy/`)

---

*This structure follows FastAPI and modern web development best practices for scalable, maintainable applications.*