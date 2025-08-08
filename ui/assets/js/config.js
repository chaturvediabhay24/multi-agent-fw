// Agent configuration page functionality
import { ApiService } from './api.js';
import { Utils } from './utils.js';

export class AgentConfig {
    constructor() {
        this.providersConfig = {};
        this.availableTools = [];
        this.editingAgent = null;
        this.existingAgents = {};
        this.tools = [];
    }

    async init() {
        await this.loadProvidersConfig();
        await this.loadAvailableTools();
        await this.loadExistingAgents();
        this.setupEventListeners();
    }

    async loadProvidersConfig() {
        try {
            const data = await ApiService.getProviders();
            this.providersConfig = data;
            this.populateProviders();
        } catch (error) {
            console.error('Error loading providers:', error);
            Utils.showStatus('Error loading model providers', true);
        }
    }

    async loadAvailableTools() {
        try {
            const data = await ApiService.getTools();
            this.availableTools = data.tools || [];
            this.populateToolSuggestions();
        } catch (error) {
            console.error('Error loading tools:', error);
        }
    }

    async loadExistingAgents() {
        try {
            const data = await ApiService.getAgents();
            this.existingAgents = data.agents || {};
            this.displayExistingAgents();
        } catch (error) {
            console.error('Error loading existing agents:', error);
            Utils.showStatus('Error loading existing agents', true);
        }
    }

    populateProviders() {
        const modelTypeSelect = document.getElementById('modelType');
        modelTypeSelect.innerHTML = '<option value="">Select Model Type</option>';

        if (this.providersConfig.providers) {
            Object.keys(this.providersConfig.providers).forEach(providerId => {
                const option = document.createElement('option');
                option.value = providerId;
                option.textContent = Utils.capitalize(providerId);
                modelTypeSelect.appendChild(option);
            });

            // Set default provider if specified
            if (this.providersConfig.default_provider) {
                modelTypeSelect.value = this.providersConfig.default_provider;
                modelTypeSelect.dispatchEvent(new Event('change'));
                
                setTimeout(() => {
                    const modelNameSelect = document.getElementById('modelName');
                    if (this.providersConfig.default_model) {
                        modelNameSelect.value = this.providersConfig.default_model;
                    }
                }, 100);
            }
        }
    }

    populateToolSuggestions() {
        const datalist = document.getElementById('toolSuggestions');
        datalist.innerHTML = '';
        
        this.availableTools.forEach(tool => {
            const option = document.createElement('option');
            option.value = tool;
            datalist.appendChild(option);
        });
    }

