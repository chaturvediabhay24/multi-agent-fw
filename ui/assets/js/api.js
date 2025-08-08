// API service for interacting with the backend
export class ApiService {
    static async get(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    }

    static async post(endpoint, data) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
            headers: {
                'Content-Type': 'application/json',
            },
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
            method: 'DELETE'
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