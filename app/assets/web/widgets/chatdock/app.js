class ChatDockWidget {
  constructor() {
    this.ws = null;
    this.messagesContainer = document.getElementById('chat-messages');
    this.messageInput = document.getElementById('message-input');
    this.sendButton = document.getElementById('send-button');
    this.charCount = document.getElementById('char-count');
    this.statusDot = document.querySelector('.status-dot');
    this.statusText = document.querySelector('.status-text');
    this.maxMessages = 100;
    this.autoScroll = true;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;

    // Current platform filter (all, twitch, youtube)
    this.currentFilter = 'all';
    // Platform to send messages to (twitch or youtube)
    this.sendPlatform = 'twitch';

    this.platformIcons = {
      twitch: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#9146FF"><path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z"/></svg>`,
      youtube: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FF0000"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
    };

    // Apply settings from URL query params
    const urlParams = new URLSearchParams(window.location.search);
    
    // Theme: dark (default), light
    const theme = urlParams.get('theme');
    if (theme === 'light') {
      document.body.classList.add('theme-light');
    } else {
      document.body.classList.add('theme-dark');
    }

    // Direction: 'down' = newest at bottom (default), 'up' = newest at top
    this.direction = urlParams.get('direction') || 'down';
    if (this.direction === 'up') {
      document.body.classList.add('direction-up');
    }

    // Font size: small, medium (default), large, xlarge
    this.fontSize = urlParams.get('fontsize') || 'medium';
    document.body.classList.add(`font-${this.fontSize}`);

    // Emote resolution based on font size
    this.emoteScale = (this.fontSize === 'medium' || this.fontSize === 'large' || this.fontSize === 'xlarge') ? 2 : 1;

    // Hide timestamp option
    const hideTime = urlParams.get('hidetime');
    if (hideTime === 'true' || hideTime === '1') {
      document.body.classList.add('hide-time');
    }

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.connect();
    this.updateSendPlatformIndicator();
    this.checkAuthStatus();

    // Handle scroll to detect manual scrolling
    this.messagesContainer.addEventListener('scroll', () => {
      const container = this.messagesContainer;
      const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50;
      this.autoScroll = isAtBottom;
    });
  }

  setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.platform));
    });

    // Message input
    this.messageInput.addEventListener('input', () => {
      this.charCount.textContent = this.messageInput.value.length;
    });

    this.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Send button
    this.sendButton.addEventListener('click', () => this.sendMessage());

    // Platform indicator click to switch send platform
    document.getElementById('send-platform-indicator').addEventListener('click', () => {
      this.toggleSendPlatform();
    });

    // Reconnect button
    document.getElementById('reconnect-btn').addEventListener('click', () => {
      this.reconnectChat();
    });
  }

  switchTab(platform) {
    this.currentFilter = platform;
    
    // Update tab UI
    document.querySelectorAll('.tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.platform === platform);
    });

    // Filter messages
    this.filterMessages();

    // Update send target based on selected tab
    this.sendPlatform = platform; // Can be 'all', 'twitch', or 'youtube'
    this.updateSendPlatformIndicator();
  }

  filterMessages() {
    const messages = this.messagesContainer.querySelectorAll('.chat-message');
    messages.forEach(msg => {
      if (this.currentFilter === 'all') {
        msg.style.display = '';
      } else {
        const msgPlatform = msg.classList.contains('twitch') ? 'twitch' : 'youtube';
        msg.style.display = msgPlatform === this.currentFilter ? '' : 'none';
      }
    });
  }

  toggleSendPlatform() {
    // Cycle through: all -> twitch -> youtube -> all
    if (this.sendPlatform === 'all') {
      this.sendPlatform = 'twitch';
    } else if (this.sendPlatform === 'twitch') {
      this.sendPlatform = 'youtube';
    } else {
      this.sendPlatform = 'all';
    }
    this.updateSendPlatformIndicator();
  }

  updateSendPlatformIndicator() {
    const iconEl = document.getElementById('send-platform-icon');
    const nameEl = document.getElementById('send-platform-name');
    const indicator = document.getElementById('send-platform-indicator');
    
    if (this.sendPlatform === 'all') {
      // Show both icons for "all"
      iconEl.innerHTML = `
        <span class="dual-icons">
          ${this.platformIcons.twitch}
          ${this.platformIcons.youtube}
        </span>
      `;
      nameEl.textContent = 'All';
      indicator.className = 'all';
    } else {
      iconEl.innerHTML = this.platformIcons[this.sendPlatform];
      nameEl.textContent = this.sendPlatform === 'twitch' ? 'Twitch' : 'YouTube';
      indicator.className = this.sendPlatform;
    }
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Chat WebSocket connected');
      this.reconnectAttempts = 0;
      this.setStatus('connected', 'Connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (err) {
        console.error('Failed to parse message:', err);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.setStatus('error', 'Connection error');
    };

    this.ws.onclose = () => {
      console.log('Chat WebSocket disconnected');
      this.setStatus('disconnected', 'Disconnected');
      this.reconnect();
    };
  }

  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus('error', 'Failed to connect');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.setStatus('connecting', 'Reconnecting...');

    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect();
    }, delay);
  }

  setStatus(state, text) {
    this.statusDot.className = 'status-dot ' + state;
    this.statusText.textContent = text;
  }

  handleMessage(data) {
    switch (data.type) {
      case 'chat_message':
        this.addChatMessage(data.data);
        break;
      case 'chat_history':
        if (data.data && Array.isArray(data.data)) {
          // For both directions, add messages in order
          data.data.forEach(msg => this.addChatMessage(msg, false));
          
          if (this.direction === 'down') {
            this.scrollToBottom();
          }
        }
        break;
      case 'send_result':
        // Handle send message result
        if (data.success) {
          this.messageInput.value = '';
          this.charCount.textContent = '0';
        } else {
          this.showSendError(data.error || 'Failed to send message');
        }
        break;
      default:
        break;
    }
  }

  addChatMessage(messageData, shouldAnimate = true) {
    const msgElement = this.createMessageElement(messageData);

    if (!shouldAnimate) {
      msgElement.style.animation = 'none';
    }

    // Apply filter
    if (this.currentFilter !== 'all') {
      const msgPlatform = messageData.platform;
      if (msgPlatform !== this.currentFilter) {
        msgElement.style.display = 'none';
      }
    }

    if (this.direction === 'up') {
      // Direction UP: newest at bottom (anchored), older messages bubble upward
      this.messagesContainer.insertBefore(msgElement, this.messagesContainer.firstChild);
      
      // Limit total messages (remove oldest = last child)
      while (this.messagesContainer.children.length > this.maxMessages) {
        this.messagesContainer.removeChild(this.messagesContainer.lastChild);
      }
    } else {
      // Direction DOWN (default): newest at bottom, scroll down
      this.messagesContainer.appendChild(msgElement);

      // Limit total messages (remove oldest = first child)
      while (this.messagesContainer.children.length > this.maxMessages) {
        this.messagesContainer.removeChild(this.messagesContainer.firstChild);
      }

      if (this.autoScroll) {
        this.scrollToBottom();
      }
    }
  }

  createMessageElement(data) {
    const msg = document.createElement('div');
    msg.className = `chat-message ${data.platform}`;
    msg.dataset.messageId = data.id;

    if (data.is_action) {
      msg.classList.add('action');
    }

    // Platform icon
    if (data.platform) {
      const iconDiv = document.createElement('div');
      iconDiv.className = 'platform-icon';
      iconDiv.innerHTML = this.platformIcons[data.platform] || '';
      msg.appendChild(iconDiv);
    }

    // Message content
    const content = document.createElement('div');
    content.className = 'message-content';

    // User info line
    const userInfo = document.createElement('div');
    userInfo.className = 'user-info';

    // Badges
    if (data.user.badges && data.user.badges.length > 0) {
      const badgesContainer = document.createElement('div');
      badgesContainer.className = 'user-badges';

      data.user.badges.forEach(badge => {
        const badgeEl = document.createElement('span');
        badgeEl.className = 'badge';
        badgeEl.title = badge.name;
        if (badge.icon_url) {
          badgeEl.innerHTML = `<img src="${badge.icon_url}" alt="${badge.name}">`;
        } else {
          badgeEl.textContent = badge.name.charAt(0).toUpperCase();
        }
        badgesContainer.appendChild(badgeEl);
      });

      userInfo.appendChild(badgesContainer);
    }

    // Username
    const username = document.createElement('span');
    username.className = 'username';
    username.textContent = data.user.display_name;
    if (data.user.color) {
      username.style.color = data.user.color;
    }
    userInfo.appendChild(username);

    // Timestamp
    const timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    timestamp.textContent = this.formatTime(data.timestamp);
    userInfo.appendChild(timestamp);

    content.appendChild(userInfo);

    // Message text with emotes
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    messageText.innerHTML = this.parseMessageWithEmotes(data.message, data.emotes);
    content.appendChild(messageText);

    msg.appendChild(content);

    return msg;
  }

  getEmoteUrl(emote) {
    if (!emote.emote_id) {
      return emote.url;
    }

    const scale = this.emoteScale;
    const provider = emote.provider;

    switch (provider) {
      case 'twitch':
        return `https://static-cdn.jtvnw.net/emoticons/v2/${emote.emote_id}/default/dark/${scale}.0`;
      case 'bttv':
        return `https://cdn.betterttv.net/emote/${emote.emote_id}/${scale}x`;
      case 'ffz':
        const ffzScale = scale === 2 ? 2 : 1;
        return emote.url.replace(/\/[124]$/, `/${ffzScale}`);
      case '7tv':
        return emote.url.replace(/\/[123]x\.webp$/, `/${scale}x.webp`);
      default:
        return emote.url;
    }
  }

  parseMessageWithEmotes(message, emotes) {
    if (!emotes || emotes.length === 0) {
      return this.escapeHtml(message);
    }

    const emoteMap = {};
    emotes.forEach(emote => {
      emoteMap[emote.code] = emote;
    });

    const words = message.split(' ');
    const result = words.map(word => {
      if (emoteMap[word]) {
        const emote = emoteMap[word];
        const animatedClass = emote.is_animated ? 'animated' : '';
        const url = this.getEmoteUrl(emote);
        return `<img class="emote ${animatedClass}" src="${url}" alt="${emote.code}" title="${emote.code} (${emote.provider})">`;
      }
      return this.escapeHtml(word);
    });

    return result.join(' ');
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  formatTime(timestamp) {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  async sendMessage() {
    const message = this.messageInput.value.trim();
    if (!message) return;

    // Disable input while sending
    this.messageInput.disabled = true;
    this.sendButton.disabled = true;

    try {
      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          platform: this.sendPlatform,
          message: message,
        }),
      });

      const result = await response.json();

      if (result.success) {
        this.messageInput.value = '';
        this.charCount.textContent = '0';
      } else {
        this.showSendError(result.error || 'Failed to send message');
      }
    } catch (error) {
      console.error('Send error:', error);
      this.showSendError('Network error');
    } finally {
      this.messageInput.disabled = false;
      this.sendButton.disabled = false;
      this.messageInput.focus();
    }
  }

  showSendError(error) {
    // Create error toast
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = error;
    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  async checkAuthStatus() {
    const statusEl = document.getElementById('auth-status-text');
    const statusContainer = document.getElementById('auth-status');
    
    try {
      const response = await fetch('/api/auth/status');
      const data = await response.json();
      
      const twitchAuth = data.twitch_authenticated;
      const youtubeAuth = data.youtube_authenticated;
      
      if (twitchAuth && youtubeAuth) {
        statusEl.textContent = 'Both authenticated';
        statusContainer.className = 'authenticated';
      } else if (twitchAuth) {
        statusEl.textContent = 'Twitch only';
        statusContainer.className = 'authenticated';
      } else if (youtubeAuth) {
        statusEl.textContent = 'YouTube only';
        statusContainer.className = 'authenticated';
      } else {
        statusEl.textContent = 'Not authenticated';
        statusContainer.className = 'not-authenticated';
      }
    } catch (error) {
      console.error('Failed to check auth status:', error);
      statusEl.textContent = 'Unknown';
      statusContainer.className = '';
    }
  }

  async reconnectChat() {
    const btn = document.getElementById('reconnect-btn');
    const statusEl = document.getElementById('auth-status-text');
    
    btn.disabled = true;
    btn.classList.add('spinning');
    statusEl.textContent = 'Reconnecting...';
    
    try {
      const response = await fetch('/api/chat/reconnect', {
        method: 'POST',
      });
      const data = await response.json();
      
      if (data.success) {
        this.showToast('Chat reconnected!', 'success');
        // Re-check auth status
        await this.checkAuthStatus();
      } else {
        this.showToast(data.error || 'Failed to reconnect', 'error');
      }
    } catch (error) {
      console.error('Reconnect error:', error);
      this.showToast('Network error', 'error');
    } finally {
      btn.disabled = false;
      btn.classList.remove('spinning');
      await this.checkAuthStatus();
    }
  }

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new ChatDockWidget();
});
