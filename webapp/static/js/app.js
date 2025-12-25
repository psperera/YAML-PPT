// HyFlux PPT Generator - Frontend JavaScript

let currentFilename = null;

// DOM Elements
const yamlEditor = document.getElementById('yamlEditor');
const loadTemplateBtn = document.getElementById('loadTemplate');
const uploadFileBtn = document.getElementById('uploadFile');
const fileInput = document.getElementById('fileInput');
const validateBtn = document.getElementById('validateBtn');
const generateBtn = document.getElementById('generateBtn');
const downloadBtn = document.getElementById('downloadBtn');
const statusBar = document.getElementById('statusBar');

// Event Listeners
loadTemplateBtn.addEventListener('click', loadTemplate);
uploadFileBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileUpload);
validateBtn.addEventListener('click', validateYAML);
generateBtn.addEventListener('click', generatePresentation);
downloadBtn.addEventListener('click', downloadPresentation);

// Load template
async function loadTemplate() {
    showStatus('Loading template...', 'info');
    try {
        const response = await fetch('/api/template');
        const data = await response.json();
        
        if (data.success) {
            yamlEditor.value = data.content;
            showStatus('Template loaded successfully!', 'success');
        } else {
            showStatus('Error: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Error loading template: ' + error.message, 'error');
    }
}

// Handle file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        yamlEditor.value = e.target.result;
        showStatus('File loaded: ' + file.name, 'success');
    };
    reader.onerror = function() {
        showStatus('Error reading file', 'error');
    };
    reader.readAsText(file);
    
    // Reset file input
    fileInput.value = '';
}

// Validate YAML
async function validateYAML() {
    const yamlContent = yamlEditor.value.trim();
    
    if (!yamlContent) {
        showStatus('Please enter YAML content first', 'error');
        return;
    }
    
    showStatus('Validating YAML...', 'info');
    
    try {
        const response = await fetch('/api/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ yaml: yamlContent })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('✓ ' + data.message, 'success');
        } else {
            showStatus('✗ ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Error validating: ' + error.message, 'error');
    }
}

// Generate presentation
async function generatePresentation() {
    const yamlContent = yamlEditor.value.trim();
    
    if (!yamlContent) {
        showStatus('Please enter YAML content first', 'error');
        return;
    }
    
    showStatus('Generating presentation... This may take a moment.', 'info');
    generateBtn.disabled = true;
    downloadBtn.style.display = 'none';
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ yaml: yamlContent })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentFilename = data.filename;
            showStatus(`✓ ${data.message} - Ready to download!`, 'success');
            downloadBtn.style.display = 'inline-flex';
        } else {
            showStatus('✗ ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Error generating: ' + error.message, 'error');
    } finally {
        generateBtn.disabled = false;
    }
}

// Download presentation
function downloadPresentation() {
    if (!currentFilename) {
        showStatus('No file to download', 'error');
        return;
    }
    
    window.location.href = `/api/download/${currentFilename}`;
    showStatus('Download started...', 'info');
}

// Show status message
function showStatus(message, type = 'info') {
    statusBar.textContent = message;
    statusBar.className = 'status-bar ' + type;
    
    // Auto-clear success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            if (statusBar.className.includes('success')) {
                statusBar.textContent = '';
                statusBar.className = 'status-bar';
            }
        }, 5000);
    }
}

// Auto-save to localStorage
yamlEditor.addEventListener('input', function() {
    localStorage.setItem('hyflux_yaml_content', yamlEditor.value);
});

// Load from localStorage on page load
window.addEventListener('load', function() {
    const saved = localStorage.getItem('hyflux_yaml_content');
    if (saved) {
        yamlEditor.value = saved;
        showStatus('Restored previous content from browser storage', 'info');
    }
    
    // Load available models
    loadOllamaModels();
});

// Chat functionality
const chatInput = document.getElementById('chatInput');
const sendChatBtn = document.getElementById('sendChatBtn');
const chatMessages = document.getElementById('chatMessages');
const chatStatus = document.getElementById('chatStatus');
const modelSelect = document.getElementById('modelSelect');

// Send chat message
sendChatBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
});

async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addChatMessage(message, 'user');
    chatInput.value = '';
    chatInput.disabled = true;
    sendChatBtn.disabled = true;
    setChatStatus('Thinking...', 'loading');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                model: modelSelect.value
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addChatMessage(data.response, 'bot');
            setChatStatus('', '');
            
            // If the response contains YAML code blocks, offer to insert it
            if (data.response.includes('```yaml') || data.response.includes('```')) {
                // Could add a button to insert YAML into editor
            }
        } else {
            addChatMessage('Error: ' + data.error, 'bot');
            setChatStatus('Error: ' + data.error, 'error');
        }
    } catch (error) {
        addChatMessage('Error connecting to Ollama: ' + error.message, 'bot');
        setChatStatus('Connection error', 'error');
    } finally {
        chatInput.disabled = false;
        sendChatBtn.disabled = false;
        chatInput.focus();
    }
}

function addChatMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    const icon = type === 'user' ? 'fa-user' : 'fa-robot';
    const content = text.replace(/\n/g, '<br>');
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <i class="fas ${icon}"></i>
            <p>${content}</p>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setChatStatus(message, type) {
    chatStatus.textContent = message;
    chatStatus.className = 'chat-status ' + type;
}

async function loadOllamaModels() {
    try {
        const response = await fetch('/api/chat/models');
        const data = await response.json();
        
        if (data.success && data.models && data.models.length > 0) {
            // Clear existing options
            modelSelect.innerHTML = '';
            
            // Add available models
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
            
            // Set default to first model if available
            if (data.models.length > 0) {
                modelSelect.value = data.models[0];
            }
        }
    } catch (error) {
        console.log('Could not load Ollama models:', error);
        // Keep default models
    }
}

