/**
 * TWIZZY Web Interface - Chat Application
 */

class TwizzyChat {
    constructor() {
        this.ws = null;
        this.messagesEl = document.getElementById('messages');
        this.inputEl = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.chatForm = document.getElementById('chatForm');
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.agentInfo = document.getElementById('agentInfo');

        this.init();
    }

    init() {
        this.connect();
        this.setupEventListeners();
        this.autoResizeInput();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

        console.log('Connecting to:', wsUrl);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.setConnected(true);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.setConnected(false);
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    setConnected(connected) {
        if (connected) {
            this.statusDot.classList.add('connected');
            this.statusDot.classList.remove('disconnected');
            this.statusText.textContent = 'Connected';
            this.sendBtn.disabled = false;
        } else {
            this.statusDot.classList.remove('connected');
            this.statusDot.classList.add('disconnected');
            this.statusText.textContent = 'Disconnected';
            this.sendBtn.disabled = true;
        }
    }

    handleMessage(data) {
        console.log('Received:', data);

        switch (data.type) {
            case 'connected':
                // Welcome message already shown
                break;

            case 'status':
                if (data.status === 'thinking') {
                    this.showThinking();
                }
                break;

            case 'response':
                this.hideThinking();
                this.addMessage(data.message, 'assistant');
                break;

            case 'error':
                this.hideThinking();
                this.addMessage(data.message, 'assistant error');
                break;

            case 'status_update':
                this.updateAgentInfo(data.status);
                break;

            case 'improvement':
                this.showImprovement(data.data);
                break;

            case 'reload':
                this.showReloadNotice(data.message);
                break;
        }
    }

    setupEventListeners() {
        // Form submit
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Enter to send (Shift+Enter for new line)
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Clear chat
        this.clearBtn.addEventListener('click', () => this.clearChat());
    }

    autoResizeInput() {
        this.inputEl.addEventListener('input', () => {
            this.inputEl.style.height = 'auto';
            this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 150) + 'px';
        });
    }

    sendMessage() {
        const message = this.inputEl.value.trim();
        if (!message || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        // Add user message to UI
        this.addMessage(message, 'user');

        // Send to server
        this.ws.send(JSON.stringify({ message }));

        // Clear input
        this.inputEl.value = '';
        this.inputEl.style.height = 'auto';
    }

    addMessage(content, type) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.textContent = content;

        messageEl.appendChild(contentEl);
        this.messagesEl.appendChild(messageEl);

        // Scroll to bottom
        this.scrollToBottom();
    }

    showThinking() {
        // Remove any existing thinking message
        this.hideThinking();

        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant thinking';
        messageEl.id = 'thinkingMessage';

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.textContent = 'Thinking';

        messageEl.appendChild(contentEl);
        this.messagesEl.appendChild(messageEl);

        this.scrollToBottom();
    }

    hideThinking() {
        const thinkingEl = document.getElementById('thinkingMessage');
        if (thinkingEl) {
            thinkingEl.remove();
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chatContainer');
        container.scrollTop = container.scrollHeight;
    }

    updateAgentInfo(status) {
        if (this.agentInfo && status) {
            const capabilities = status.enabled_capabilities || [];
            this.agentInfo.innerHTML = `<small>Capabilities: ${capabilities.join(', ') || 'None'}</small>`;
        }
    }

    showImprovement(data) {
        this.addMessage(
            `🔧 Self-improvement applied: ${data.improvement}\nFiles changed: ${data.files_changed?.join(', ') || 'Unknown'}`,
            'assistant'
        );
    }

    showReloadNotice(message) {
        this.addMessage(`⚡ ${message}`, 'assistant');
    }

    async clearChat() {
        try {
            const response = await fetch('/api/clear', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                // Clear messages except welcome
                this.messagesEl.innerHTML = `
                    <div class="message assistant">
                        <div class="message-content">
                            Conversation cleared. How can I help you?
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            console.error('Error clearing chat:', e);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new TwizzyChat();
});
