# Multi-Agent Framework UI

This folder contains the modularized UI components for the Multi-Agent Framework.

## 📁 Structure

```
ui/
├── assets/
│   ├── css/
│   │   ├── base.css      # Base styles and utilities
│   │   ├── config.css    # Agent configuration page styles
│   │   └── chat.css      # Chat interface styles
│   └── js/
│       ├── api.js        # API service for backend communication
│       ├── utils.js      # Utility functions and helpers
│       ├── config.js     # Agent configuration functionality
│       └── chat.js       # Chat interface functionality
├── pages/
│   ├── config.html       # Agent configuration page
│   └── chat.html         # Chat interface page
└── components/           # Future: Reusable UI components
```

## 🎯 Design Principles

### **Modular Architecture**
- **Separation of Concerns**: CSS, JavaScript, and HTML are separated
- **Reusable Components**: Common styles and utilities are centralized
- **Clean Dependencies**: Clear import/export structure

### **Professional Standards**
- **ES6 Modules**: Modern JavaScript module system
- **Class-based Architecture**: Organized JavaScript classes
- **Responsive Design**: Mobile-first CSS approach
- **Accessible UI**: Semantic HTML and ARIA standards

## 🔧 Components

### **CSS Modules**

#### `base.css`
- Global styles and resets
- Common button styles (`.btn`, `.btn-primary`, etc.)
- Status message styles
- Loading animations
- Responsive utilities

#### `config.css`
- Agent configuration form styles
- Agent card components
- Tool management interface
- Edit mode indicators

#### `chat.css`
- Chat interface layout
- Message bubbles and avatars
- Sidebar and conversation list
- Input controls and buttons

### **JavaScript Modules**

#### `api.js`
- **ApiService class**: Centralized API communication
- RESTful endpoint methods (GET, POST, PUT, DELETE)
- Error handling and response parsing
- Agent, provider, and chat-specific methods

#### `utils.js`
- **Utils class**: Common utility functions
- Status message management
- Form validation helpers
- Local storage wrapper
- Text formatting and DOM helpers

#### `config.js`
- **AgentConfig class**: Agent configuration page logic
- Form handling and validation
- Agent CRUD operations
- Provider and tool management
- Edit mode functionality

#### `chat.js`
- **ChatUI class**: Chat interface functionality
- Message handling and display
- Agent selection and switching
- Command processing (/help, /debug, etc.)
- Conversation management

## 🚀 Usage

### **Development**
The UI is served by the FastAPI backend with static file mounting:

```python
# Server serves static files from /ui route
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

# Pages are served at root paths
@app.get("/")          # → ui/pages/config.html
@app.get("/chat")      # → ui/pages/chat.html
```

### **Module Imports**
JavaScript modules use ES6 import/export syntax:

```javascript
// In config.html
import { AgentConfig } from '/ui/assets/js/config.js';

// In chat.html
import { ChatUI } from '/ui/assets/js/chat.js';
```

### **CSS Architecture**
Layered CSS approach with base → specific styles:

```html
<!-- Common pattern -->
<link rel="stylesheet" href="/ui/assets/css/base.css">
<link rel="stylesheet" href="/ui/assets/css/[page].css">
```

## 🔄 Migration from Monolithic Files

The original single-file approach has been refactored into:

- `agent_config_ui.html` → `ui/pages/config.html` + CSS/JS modules
- `chat_ui.html` → `ui/pages/chat.html` + CSS/JS modules
- Inline styles → `ui/assets/css/*.css`
- Inline scripts → `ui/assets/js/*.js`

## 🎨 Benefits

### **Maintainability**
- **Single Responsibility**: Each file has a clear purpose
- **Easy Updates**: Modify styles or logic in one place
- **Code Reuse**: Common utilities shared across pages

### **Performance**
- **Caching**: Static assets can be cached separately
- **Minification**: CSS/JS can be minified independently
- **Load Optimization**: Only necessary assets per page

### **Developer Experience**
- **IDE Support**: Better syntax highlighting and intellisense
- **Debugging**: Clear stack traces and source maps
- **Version Control**: Meaningful diffs and conflict resolution

## 🔮 Future Enhancements

1. **Component System**: Reusable UI components (buttons, modals, forms)
2. **Build Process**: CSS preprocessing, JS bundling, minification
3. **Testing**: Unit tests for JavaScript modules
4. **Theming**: CSS custom properties for dynamic theming
5. **Internationalization**: Multi-language support structure