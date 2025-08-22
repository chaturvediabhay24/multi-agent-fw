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
        this.toolCallEventSource = null;
        this.activeToolCalls = new Map(); // Track active tool calls by ID

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
        this.killBtn = document.getElementById('killBtn');
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
        this.killBtn.addEventListener('click', () => this.handleKillConversation());
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
        
        // Setup real-time tool call monitoring if conversation ID is available
        if (this.currentConversationId) {
            this.setupToolCallStream();
        }
    }

    setupToolCallStream() {
        // Close existing connection
        if (this.toolCallEventSource) {
            console.log('🔥 DEBUG: Closing existing SSE connection');
            this.toolCallEventSource.close();
        }

        if (!this.currentConversationId) {
            console.log('🔥 DEBUG: No conversation ID, skipping SSE setup');
            return;
        }

        console.log('🔥 DEBUG: Setting up SSE connection for conversation:', this.currentConversationId);

        // Setup Server-Sent Events for real-time tool calls
        const streamUrl = `/api/tool-calls/stream/${this.currentConversationId}`;
        console.log('🔥 DEBUG: SSE URL:', streamUrl);
        
        this.toolCallEventSource = new EventSource(streamUrl);
        
        this.toolCallEventSource.onopen = (event) => {
            console.log('🔥 DEBUG: SSE connection opened:', event);
        };
        
        this.toolCallEventSource.onmessage = (event) => {
            console.log('🔥 DEBUG: Received SSE message:', event.data);
            try {
                const data = JSON.parse(event.data);
                this.handleToolCallEvent(data);
            } catch (error) {
                console.error('Error parsing tool call event:', error);
            }
        };

        this.toolCallEventSource.onerror = (error) => {
            console.error('🔥 DEBUG: Tool call stream error:', error);
        };
    }

    handleToolCallEvent(event) {
        console.log('DEBUG: Received tool call event:', event);
        
        if (event.type === 'keepalive') return;

        switch (event.type) {
            case 'tool_call_start':
                this.showToolCallStart(event);
                break;
            case 'tool_execution_start':
                this.updateToolCallStatus(event.tool_id, 'executing');
                break;
            case 'tool_execution_complete':
                this.updateToolCallStatus(event.tool_id, 'completed', event.result, event.execution_time_ms);
                break;
            case 'tool_execution_error':
                this.updateToolCallStatus(event.tool_id, 'error', event.error, event.execution_time_ms);
                break;
            case 'llm_usage':
                this.showLLMUsageDetails(event);
                break;
        }
    }

    showToolCallStart(event) {
        // Create a simplified tool call display
        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-call tool-call-realtime';
        toolDiv.id = `tool-call-${event.tool_id}`;
        
        toolDiv.innerHTML = `
            <div class="tool-call-header" onclick="chatUI.toggleToolDetails('tool-call-${event.tool_id}')">
                <span class="tool-call-icon">🔧</span>
                <span class="tool-call-name">${Utils.escapeHtml(event.tool_name)}</span>
                <span class="tool-call-status" id="status-${event.tool_id}">Requested</span>
                <span class="tool-call-toggle">▼</span>
            </div>
            <div class="tool-call-details" style="display: none;">
                <div class="tool-call-params">
                    <strong>Input:</strong>
                    <pre>${Utils.escapeHtml(JSON.stringify(event.params || {}, null, 2))}</pre>
                </div>
                <div class="tool-call-result" id="result-${event.tool_id}" style="display: none;"></div>
            </div>
        `;

        // Add to the messages container
        this.messagesContainer.appendChild(toolDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        
        // Track the active tool call
        this.activeToolCalls.set(event.tool_id, toolDiv);
    }

    updateToolCallStatus(toolId, status, result = null, executionTimeMs = null) {
        const statusElement = document.getElementById(`status-${toolId}`);
        const resultElement = document.getElementById(`result-${toolId}`);
        
        if (statusElement) {
            switch (status) {
                case 'executing':
                    statusElement.textContent = 'Executing...';
                    statusElement.className = 'tool-call-status executing';
                    break;
                case 'completed':
                    const timeText = this.formatExecutionTime(executionTimeMs);
                    statusElement.textContent = `Completed${timeText}`;
                    statusElement.className = 'tool-call-status completed';
                    if (result && resultElement) {
                        resultElement.innerHTML = `
                            <div class="tool-call-output">
                                <strong>Output:</strong>
                                <pre>${Utils.escapeHtml(result)}</pre>
                            </div>
                        `;
                        resultElement.style.display = 'block';
                    }
                    break;
                case 'error':
                    const errorTimeText = this.formatExecutionTime(executionTimeMs);
                    statusElement.textContent = `Error${errorTimeText}`;
                    statusElement.className = 'tool-call-status error';
                    if (result && resultElement) {
                        resultElement.innerHTML = `
                            <div class="tool-call-output error">
                                <strong>Error:</strong>
                                <pre>${Utils.escapeHtml(result)}</pre>
                            </div>
                        `;
                        resultElement.style.display = 'block';
                    }
                    break;
            }
        }
    }

    formatExecutionTime(executionTimeMs) {
        if (!executionTimeMs) return '';
        
        if (executionTimeMs < 1000) {
            return ` (${executionTimeMs}ms)`;
        } else if (executionTimeMs < 60000) {
            return ` (${(executionTimeMs / 1000).toFixed(1)}s)`;
        } else {
            const minutes = Math.floor(executionTimeMs / 60000);
            const seconds = ((executionTimeMs % 60000) / 1000).toFixed(1);
            return ` (${minutes}m ${seconds}s)`;
        }
    }

    showLLMUsageDetails(event) {
        // Create LLM usage details component
        const usageDiv = document.createElement('div');
        usageDiv.className = 'llm-usage-details';
        
        const usageId = `usage-${Date.now()}`;
        usageDiv.id = usageId;
        
        const responseTimeText = event.llm_response_time_ms ? this.formatExecutionTime(event.llm_response_time_ms) : '';
        
        usageDiv.innerHTML = `
            <div class="llm-usage-header" onclick="chatUI.toggleUsageDetails('${usageId}')">
                <span class="llm-usage-icon">📊</span>
                <span class="llm-usage-title">LLM Metrics${responseTimeText}</span>
                <span class="llm-usage-summary">${event.total_tokens || 'N/A'} tokens</span>
                <span class="llm-usage-toggle">▼</span>
            </div>
            <div class="llm-usage-content" style="display: none;">
                <div class="usage-grid">
                    <div class="usage-item">
                        <span class="usage-label">Model:</span>
                        <span class="usage-value">${Utils.escapeHtml(event.model || 'Unknown')}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Provider:</span>
                        <span class="usage-value">${Utils.escapeHtml(event.provider || 'Unknown')}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Input Tokens:</span>
                        <span class="usage-value">${(event.input_tokens || 0).toLocaleString()}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Output Tokens:</span>
                        <span class="usage-value">${(event.output_tokens || 0).toLocaleString()}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Total Tokens:</span>
                        <span class="usage-value">${(event.total_tokens || 0).toLocaleString()}</span>
                    </div>
                    ${event.estimated_cost ? `
                    <div class="usage-item cost-item">
                        <span class="usage-label">Total Cost:</span>
                        <span class="usage-value">$${event.estimated_cost.toFixed(6)}</span>
                    </div>
                    ` : ''}
                    ${event.input_cost ? `
                    <div class="usage-item">
                        <span class="usage-label">Input Cost:</span>
                        <span class="usage-value">$${event.input_cost.toFixed(6)}</span>
                    </div>
                    ` : ''}
                    ${event.output_cost ? `
                    <div class="usage-item">
                        <span class="usage-label">Output Cost:</span>
                        <span class="usage-value">$${event.output_cost.toFixed(6)}</span>
                    </div>
                    ` : ''}
                    ${event.pricing_model ? `
                    <div class="usage-item">
                        <span class="usage-label">Pricing Model:</span>
                        <span class="usage-value">${Utils.escapeHtml(event.pricing_model)}</span>
                    </div>
                    ` : ''}
                    ${event.input_rate ? `
                    <div class="usage-item">
                        <span class="usage-label">Input Rate:</span>
                        <span class="usage-value">$${event.input_rate}/1M tokens</span>
                    </div>
                    ` : ''}
                    ${event.output_rate ? `
                    <div class="usage-item">
                        <span class="usage-label">Output Rate:</span>
                        <span class="usage-value">$${event.output_rate}/1M tokens</span>
                    </div>
                    ` : ''}
                    ${event.llm_response_time_ms ? `
                    <div class="usage-item">
                        <span class="usage-label">Response Time:</span>
                        <span class="usage-value">${this.formatExecutionTime(event.llm_response_time_ms)}</span>
                    </div>
                    ` : ''}
                    ${event.stop_reason ? `
                    <div class="usage-item">
                        <span class="usage-label">Stop Reason:</span>
                        <span class="usage-value">${Utils.escapeHtml(event.stop_reason)}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        // Add to the messages container
        this.messagesContainer.appendChild(usageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    toggleUsageDetails(usageId) {
        const usageDiv = document.getElementById(usageId);
        if (!usageDiv) return;
        
        const content = usageDiv.querySelector('.llm-usage-content');
        const toggle = usageDiv.querySelector('.llm-usage-toggle');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            toggle.textContent = '▲';
        } else {
            content.style.display = 'none';
            toggle.textContent = '▼';
        }
    }

    toggleToolDetails(toolId) {
        const toolDiv = document.getElementById(toolId);
        if (!toolDiv) return;
        
        const details = toolDiv.querySelector('.tool-call-details');
        const toggle = toolDiv.querySelector('.tool-call-toggle');
        
        if (details.style.display === 'none') {
            details.style.display = 'block';
            toggle.textContent = '▲';
        } else {
            details.style.display = 'none';
            toggle.textContent = '▼';
        }
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

        // Generate conversation ID upfront if we don't have one yet
        if (!this.currentConversationId) {
            this.currentConversationId = 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            console.log('🔥 DEBUG: Generated new conversation ID:', this.currentConversationId);
            this.setupToolCallStream();
        }

        this.setLoading(true);

        try {
            const data = await ApiService.sendMessage(
                this.currentAgent, 
                message, 
                this.currentConversationId, 
                this.debugMode
            );

            // Debug logging
            console.log('DEBUG: API Response data:', data);

            // Update conversation ID if the backend returned a different one
            if (data.conversation_id && data.conversation_id !== this.currentConversationId) {
                console.log('🔥 DEBUG: Backend returned different conversation ID:', data.conversation_id);
                const oldConversationId = this.currentConversationId;
                this.currentConversationId = data.conversation_id;
                
                // Reconnect SSE stream with the new conversation ID
                this.setupToolCallStream();
            }

            // Show assistant response
            this.showMessage('assistant', data.response);
            
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

    showMessage(role, content) {
        console.log('DEBUG: showMessage called with:', { role, content });
        
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

        // Tool calls are now displayed in real-time via SSE events
        // No need to display them again here

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
        
        // Show/hide kill button based on loading state
        if (loading && this.currentConversationId) {
            this.killBtn.style.display = 'inline-block';
        } else {
            this.killBtn.style.display = 'none';
        }
        
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

    async handleKillConversation() {
        if (!this.currentConversationId || !this.isLoading) return;
        
        try {
            // Update kill button to show it's processing
            const originalText = this.killBtn.textContent;
            this.killBtn.textContent = '⏹️ Stopping...';
            this.killBtn.disabled = true;
            
            // Call the kill API
            const response = await fetch(`/api/kill-conversation/${this.currentConversationId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Conversation killed:', data);
                
                // Stop loading state and hide kill button
                this.setLoading(false);
                
                // Show system message about termination
                this.showMessage('system', '🛑 Conversation stopped by user');
                
                // Close SSE connection if it exists
                if (this.toolCallEventSource) {
                    this.toolCallEventSource.close();
                    this.toolCallEventSource = null;
                }
                
            } else {
                const error = await response.json();
                console.error('Error killing conversation:', error);
                this.showMessage('system', `❌ Failed to stop conversation: ${error.detail || 'Unknown error'}`);
            }
            
        } catch (error) {
            console.error('Error killing conversation:', error);
            this.showMessage('system', `❌ Error stopping conversation: ${error.message}`);
        } finally {
            // Reset kill button
            this.killBtn.textContent = '🛑 Stop';
            this.killBtn.disabled = false;
        }
    }
}

// Global instance for potential external access
window.chatUI = new ChatUI();