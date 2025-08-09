// API service for interacting with the backend
export class ApiService {
    static getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Try localStorage first, then global variable as backup
        let sessionId = localStorage.getItem('session-id');
        if (!sessionId && window.currentSessionId) {
            sessionId = window.currentSessionId;
            console.log('DEBUG JS: Using global session ID as backup:', sessionId);
        }
        
        console.log('DEBUG JS: Getting session ID from localStorage:', localStorage.getItem('session-id'));
        console.log('DEBUG JS: Global session ID available:', window.currentSessionId);
        console.log('DEBUG JS: Final session ID to use:', sessionId);
        
        if (sessionId) {
            headers['x-session-id'] = sessionId;
            console.log('DEBUG JS: Added x-session-id header:', sessionId);
        } else {
            console.log('DEBUG JS: No session ID found anywhere!');
        }
        console.log('DEBUG JS: Final headers object:', headers);
        
        return headers;
    }
    
    static async get(endpoint) {
        const response = await fetch(endpoint, {
            headers: this.getHeaders()
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    }

    static async post(endpoint, data) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    }

    static async put(endpoint, data) {
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    }

    static async delete(endpoint) {
        const response = await fetch(endpoint, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    }

    // Agent-specific API calls
    static async getAgents() {
        return this.get('/api/agents');
    }

    static async createAgent(agentName, config) {
        return this.post('/api/agents', {
            agent_name: agentName,
            config: config
        });
    }

    static async updateAgent(agentName, config) {
        return this.put(`/api/agents/${agentName}`, config);
    }

    static async deleteAgent(agentName) {
        return this.delete(`/api/agents/${agentName}`);
    }

    static async getProviders() {
        return this.get('/api/providers');
    }

    static async getTools() {
        return this.get('/api/tools');
    }

    static async reloadAgents() {
        return this.post('/api/reload-agents', {});
    }

    // Chat-specific API calls
    static async sendMessage(agentName, message, conversationId = null, debug = false) {
        return this.post('/api/chat', {
            agent_name: agentName,
            message: message,
            conversation_id: conversationId,
            debug: debug
        });
    }

    static async switchModel(agentName, modelType, modelName, conversationId = null) {
        return this.post('/api/switch-model', {
            agent_name: agentName,
            model_type: modelType,
            model_name: modelName,
            conversation_id: conversationId
        });
    }

    static async getConversations(agentName) {
        return this.get(`/api/conversations/${agentName}`);
    }

    static async getConversation(conversationId) {
        return this.get(`/api/conversation/${conversationId}`);
    }
}