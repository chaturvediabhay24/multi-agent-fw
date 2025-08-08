// Chat UI functionality
import { ApiService } from './api.js';
import { Utils } from './utils.js';

export class ChatUI {
    constructor() {
        this.currentAgent = null;
        this.currentConversationId = null;
        this.isLoading = false;
        this.debugMode = false;
        this.agents = {};

        // DOM elements
        this.agentSelector = document.getElementById('agentSelector');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.chatTitle = document.getElementById('chatTitle');
        this.agentInfo = document.getElementById('agentInfo');
        this.debugBtn = document.getElementById('debugBtn');
        this.helpBtn = document.getElementById('helpBtn');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.conversationsList = document.getElementById('conversationsList');
        this.commandsHelp = document.getElementById('commandsHelp');
    }

    async init() {
        await this.loadAgents();
        this.setupEventListeners();
        this.adjustTextarea();
    }

    async loadAgents() {
        try {
            const data = await ApiService.getAgents();
            this.agents = data.agents || {};
            
            this.agentSelector.innerHTML = '<option value="">Select Agent</option>';
            Object.keys(this.agents).forEach(agentName => {
                const option = document.createElement('option');
                option.value = agentName;
                option.textContent = agentName;
                this.agentSelector.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading agents:', error);
            this.showMessage('system', 'Error loading agents. Please check the server connection.');
        }
    }

    setupEventListeners() {
        this.agentSelector.addEventListener('change', () => this.handleAgentChange());
        this.sendBtn.addEventListener('click', () => this.handleSendMessage());
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.messageInput.addEventListener('input', () => this.adjustTextarea());
        this.debugBtn.addEventListener('click', () => this.toggleDebugMode());
        this.helpBtn.addEventListener('click', () => this.toggleHelp());
        this.newChatBtn.addEventListener('click', () => this.startNewChat());
        document.getElementById('reloadBtn').addEventListener('click', () => this.reloadAgents());
    }

    handleAgentChange() {
        const selectedAgent = this.agentSelector.value;
        if (!selectedAgent) {
            this.currentAgent = null;
            this.messageInput.disabled = true;
            this.sendBtn.disabled = true;
            this.chatTitle.textContent = 'Select an agent to start';
            this.agentInfo.textContent = 'Select an agent to start chatting';
            this.showEmptyState();
            return;
        }

        this.currentAgent = selectedAgent;
        this.currentConversationId = null;
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
        
        const agent = this.agents[selectedAgent];
        this.chatTitle.textContent = `Chat with ${selectedAgent}`;
        this.agentInfo.innerHTML = `
            <div><strong>${Utils.escapeHtml(selectedAgent)}</strong></div>
            <div style="margin-top: 8px; opacity: 0.9;">${Utils.escapeHtml(agent.description)}</div>
            <div style="margin-top: 8px; font-size: 0.8rem;">
                <div>Model: ${Utils.escapeHtml(agent.model_type)} - ${Utils.escapeHtml(agent.model_name)}</div>
                <div>Tools: ${agent.tools && agent.tools.length ? agent.tools.map(t => Utils.escapeHtml(t)).join(', ') : 'None'}</div>
            </div>
        `;
        
        this.clearMessages();
        this.loadConversations();
        this.messageInput.focus();
    }

    handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.handleSendMessage();
        }
    }