    displayExistingAgents() {
        const agentsList = document.getElementById('existingAgentsList');
        agentsList.innerHTML = '';

        if (Object.keys(this.existingAgents).length === 0) {
            agentsList.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px; border: 2px dashed #ddd; border-radius: 12px;">
                    <p>No agents configured yet</p>
                    <p style="font-size: 0.9rem; margin-top: 8px;">Create your first agent using the form below</p>
                </div>
            `;
            return;
        }

        Object.keys(this.existingAgents).forEach(agentName => {
            const agent = this.existingAgents[agentName];
            const agentCard = this.createAgentCard(agentName, agent);
            agentsList.appendChild(agentCard);
        });
    }

    createAgentCard(agentName, agent) {
        const agentCard = document.createElement('div');
        agentCard.className = 'agent-card';
        
        const toolsDisplay = agent.tools && agent.tools.length > 0 
            ? agent.tools.map(tool => `<span class="agent-tool-tag">${tool}</span>`).join('')
            : '<span style="color: #666; font-style: italic;">None</span>';

        agentCard.innerHTML = `
            <div class="agent-card-header">
                <div>
                    <div class="agent-name">${Utils.escapeHtml(agentName)}</div>
                    <div class="agent-model">${Utils.escapeHtml(agent.model_type)} - ${Utils.escapeHtml(agent.model_name)}</div>
                </div>
            </div>
            <div class="agent-description">${Utils.escapeHtml(agent.description)}</div>
            <div class="agent-tools">
                <div class="agent-tools-label">Tools:</div>
                <div class="agent-tool-tags">${toolsDisplay}</div>
            </div>
            <div class="agent-actions">
                <button class="edit-btn" onclick="agentConfig.editAgent('${agentName}')">✏️ Edit</button>
                <button class="delete-btn" onclick="agentConfig.deleteAgent('${agentName}')">🗑️ Delete</button>
            </div>
        `;
        
        return agentCard;
    }

    setupEventListeners() {
        const modelTypeSelect = document.getElementById('modelType');
        const modelNameSelect = document.getElementById('modelName');

        modelTypeSelect.addEventListener('change', () => {
            const selectedType = modelTypeSelect.value;
            modelNameSelect.innerHTML = '<option value="">Select Model</option>';
            
            if (selectedType && this.providersConfig.providers && this.providersConfig.providers[selectedType]) {
                const models = this.providersConfig.providers[selectedType];
                models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    modelNameSelect.appendChild(option);
                });
            }
        });

        // Handle form submission
        document.getElementById('agentForm').addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Handle cancel edit
        document.getElementById('cancelBtn').addEventListener('click', () => this.cancelEdit());
        
        // Handle refresh
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshData());

        // Handle tool input
        document.getElementById('toolInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addTool();
            }
        });
    }

    editAgent(agentName) {
        this.editingAgent = agentName;
        const agent = this.existingAgents[agentName];
        
        // Update form title and button
        document.getElementById('formTitle').textContent = `Edit Agent: ${agentName}`;
        document.getElementById('submitBtn').textContent = 'Update Agent';
        document.getElementById('cancelBtn').style.display = 'inline-block';
        
        // Add edit mode indicator
        const form = document.getElementById('agentForm');
        if (!form.querySelector('.form-mode-edit')) {
            const editIndicator = document.createElement('div');
            editIndicator.className = 'form-mode-edit';
            editIndicator.innerHTML = `<strong>✏️ Edit Mode:</strong> Modifying agent "${Utils.escapeHtml(agentName)}". Click "Update Agent" to save changes or "Cancel Edit" to abort.`;
            form.insertBefore(editIndicator, form.firstChild);
        }
        
        // Populate form with existing data
        document.getElementById('agentName').value = agentName;
        document.getElementById('agentName').disabled = true;
        document.getElementById('description').value = agent.description;
        document.getElementById('systemPrompt').value = agent.system_prompt;
        
        // Set model type and name
        document.getElementById('modelType').value = agent.model_type;
        document.getElementById('modelType').dispatchEvent(new Event('change'));
        
        setTimeout(() => {
            document.getElementById('modelName').value = agent.model_name;
        }, 100);
        
        // Set tools
        this.tools = [...(agent.tools || [])];
        this.renderTools();
        
        // Set other settings
        document.getElementById('parallelTools').checked = agent.parallel_tools !== false;
        document.getElementById('maxParallelTools').value = agent.max_parallel_tools || 3;
        document.getElementById('debug').checked = agent.debug === true;
        
        // Scroll to form
        Utils.scrollToElement(document.getElementById('agentForm'));
    }

    cancelEdit() {
        this.editingAgent = null;
        
        // Reset form title and button
        document.getElementById('formTitle').textContent = 'Create New Agent';
        document.getElementById('submitBtn').textContent = 'Create Agent';
        document.getElementById('cancelBtn').style.display = 'none';
        
        // Remove edit mode indicator
        const editIndicator = document.querySelector('.form-mode-edit');
        if (editIndicator) {
            editIndicator.remove();
        }
        
        // Reset form
        document.getElementById('agentForm').reset();
        document.getElementById('agentName').disabled = false;
        this.tools = [];
        this.renderTools();
        document.getElementById('modelName').innerHTML = '<option value="">Select Model</option>';
    }

    async deleteAgent(agentName) {
        if (!confirm(`Are you sure you want to delete the agent "${agentName}"?\n\nThis action cannot be undone.`)) {
            return;
        }
        
        try {
            const result = await ApiService.deleteAgent(agentName);
            Utils.showStatus(result.message);
            
            // Reload agents
            await this.loadExistingAgents();
            
            // Cancel edit if we were editing the deleted agent
            if (this.editingAgent === agentName) {
                this.cancelEdit();
            }
            
        } catch (error) {
            Utils.showStatus('Error deleting agent: ' + error.message, true);
        }
    }

    async refreshData() {
        const refreshBtn = document.getElementById('refreshBtn');
        Utils.setButtonLoading(refreshBtn, true, '🔄 Refreshing...');
        
        try {
            await this.loadProvidersConfig();
            await this.loadAvailableTools();
            await this.loadExistingAgents();
            Utils.showStatus('Data refreshed successfully');
        } catch (error) {
            Utils.showStatus('Error refreshing data', true);
        } finally {
            Utils.setButtonLoading(refreshBtn, false);
        }
    }

    addTool() {
        const toolInput = document.getElementById('toolInput');
        const toolName = toolInput.value.trim();
        
        if (toolName && !this.tools.includes(toolName)) {
            this.tools.push(toolName);
            this.renderTools();
            toolInput.value = '';
        }
    }

    removeTool(toolName) {
        this.tools = this.tools.filter(tool => tool !== toolName);
        this.renderTools();
    }

    renderTools() {
        const toolsList = document.getElementById('toolsList');
        toolsList.innerHTML = '';
        
        this.tools.forEach(tool => {
            const toolTag = document.createElement('div');
            toolTag.className = 'tool-tag';
            toolTag.innerHTML = `
                ${Utils.escapeHtml(tool)}
                <button type="button" class="tool-remove" onclick="agentConfig.removeTool('${tool}')">×</button>
            `;
            toolsList.appendChild(toolTag);
        });
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submitBtn');
        const isEditing = this.editingAgent !== null;
        
        Utils.setButtonLoading(submitBtn, true, isEditing ? 'Updating Agent...' : 'Creating Agent...');

        try {
            const formData = new FormData(e.target);
            const agentName = isEditing ? this.editingAgent : formData.get('agentName');
            
            const config = {
                class_name: "CustomAgent",
                description: formData.get('description'),
                model_type: formData.get('modelType'),
                model_name: formData.get('modelName'),
                system_prompt: formData.get('systemPrompt'),
                tools: this.tools,
                parallel_tools: formData.get('parallelTools') === 'on',
                max_parallel_tools: parseInt(formData.get('maxParallelTools')),
                debug: formData.get('debug') === 'on'
            };

            // Validate required fields
            const requiredFields = ['description', 'modelType', 'modelName', 'systemPrompt'];
            const missing = Utils.validateRequired(Utils.parseFormData(formData), requiredFields);
            if (missing.length > 0) {
                throw new Error(`Missing required fields: ${missing.join(', ')}`);
            }

            let result;
            if (isEditing) {
                result = await ApiService.updateAgent(agentName, config);
            } else {
                result = await ApiService.createAgent(agentName, config);
            }
            
            Utils.showStatus(result.message);
            
            // Reload existing agents
            await this.loadExistingAgents();
            
            if (isEditing) {
                // Exit edit mode
                this.cancelEdit();
            } else {
                // Reset form for new creation
                e.target.reset();
                this.tools = [];
                this.renderTools();
                document.getElementById('modelName').innerHTML = '<option value="">Select Model</option>';
            }

        } catch (error) {
            Utils.showStatus(`Error ${isEditing ? 'updating' : 'creating'} agent: ` + error.message, true);
        } finally {
            Utils.setButtonLoading(submitBtn, false);
        }
    }
}

// Global instance for onclick handlers
window.agentConfig = new AgentConfig();