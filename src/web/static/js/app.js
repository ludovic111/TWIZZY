/**
 * TWIZZY Web Interface - Enhanced Chat with Persistent Memory
 */

class TwizzyChat {
    constructor() {
        this.ws = null;
        this.currentConversationId = null;
        this.conversations = [];
        this.isLoading = false;
        
        // DOM elements
        this.messagesEl = document.getElementById('messages');
        this.inputEl = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.chatForm = document.getElementById('chatForm');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.conversationsListEl = document.getElementById('conversationsList');
        this.searchInput = document.getElementById('searchChats');
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.chatTitle = document.getElementById('chatTitle');
        this.chatSubtitle = document.getElementById('chatSubtitle');
        
        this.init();
    }

    init() {
        this.connect();
        this.setupEventListeners();
        this.autoResizeInput();
        this.loadConversations();
        this.loadCurrentConversation();
        
        // Setup suggestion chips
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                this.inputEl.value = chip.dataset.message;
                this.sendMessage();
            });
        });
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
            this.statusText.textContent = 'Connected';
            this.sendBtn.disabled = false;
        } else {
            this.statusDot.classList.remove('connected');
            this.statusText.textContent = 'Disconnected';
            this.sendBtn.disabled = true;
        }
    }

    handleMessage(data) {
        console.log('Received:', data);

        switch (data.type) {
            case 'connected':
                if (data.conversation_id) {
                    this.currentConversationId = data.conversation_id;
                }
                break;

            case 'status':
                if (data.status === 'thinking') {
                    this.showThinking();
                }
                break;

            case 'response':
                this.hideThinking();
                this.addMessage(data.message, 'assistant', data.timestamp);
                this.refreshConversations();
                break;

            case 'error':
                this.hideThinking();
                this.addMessage(data.message, 'assistant error');
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
        
        // New chat
        this.newChatBtn.addEventListener('click', () => this.startNewChat());
        
        // Search conversations
        this.searchInput.addEventListener('input', (e) => {
            this.filterConversations(e.target.value);
        });
    }

    autoResizeInput() {
        this.inputEl.addEventListener('input', () => {
            this.inputEl.style.height = 'auto';
            this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 200) + 'px';
            
            // Enable/disable send button
            this.sendBtn.disabled = this.inputEl.value.trim().length === 0;
        });
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            
            if (data.conversations) {
                this.conversations = data.conversations;
                this.renderConversations();
            }
        } catch (e) {
            console.error('Error loading conversations:', e);
        }
    }

    async loadCurrentConversation() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            if (data.conversation_id) {
                this.currentConversationId = data.conversation_id;
                this.updateChatTitle(data.title || 'Current Chat');
            }
            
            if (data.messages && data.messages.length > 0) {
                // Clear welcome message
                this.messagesEl.innerHTML = '';
                
                // Load messages
                data.messages.forEach(msg => {
                    if (msg.role !== 'system') {
                        this.addMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant', msg.timestamp, false);
                    }
                });
                
                this.scrollToBottom();
            }
        } catch (e) {
            console.error('Error loading conversation:', e);
        }
    }

    renderConversations() {
        if (this.conversations.length === 0) {
            this.conversationsListEl.innerHTML = '<div class="empty-conversations">No conversations yet</div>';
            return;
        }

        this.conversationsListEl.innerHTML = this.conversations.map(conv => {
            const isActive = conv.id === this.currentConversationId;
            const date = new Date(conv.updated_at).toLocaleDateString();
            const messageCount = conv.message_count || 0;
            
            return `
                <div class="conversation-item ${isActive ? 'active' : ''}" data-id="${conv.id}">
                    <div class="conversation-icon">💬</div>
                    <div class="conversation-info">
                        <div class="conversation-title">${this.escapeHtml(conv.title)}</div>
                        <div class="conversation-meta">
                            <span>${date}</span>
                            <span>•</span>
                            <span>${messageCount} messages</span>
                        </div>
                    </div>
                    <button class="conversation-delete" title="Delete conversation" data-id="${conv.id}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            `;
        }).join('');

        // Add click handlers
        this.conversationsListEl.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.conversation-delete')) {
                    this.loadConversation(item.dataset.id);
                }
            });
        });

        this.conversationsListEl.querySelectorAll('.conversation-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteConversation(btn.dataset.id);
            });
        });
    }

    filterConversations(query) {
        const items = this.conversationsListEl.querySelectorAll('.conversation-item');
        const lowerQuery = query.toLowerCase();
        
        items.forEach(item => {
            const title = item.querySelector('.conversation-title').textContent.toLowerCase();
            item.style.display = title.includes(lowerQuery) ? 'flex' : 'none';
        });
    }

    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`);
            const data = await response.json();
            
            if (data.success) {
                this.currentConversationId = conversationId;
                this.updateChatTitle(data.conversation.title);
                
                // Clear and load messages
                this.messagesEl.innerHTML = '';
                
                data.conversation.messages.forEach(msg => {
                    if (msg.role !== 'system') {
                        this.addMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant', msg.timestamp, false);
                    }
                });
                
                this.scrollToBottom();
                this.renderConversations(); // Update active state
                
                // Notify server of conversation switch
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ 
                        type: 'switch_conversation', 
                        conversation_id: conversationId 
                    }));
                }
            }
        } catch (e) {
            console.error('Error loading conversation:', e);
        }
    }

    async deleteConversation(conversationId) {
        if (!confirm('Delete this conversation?')) return;
        
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                this.conversations = this.conversations.filter(c => c.id !== conversationId);
                this.renderConversations();
                
                if (this.currentConversationId === conversationId) {
                    this.startNewChat();
                }
            }
        } catch (e) {
            console.error('Error deleting conversation:', e);
        }
    }

    async startNewChat() {
        try {
            const response = await fetch('/api/conversations/new', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.currentConversationId = data.conversation_id;
                this.updateChatTitle('New Chat');
                
                // Reset UI
                this.messagesEl.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-icon">🧠</div>
                        <h2>New Conversation</h2>
                        <p>How can I help you today?</p>
                        <div class="suggestions">
                            <button class="suggestion-chip" data-message="List all files on my Desktop">List Desktop files</button>
                            <button class="suggestion-chip" data-message="What can you do?">What can you do?</button>
                            <button class="suggestion-chip" data-message="Improve your own code">Self-improve</button>
                        </div>
                    </div>
                `;
                
                // Re-attach suggestion handlers
                this.messagesEl.querySelectorAll('.suggestion-chip').forEach(chip => {
                    chip.addEventListener('click', () => {
                        this.inputEl.value = chip.dataset.message;
                        this.sendMessage();
                    });
                });
                
                this.renderConversations();
                this.refreshConversations();
            }
        } catch (e) {
            console.error('Error starting new chat:', e);
        }
    }

    updateChatTitle(title) {
        this.chatTitle.textContent = title;
        const count = this.conversations.find(c => c.id === this.currentConversationId)?.message_count || 0;
        this.chatSubtitle.textContent = count > 0 ? `${count} messages` : 'Start a conversation';
    }

    sendMessage() {
        const message = this.inputEl.value.trim();
        if (!message || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        // Remove welcome message if present
        const welcome = this.messagesEl.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        // Add user message to UI
        this.addMessage(message, 'user', null, true);

        // Send to server
        this.ws.send(JSON.stringify({ 
            message,
            conversation_id: this.currentConversationId
        }));

        // Clear input
        this.inputEl.value = '';
        this.inputEl.style.height = 'auto';
        this.sendBtn.disabled = true;
    }

    addMessage(content, type, timestamp, animate = true) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        if (!animate) messageEl.style.animation = 'none';

        const time = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        
        const avatar = type === 'user' ? '👤' : '🧠';
        const author = type === 'user' ? 'You' : 'TWIZZY';
        
        // Handle markdown-style formatting
        const formattedContent = this.formatMessage(content);
        
        messageEl.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content-wrapper">
                <div class="message-header">
                    <span class="message-author">${author}</span>
                    ${time ? `<span class="message-time">${time}</span>` : ''}
                </div>
                <div class="message-content">${formattedContent}</div>
            </div>
        `;

        this.messagesEl.appendChild(messageEl);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Escape HTML
        let formatted = this.escapeHtml(content);
        
        // Convert code blocks
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // Convert inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Convert bold
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Convert italic
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Convert newlines to <br> (but not inside pre blocks)
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showThinking() {
        this.hideThinking();

        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant thinking';
        messageEl.id = 'thinkingMessage';

        messageEl.innerHTML = `
            <div class="message-avatar">🧠</div>
            <div class="message-content-wrapper">
                <div class="message-header">
                    <span class="message-author">TWIZZY</span>
                </div>
                <div class="message-content">Thinking</div>
            </div>
        `;

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
        const container = document.getElementById('messagesContainer');
        container.scrollTop = container.scrollHeight;
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
        if (!confirm('Clear this conversation?')) return;
        
        try {
            const response = await fetch('/api/clear', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                this.messagesEl.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-icon">🧠</div>
                        <h2>Conversation Cleared</h2>
                        <p>How can I help you?</p>
                    </div>
                `;
                this.refreshConversations();
            }
        } catch (e) {
            console.error('Error clearing chat:', e);
        }
    }

    refreshConversations() {
        // Debounced refresh
        clearTimeout(this.refreshTimeout);
        this.refreshTimeout = setTimeout(() => this.loadConversations(), 500);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new TwizzyChat();
});
