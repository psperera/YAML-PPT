// HyFlux PPT Generator - Frontend JavaScript

let currentFilename = null;

// DOM Elements
const yamlEditor = document.getElementById('yamlEditor');
const loadTemplateBtn = document.getElementById('loadTemplate');
const uploadFileBtn = document.getElementById('uploadFile');
const fileInput = document.getElementById('fileInput');
const saveBtn = document.getElementById('saveBtn');
const validateBtn = document.getElementById('validateBtn');
const generateBtn = document.getElementById('generateBtn');
const downloadBtn = document.getElementById('downloadBtn');
const statusBar = document.getElementById('statusBar');

// Event Listeners
loadTemplateBtn.addEventListener('click', loadTemplate);
uploadFileBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileUpload);
saveBtn.addEventListener('click', saveYAML);
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

// Save YAML
async function saveYAML() {
    const yamlContent = yamlEditor.value.trim();
    
    if (!yamlContent) {
        showStatus('No content to save', 'error');
        return;
    }
    
    // Validate YAML first
    try {
        const validateResponse = await fetch('/api/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ yaml: yamlContent })
        });
        
        const validateData = await validateResponse.json();
        if (!validateData.success) {
            const proceed = confirm('YAML has validation errors. Save anyway?');
            if (!proceed) return;
        }
    } catch (error) {
        console.error('Validation error:', error);
    }
    
    // Ask for filename
    const defaultName = 'presentation_' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '.yaml';
    const filename = prompt('Enter filename (or leave empty for auto-generated):', defaultName) || defaultName;
    
    if (!filename) return;
    
    showStatus('Saving YAML...', 'info');
    saveBtn.disabled = true;
    
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                yaml: yamlContent,
                filename: filename
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(`✓ ${data.message}`, 'success');
            
            // Also offer to download
            const download = confirm('YAML saved to server. Download a copy?');
            if (download) {
                downloadYAMLFile(data.filename);
            }
        } else {
            showStatus('✗ ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Error saving: ' + error.message, 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

// Download YAML file
function downloadYAMLFile(filename) {
    window.location.href = `/api/download-yaml/${filename}`;
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
    
    // Test Ollama connection and load models
    testOllamaConnection();
    
    // Load saved files list
    loadSavedFiles();
});

// Test Ollama connection
async function testOllamaConnection() {
    try {
        const response = await fetch('/api/chat/test');
        const data = await response.json();
        
        if (data.success) {
            console.log('Ollama connection successful:', data.ollama_url);
            loadOllamaModels();
        } else {
            console.warn('Ollama connection failed:', data.message);
            setChatStatus('Ollama not connected. Chat will not work until Ollama is running.', 'error');
            
            // Show helpful message in chat
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'chat-message bot-message';
                errorDiv.innerHTML = `
                    <div class="message-content">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p><strong>Ollama Connection Error</strong><br>
                        ${data.message}<br><br>
                        <strong>To fix:</strong><br>
                        ${data.suggestions ? data.suggestions.map(s => '• ' + s).join('<br>') : 'Please ensure Ollama is running on your host machine.'}
                        </p>
                    </div>
                `;
                chatMessages.appendChild(errorDiv);
            }
        }
    } catch (error) {
        console.error('Error testing Ollama connection:', error);
    }
}

// Load saved files list
async function loadSavedFiles() {
    try {
        const response = await fetch('/api/saved-files');
        const data = await response.json();
        
        if (data.success && data.files && data.files.length > 0) {
            const savedFilesCard = document.getElementById('savedFilesCard');
            const savedFilesList = document.getElementById('savedFilesList');
            
            savedFilesCard.style.display = 'block';
            savedFilesList.innerHTML = '';
            
            data.files.slice(0, 5).forEach(file => {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'saved-file-item';
                fileDiv.innerHTML = `
                    <div class="file-info">
                        <strong>${file.filename}</strong>
                        <span class="file-meta">${formatFileSize(file.size)} • ${formatDate(file.modified)}</span>
                    </div>
                    <div class="file-actions">
                        <button class="btn-small btn-primary" onclick="loadSavedFile('${file.filename}')">
                            <i class="fas fa-folder-open"></i> Load
                        </button>
                        <button class="btn-small btn-secondary" onclick="downloadYAMLFile('${file.filename}')">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                `;
                savedFilesList.appendChild(fileDiv);
            });
            
            if (data.files.length > 5) {
                const moreDiv = document.createElement('div');
                moreDiv.className = 'more-files';
                moreDiv.textContent = `... and ${data.files.length - 5} more files`;
                savedFilesList.appendChild(moreDiv);
            }
        }
    } catch (error) {
        console.log('Could not load saved files:', error);
    }
}

// Load a saved file
async function loadSavedFile(filename) {
    try {
        const response = await fetch(`/api/load-file/${filename}`);
        const data = await response.json();
        
        if (data.success) {
            yamlEditor.value = data.content;
            showStatus(`Loaded: ${data.filename}`, 'success');
        } else {
            showStatus('Error loading file: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Error loading file: ' + error.message, 'error');
    }
}

// Helper functions
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

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
            // Render markdown in chat
            addChatMessage(data.response, 'bot', true); // true = render markdown
            
            // If YAML was extracted, auto-populate the editor
            if (data.yaml_content) {
                yamlEditor.value = data.yaml_content;
                showStatus('✓ YAML extracted and loaded into editor', 'success');
                
                // Auto-validate
                setTimeout(() => {
                    validateYAML();
                }, 500);
            }
            
            setChatStatus('', '');
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

function addChatMessage(text, type, renderMarkdown = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    const icon = type === 'user' ? 'fa-user' : 'fa-robot';
    let content = text;
    
    if (renderMarkdown) {
        // Simple markdown rendering
        content = renderSimpleMarkdown(text);
    } else {
        // Escape HTML and preserve line breaks
        content = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <i class="fas ${icon}"></i>
            <div class="message-text">${content}</div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderSimpleMarkdown(text) {
    // Escape HTML first
    let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Code blocks
    html = html.replace(/```yaml\n([\s\S]*?)```/g, '<pre class="yaml-block"><code>$1</code></pre>');
    html = html.replace(/```\n([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Lists
    html = html.replace(/^\d+\.\s+(.*)$/gim, '<li>$1</li>');
    html = html.replace(/^-\s+(.*)$/gim, '<li>$1</li>');
    
    // Wrap consecutive list items in ul
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // Tables
    html = html.replace(/\|(.+)\|/g, function(match, content) {
        const cells = content.split('|').map(cell => cell.trim());
        return '<tr>' + cells.map(cell => {
            if (cell.includes('---')) return '';
            const isHeader = cell.includes('**');
            const tag = isHeader ? 'th' : 'td';
            return `<${tag}>${cell.replace(/\*\*/g, '')}</${tag}>`;
        }).join('') + '</tr>';
    });
    
    // Wrap table rows in table
    html = html.replace(/(<tr>.*<\/tr>\n?)+/g, '<table>$&</table>');
    
    // Horizontal rules
    html = html.replace(/^---$/gim, '<hr>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
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

