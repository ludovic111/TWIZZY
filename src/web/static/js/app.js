/**
 * TWIZZY - Enhanced Chat with Persistent Memory
 * Features: Toast notifications, keyboard shortcuts, auto-reconnect, conversation management
 */

class TwizzyApp {
    constructor() {
        this.ws = null;
        this.currentConversationId = null;
        this.conversations = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        
        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.connect();
        this.loadConversations();
        this.loadCurrentConversation();
    }

    cacheElements() {
        this.elements = {
            messages: document.getElementById('messages'),
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            clearBtn: document.getElementById('clearBtn'),
            chatForm: document.getElementById('chatForm'),
            newChatBtn: document.getElementById('newChatBtn'),
            conversationsList: document.getElementById('conversationsList'),
            searchInput: document.getElementById('searchChats'),
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            chatTitle: document.getElementById('chatTitle'),
            chatSubtitle: document.getElementById('chatSubtitle'),
            toastContainer: document.getElementById('toastContainer'),
            sidebar: document.getElementById('sidebar'),
            menuToggle: document.getElementById('menuToggle'),
            modalOverlay: document.getElementById('modalOverlay'),
            modalTitle: document.getElementById('modalTitle'),
            modalMessage: document.getElementById('modalMessage'),
            modalCancel: document.getElementById('modalCancel'),
            modalConfirm: document.getElementById('modalConfirm'),
            welcomeScreen: document.getElementById('welcomeScreen'),
            messagesContainer: document.getElementById('messagesContainer'),
        };
    }

    // WebSocket Connection
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