    async handleSendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.currentAgent || this.isLoading) return;

        // Show user message
        this.showMessage('user', message);
        this.messageInput.value = '';
        this.adjustTextarea();

        // Handle special commands
        if (message.startsWith('/')) {
            this.handleCommand(message);
            return;
        }

        this.setLoading(true);

        try {
            const data = await ApiService.sendMessage(
                this.currentAgent, 
                message, 
                this.currentConversationId, 
                this.debugMode
            );

            // Update conversation ID
            if (data.conversation_id) {
                this.currentConversationId = data.conversation_id;
            }

            // Show assistant response
            this.showMessage('assistant', data.response, data.tool_calls);
            
            // Reload conversations list
            this.loadConversations();

        } catch (error) {
            console.error('Error sending message:', error);
            this.showMessage('system', `Error: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    handleCommand(command) {
        const parts = command.split(' ');
        const cmd = parts[0].toLowerCase();

        switch (cmd) {
            case '/help':
                this.showCommandHelp();
                break;
            case '/info':
                this.showAgentInfo();
                break;
            case '/debug':
                this.toggleDebugMode();
                break;
            case '/switch':
                if (parts.length === 3) {
                    this.switchModel(parts[1], parts[2]);
                } else {
                    this.showMessage('system', 'Usage: /switch <provider> <model>\\nExample: /switch openai gpt-4');
                }
                break;
            default:
                this.showMessage('system', `Unknown command: ${cmd}. Type /help for available commands.`);
        }
    }

    showCommandHelp() {
        const helpText = `Available commands:
/help - Show this help
/info - Show agent information  
/debug - Toggle debug mode
/switch <provider> <model> - Switch model
/tools - Show tool call history (not implemented)
/history - Show conversation history (not implemented)`;
        this.showMessage('system', helpText);
    }

    showAgentInfo() {
        if (!this.currentAgent) {
            this.showMessage('system', 'No agent selected');
            return;
        }
        
        const agent = this.agents[this.currentAgent];
        const info = `Agent: ${this.currentAgent}
Description: ${agent.description}
Model: ${agent.model_type} - ${agent.model_name}
Tools: ${agent.tools && agent.tools.length ? agent.tools.join(', ') : 'None'}
Debug Mode: ${this.debugMode ? 'ON' : 'OFF'}`;
        this.showMessage('system', info);
    }

    async switchModel(provider, model) {
        try {
            const data = await ApiService.switchModel(
                this.currentAgent, 
                provider, 
                model, 
                this.currentConversationId
            );

            this.showMessage('system', `✅ ${data.message}`);
            
            // Update agent info
            this.agents[this.currentAgent].model_type = provider;
            this.agents[this.currentAgent].model_name = model;
            this.handleAgentChange(); // Refresh display

        } catch (error) {
            this.showMessage('system', `❌ Error switching model: ${error.message}`);
        }
    }

    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        this.debugBtn.textContent = `Debug: ${this.debugMode ? 'ON' : 'OFF'}`;
        this.debugBtn.classList.toggle('active', this.debugMode);
        this.showMessage('system', `🔧 Debug mode ${this.debugMode ? 'ON' : 'OFF'}`);
    }

    toggleHelp() {
        this.commandsHelp.classList.toggle('show');
    }

    startNewChat() {
        if (!this.currentAgent) return;
        
        this.currentConversationId = null;
        this.clearMessages();
        this.showMessage('system', `Started new conversation with ${this.currentAgent}`);
        this.messageInput.focus();
    }

    showMessage(role, content, toolCalls = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (role === 'user') {
            avatar.textContent = '👤';
        } else if (role === 'assistant') {
            avatar.textContent = '🤖';
        } else {
            avatar.textContent = 'ℹ️';
            avatar.style.background = '#6c757d';
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Format content with line breaks
        const formattedContent = content.replace(/\\n/g, '\n');
        contentDiv.style.whiteSpace = 'pre-wrap';
        contentDiv.textContent = formattedContent;

        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = Utils.formatTime(new Date());

        messageDiv.appendChild(avatar);
        const messageBody = document.createElement('div');
        messageBody.appendChild(contentDiv);
        messageBody.appendChild(timeDiv);

        // Add tool calls if present
        if (toolCalls && toolCalls.length > 0) {
            toolCalls.forEach(toolCall => {
                const toolDiv = document.createElement('div');
                toolDiv.className = 'tool-call';
                toolDiv.innerHTML = `
                    <div class="tool-call-name">🔧 ${Utils.escapeHtml(toolCall.name || toolCall.tool_name)}</div>
                    <div class="tool-call-params">${Utils.escapeHtml(JSON.stringify(toolCall.params || toolCall.arguments || {}, null, 2))}</div>
                `;
                messageBody.appendChild(toolDiv);
            });
        }

        messageDiv.appendChild(messageBody);

        // Remove empty state if present
        const emptyState = this.messagesContainer.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    showEmptyState() {
        this.messagesContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💬</div>
                <h3>Welcome to Multi-Agent Chat</h3>
                <p>Select an agent from the dropdown above to start a conversation.</p>
                <p>Use commands like /help, /info, /debug for additional features.</p>
            </div>
        `;
    }

    clearMessages() {
        this.messagesContainer.innerHTML = '';
    }

    setLoading(loading) {
        this.isLoading = loading;
        this.sendBtn.disabled = loading || !this.currentAgent;
        
        if (loading) {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'loading';
            loadingDiv.innerHTML = `
                <span>🤖 ${this.currentAgent} is thinking</span>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            `;
            this.messagesContainer.appendChild(loadingDiv);
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        } else {
            const loadingDiv = this.messagesContainer.querySelector('.loading');
            if (loadingDiv) {
                loadingDiv.remove();
            }
        }
    }

    adjustTextarea() {
        Utils.adjustTextarea(this.messageInput);
    }

    async loadConversations() {
        if (!this.currentAgent) return;
        
        try {
            const data = await ApiService.getConversations(this.currentAgent);
            
            this.conversationsList.innerHTML = '';
            
            if (data.conversations && data.conversations.length > 0) {
                data.conversations.forEach(conv => {
                    const convDiv = document.createElement('div');
                    convDiv.className = 'conversation-item';
                    if (conv.conversation_id === this.currentConversationId) {
                        convDiv.classList.add('active');
                    }
                    
                    convDiv.innerHTML = `
                        <div class="conversation-time">${Utils.formatDateTime(conv.timestamp)}</div>
                        <div class="conversation-preview">${conv.message_count} messages</div>
                    `;
                    
                    convDiv.addEventListener('click', () => this.loadConversation(conv.conversation_id, convDiv));
                    this.conversationsList.appendChild(convDiv);
                });
            } else {
                this.conversationsList.innerHTML = '<div style="color: rgba(255,255,255,0.7); text-align: center; padding: 20px;">No conversations yet</div>';
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    }

    loadConversation(conversationId, element) {
        // This would load a specific conversation
        // For now, we'll just set it as current
        this.currentConversationId = conversationId;
        this.clearMessages();
        this.showMessage('system', `Loaded conversation ${conversationId}`);
        
        // Update active state
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        element.classList.add('active');
    }

    async reloadAgents() {
        const reloadBtn = document.getElementById('reloadBtn');
        Utils.setButtonLoading(reloadBtn, true, '🔄 Reloading...');
        
        try {
            // Call the reload endpoint
            const result = await ApiService.reloadAgents();
            
            // Refresh the agent list
            await this.loadAgents();
            
            // Show success message
            this.showMessage('system', `✅ ${result.message}: ${result.agents.join(', ')}`);
            
            // If current agent is no longer available, reset selection
            if (this.currentAgent && !this.agents[this.currentAgent]) {
                this.agentSelector.value = '';
                this.handleAgentChange();
            }
            
        } catch (error) {
            console.error('Error reloading agents:', error);
            this.showMessage('system', `❌ Error reloading agents: ${error.message}`);
        } finally {
            Utils.setButtonLoading(reloadBtn, false);
        }
    }
}

// Global instance for potential external access
window.chatUI = new ChatUI();