class LiveChatWidget {
  constructor() {
    this.ws = null;
    this.messagesContainer = document.getElementById('chat-messages');
    this.maxMessages = 50;
    this.autoScroll = true;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;

    this.platformIcons = {
      twitch: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#9146FF"><path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z"/></svg>`,
      youtube: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FF0000"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
    };

    // Apply theme from URL query param
    const urlParams = new URLSearchParams(window.location.search);
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
    const fontSize = urlParams.get('fontsize') || 'medium';
    document.body.classList.add(`font-${fontSize}`);

    // Hide timestamp option
    const hideTime = urlParams.get('hidetime');
    if (hideTime === 'true' || hideTime === '1') {
      document.body.classList.add('hide-time');
    }

    this.init();
  }

  init() {
    this.showStatus('Connecting to chat...', 'connecting');
    this.connect();

    // Handle scroll to detect manual scrolling
    this.messagesContainer.addEventListener('scroll', () => {
      const container = this.messagesContainer;
      const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50;
      this.autoScroll = isAtBottom;
    });
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Chat WebSocket connected');
      this.reconnectAttempts = 0;
      this.clearStatus();
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
    };

    this.ws.onclose = () => {
      console.log('Chat WebSocket disconnected');
      this.showStatus('Disconnected. Reconnecting...', 'error');
      this.reconnect();
    };
  }

  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.showStatus('Failed to connect. Please refresh.', 'error');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect();
    }, delay);
  }

  handleMessage(data) {
    switch (data.type) {
      case 'chat_message':
        this.addChatMessage(data.data);
        break;
      case 'chat_history':
        // Initial history load (comes in oldest-to-newest order)
        if (data.data && Array.isArray(data.data)) {
          // For both directions, we add messages in order
          // The addChatMessage handles placement based on direction
          data.data.forEach(msg => this.addChatMessage(msg, false));
          
          if (this.direction === 'down') {
            this.scrollToBottom();
          }
        }
        break;
      default:
        // Ignore other message types
        break;
    }
  }

  addChatMessage(messageData, shouldAnimate = true) {
    const msgElement = this.createMessageElement(messageData);

    if (!shouldAnimate) {
      msgElement.style.animation = 'none';
    }

    if (this.direction === 'up') {
      // Direction UP: newest at bottom (anchored), older messages bubble upward
      // With flex-direction: column-reverse, prepending puts new message at visual bottom
      this.messagesContainer.insertBefore(msgElement, this.messagesContainer.firstChild);
      
      // Limit total messages (remove oldest = last child = visually at top)
      while (this.messagesContainer.children.length > this.maxMessages) {
        this.messagesContainer.removeChild(this.messagesContainer.lastChild);
      }
    } else {
      // Direction DOWN (default): newest at bottom, scroll down
      this.messagesContainer.appendChild(msgElement);

      // Limit total messages (remove oldest = first child = visually at top)
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

    // Platform icon (optional)
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
          // Simple text badge fallback
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

    // Timestamp (optional)
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

  parseMessageWithEmotes(message, emotes) {
    if (!emotes || emotes.length === 0) {
      return this.escapeHtml(message);
    }

    // Build a map of emote codes to emote data
    const emoteMap = {};
    emotes.forEach(emote => {
      emoteMap[emote.code] = emote;
    });

    // Split message into words and replace emotes
    const words = message.split(' ');
    const result = words.map(word => {
      if (emoteMap[word]) {
        const emote = emoteMap[word];
        const animatedClass = emote.is_animated ? 'animated' : '';
        return `<img class="emote ${animatedClass}" src="${emote.url}" alt="${emote.code}" title="${emote.code} (${emote.provider})">`;
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

  showStatus(message, className = '') {
    this.messagesContainer.innerHTML = `<div class="status-message ${className}">${message}</div>`;
  }

  clearStatus() {
    const statusMsg = this.messagesContainer.querySelector('.status-message');
    if (statusMsg) {
      statusMsg.remove();
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new LiveChatWidget();
});