        console.log('Connecting to WebSocket...');
        this.setStatus('connecting');
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.setStatus('connected');
            this.elements.sendBtn.disabled = this.elements.messageInput.value.trim() === '';
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.setStatus('disconnected');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showToast('Connection error', 'error');
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.setStatus('connecting');
            this.showToast(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'warning');
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            this.showToast('Failed to connect. Please refresh the page.', 'error');
        }
    }

    setStatus(status) {
        const dot = this.elements.statusDot;
        const text = this.elements.statusText;
        
        dot.classList.remove('connected', 'connecting');
        
        switch (status) {
            case 'connected':
                dot.classList.add('connected');
                text.textContent = 'Connected';
                break;
            case 'connecting':
                dot.classList.add('connecting');
                text.textContent = 'Connecting...';
                break;
            case 'disconnected':
                text.textContent = 'Disconnected';
                break;
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
                this.saveToMemory();
                break;

            case 'error':
                this.hideThinking();
                this.addMessage(data.message, 'error');
                this.showToast('Error: ' + data.message, 'error');
                break;

            case 'improvement':
                this.showImprovement(data.data);
                break;

            case 'reload':
                this.showReloadNotice(data.message);
                break;
        }
    }

    // Event Listeners
    setupEventListeners() {
        // Form submit
        this.elements.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Input handling
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.elements.messageInput.addEventListener('input', () => {
            this.autoResizeInput();
            this.elements.sendBtn.disabled = this.elements.messageInput.value.trim() === '';
        });

        // Buttons
        this.elements.clearBtn.addEventListener('click', () => this.confirmClear());
        this.elements.newChatBtn.addEventListener('click', () => this.startNewChat());
        this.elements.menuToggle.addEventListener('click', () => this.toggleSidebar());

        // Search
        this.elements.searchInput.addEventListener('input', (e) => {
            this.filterConversations(e.target.value);
        });

        // Suggestion chips
        this.elements.messages.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                this.elements.messageInput.value = chip.dataset.message;
                this.sendMessage();
            });
        });

        // Modal
        this.elements.modalCancel.addEventListener('click', () => this.hideModal());
        this.elements.modalOverlay.addEventListener('click', (e) => {
            if (e.target === this.elements.modalOverlay) this.hideModal();
        });

        // Close sidebar on mobile when clicking outside
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && 
                !this.elements.sidebar.contains(e.target) && 
                !this.elements.menuToggle.contains(e.target)) {
                this.elements.sidebar.classList.remove('open');
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K - Focus search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                this.elements.searchInput.focus();
            }
            
            // Cmd/Ctrl + N - New chat
            if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
                e.preventDefault();
                this.startNewChat();
            }
            
            // Cmd/Ctrl + / - Focus input
            if ((e.metaKey || e.ctrlKey) && e.key === '/') {
                e.preventDefault();
                this.elements.messageInput.focus();
            }
            
            // Escape - Close sidebar on mobile
            if (e.key === 'Escape') {
                this.elements.sidebar.classList.remove('open');
                this.hideModal();
            }
        });
    }

    // UI Functions
    autoResizeInput() {
        const input = this.elements.messageInput;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    }

    toggleSidebar() {
        this.elements.sidebar.classList.toggle('open');
    }

    // Toast Notifications
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span>${icons[type] || 'ℹ'}</span>
            <span>${message}</span>
        `;
        
        this.elements.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    // Modal
    showModal(title, message, onConfirm, isDanger = false) {
        this.elements.modalTitle.textContent = title;
        this.elements.modalMessage.textContent = message;
        this.elements.modalConfirm.className = isDanger ? 'btn btn-danger' : 'btn btn-primary';
        this.elements.modalOverlay.classList.add('active');
        
        this.modalCallback = onConfirm;
        
        this.elements.modalConfirm.onclick = () => {
            this.hideModal();
            if (this.modalCallback) this.modalCallback();
        };
    }

    hideModal() {
        this.elements.modalOverlay.classList.remove('active');
        this.modalCallback = null;
    }

    // Conversation Management
    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            
            if (data.success && data.conversations) {
                this.conversations = data.conversations;
                this.renderConversations();
            } else {
                this.conversations = [];
                this.renderConversations();
            }
        } catch (e) {
            console.error('Error loading conversations:', e);
            this.elements.conversationsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <div>Failed to load conversations</div>
                </div>
            `;
        }
    }

    renderConversations() {
        if (this.conversations.length === 0) {
            this.elements.conversationsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💬</div>
                    <div>No conversations yet</div>
                </div>
            `;
            return;
        }

        this.elements.conversationsList.innerHTML = this.conversations.map(conv => {
            const isActive = conv.id === this.currentConversationId;
            const date = new Date(conv.updated_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric'
            });
            const messageCount = conv.message_count || conv.messages?.length || 0;
            const title = this.escapeHtml(conv.title || 'Untitled');
            
            return `
                <div class="conversation-item ${isActive ? 'active' : ''}" data-id="${conv.id}" title="${title}">
                    <div class="conversation-icon">💬</div>
                    <div class="conversation-info">
                        <div class="conversation-title">${title}</div>
                        <div class="conversation-meta">
                            <span>${date}</span>
                            <span>•</span>
                            <span>${messageCount} messages</span>
                        </div>
                    </div>
                    <button class="conversation-delete" title="Delete" data-id="${conv.id}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            `;
        }).join('');

        // Add click handlers
        this.elements.conversationsList.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.conversation-delete')) {
                    this.loadConversation(item.dataset.id);
                }
            });
        });

        this.elements.conversationsList.querySelectorAll('.conversation-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.confirmDelete(btn.dataset.id);
            });
        });
    }

    filterConversations(query) {
        const items = this.elements.conversationsList.querySelectorAll('.conversation-item');
        const lowerQuery = query.toLowerCase();
        
        items.forEach(item => {
            const title = item.querySelector('.conversation-title').textContent.toLowerCase();
            item.style.display = title.includes(lowerQuery) ? 'flex' : 'none';
        });
    }

    async loadCurrentConversation() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            if (data.conversation_id) {
                this.currentConversationId = data.conversation_id;
                this.updateChatTitle(data.title || 'Current Chat', data.message_count || 0);
            }
            
            if (data.messages && data.messages.length > 0) {
                this.elements.welcomeScreen?.remove();
                
                data.messages.forEach(msg => {
                    if (msg.role !== 'system') {
                        this.addMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant', msg.timestamp, false);
                    }
                });
                
                this.scrollToBottom();
            }
        } catch (e) {
            console.error('Error loading current conversation:', e);
        }
    }

    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`);
            const data = await response.json();
            
            if (data.success && data.conversation) {
                this.currentConversationId = conversationId;
                this.updateChatTitle(data.conversation.title, data.conversation.messages?.length || 0);
                
                // Clear and load messages
                this.elements.messages.innerHTML = '';
                
                if (data.conversation.messages && data.conversation.messages.length > 0) {
                    data.conversation.messages.forEach(msg => {
                        if (msg.role !== 'system') {
                            this.addMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant', msg.timestamp, false);
                        }
                    });
                } else {
                    this.showWelcomeScreen();
                }
                
                this.scrollToBottom();
                this.renderConversations();
                
                // Close sidebar on mobile
                if (window.innerWidth <= 768) {
                    this.elements.sidebar.classList.remove('open');
                }
                
                this.showToast('Conversation loaded', 'success');
            }
        } catch (e) {
            console.error('Error loading conversation:', e);
            this.showToast('Failed to load conversation', 'error');
        }
    }

    confirmDelete(conversationId) {
        this.showModal(
            'Delete Conversation',
            'Are you sure you want to delete this conversation? This action cannot be undone.',
            () => this.deleteConversation(conversationId),
            true
        );
    }

    async deleteConversation(conversationId) {
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
                
                this.showToast('Conversation deleted', 'success');
            }
        } catch (e) {
            console.error('Error deleting conversation:', e);
            this.showToast('Failed to delete conversation', 'error');
        }
    }

    async startNewChat() {
        try {
            const response = await fetch('/api/conversations/new', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                this.currentConversationId = data.conversation_id;
                this.updateChatTitle('New Chat', 0);
                this.showWelcomeScreen();
                this.loadConversations();
                this.showToast('New chat started', 'success');
                
                // Focus input
                this.elements.messageInput.focus();
            }
        } catch (e) {
            console.error('Error starting new chat:', e);
            this.showToast('Failed to start new chat', 'error');
        }
    }

    showWelcomeScreen() {
        this.elements.messages.innerHTML = `
            <div class="welcome-message" id="welcomeScreen">
                <div class="welcome-icon">🧠</div>
                <h2>New Conversation</h2>
                <p>How can I help you today?</p>
                <div class="suggestions">
                    <button class="suggestion-chip" data-message="List all files on my Desktop">
                        <span class="suggestion-icon">📁</span>
                        List Desktop files
                    </button>
                    <button class="suggestion-chip" data-message="What did we talk about before?">
                        <span class="suggestion-icon">💭</span>
                        Recall memory
                    </button>
                </div>
            </div>
        `;
        
        this.elements.messages.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                this.elements.messageInput.value = chip.dataset.message;
                this.sendMessage();
            });
        });
    }

    confirmClear() {
        this.showModal(
            'Clear Conversation',
            'Are you sure you want to clear this conversation? This will remove all messages.',
            () => this.clearChat(),
            true
        );
    }

    async clearChat() {
        try {
            const response = await fetch('/api/clear', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                this.showWelcomeScreen();
                this.loadConversations();
                this.showToast('Conversation cleared', 'success');
            }
        } catch (e) {
            console.error('Error clearing chat:', e);
            this.showToast('Failed to clear conversation', 'error');
        }
    }

    updateChatTitle(title, messageCount = 0) {
        this.elements.chatTitle.textContent = title;
        this.elements.chatSubtitle.textContent = messageCount > 0 
            ? `${messageCount} message${messageCount !== 1 ? 's' : ''}` 
            : 'Start a conversation';
    }

    // Messaging
    sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message) return;
        
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.showToast('Not connected. Please wait...', 'warning');
            return;
        }

        // Remove welcome screen
        this.elements.welcomeScreen?.remove();

        // Add user message
        this.addMessage(message, 'user', null, true);

        // Send to server
        this.ws.send(JSON.stringify({ 
            message,
            conversation_id: this.currentConversationId
        }));

        // Clear input
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';
        this.elements.sendBtn.disabled = true;
    }

    addMessage(content, type, timestamp, animate = true) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        if (!animate) messageEl.style.animation = 'none';

        const time = timestamp ? new Date(timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        }) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const avatar = type === 'user' ? '👤' : '🧠';
        const author = type === 'user' ? 'You' : 'TWIZZY';
        
        const formattedContent = type === 'error' 
            ? `<span style="color: var(--error)">${this.escapeHtml(content)}</span>`
            : this.formatMessage(content);
        
        messageEl.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content-wrapper">
                <div class="message-header">
                    <span class="message-author">${author}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-content">${formattedContent}</div>
            </div>
        `;

        this.elements.messages.appendChild(messageEl);
        this.scrollToBottom();
    }

    formatMessage(content) {
        let formatted = this.escapeHtml(content);
        
        // Code blocks
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Bold
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Italic
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Links
        formatted = formatted.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" style="color: var(--accent); text-decoration: underline;">$1</a>'
        );
        
        // Newlines
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

        this.elements.messages.appendChild(messageEl);
        this.scrollToBottom();
    }

    hideThinking() {
        const thinkingEl = document.getElementById('thinkingMessage');
        if (thinkingEl) thinkingEl.remove();
    }

    scrollToBottom() {
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    }

    showImprovement(data) {
        this.addMessage(
            `🔧 Self-improvement applied: ${data.improvement}\nFiles changed: ${data.files_changed?.join(', ') || 'Unknown'}`,
            'assistant'
        );
        this.showToast('Self-improvement applied!', 'success');
    }

    showReloadNotice(message) {
        this.addMessage(`⚡ ${message}`, 'assistant');
        this.showToast('System updated', 'info');
    }

    saveToMemory() {
        // Debounced save
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => this.loadConversations(), 1000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TwizzyApp();
});
