class ViewerCountWidget {
  constructor() {
    this.countElement = document.getElementById('count-value');
    this.viewerCount = document.getElementById('viewer-count');
    this.statusMessage = document.getElementById('status-message');
    this.iconElement = document.getElementById('count-icon');
    this.labelElement = document.getElementById('count-label');
    
    this.currentCount = 0;
    this.refreshInterval = 30000; // 30 seconds
    this.intervalId = null;

    // Parse URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    
    // Theme: dark (default), light, minimal
    const theme = urlParams.get('theme') || 'dark';
    document.body.classList.add(`theme-${theme}`);
    
    // Font size: small, medium (default), large, xlarge
    const fontSize = urlParams.get('fontsize') || 'medium';
    document.body.classList.add(`font-${fontSize}`);
    
    // Hide label option
    const hideLabel = urlParams.get('hidelabel');
    if (hideLabel === 'true' || hideLabel === '1') {
      document.body.classList.add('hide-label');
    }
    
    // Show live dot
    const showDot = urlParams.get('livedot');
    if (showDot === 'true' || showDot === '1') {
      document.body.classList.add('show-live-dot');
    }
    
    // Custom refresh interval (in seconds)
    const interval = parseInt(urlParams.get('interval'));
    if (interval && interval >= 10) {
      this.refreshInterval = interval * 1000;
    }

    this.init();
  }

  init() {
    this.fetchViewerCount();
    this.intervalId = setInterval(() => this.fetchViewerCount(), this.refreshInterval);
  }

  async fetchViewerCount() {
    try {
      const response = await fetch('/api/viewercount');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      this.updateDisplay(data);
    } catch (error) {
      console.error('Failed to fetch viewer count:', error);
      this.showError('Failed to load');
    }
  }

  updateDisplay(data) {
    const { twitch, youtube, total } = data;
    
    // Determine which platform(s) have data
    const hasTwitch = twitch !== null;
    const hasYoutube = youtube !== null;
    
    // Set platform class for icon color based on what's configured/available
    document.body.classList.remove('platform-twitch', 'platform-youtube', 'platform-combined');
    if (hasTwitch && hasYoutube) {
      document.body.classList.add('platform-combined');
      this.setIcon('eye');
    } else if (hasTwitch) {
      document.body.classList.add('platform-twitch');
      this.setIcon('twitch');
    } else if (hasYoutube) {
      document.body.classList.add('platform-youtube');
      this.setIcon('youtube');
    } else {
      // No platform configured, use generic eye icon
      document.body.classList.add('platform-combined');
      this.setIcon('eye');
    }
    
    // Update count with animation
    const newCount = total || 0;
    if (newCount !== this.currentCount) {
      this.viewerCount.classList.add('updating');
      setTimeout(() => this.viewerCount.classList.remove('updating'), 300);
    }
    
    this.currentCount = newCount;
    this.countElement.textContent = this.formatNumber(newCount);
    
    // Update label
    this.labelElement.textContent = newCount === 1 ? 'viewer' : 'viewers';
    
    // Show the widget, hide status
    this.viewerCount.classList.remove('hidden');
    this.statusMessage.classList.add('hidden');
  }

  formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 10000) {
      return (num / 1000).toFixed(1) + 'K';
    } else if (num >= 1000) {
      return num.toLocaleString();
    }
    return num.toString();
  }

  setIcon(type) {
    const icons = {
      twitch: `<svg viewBox="0 0 24 24"><path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z"/></svg>`,
      youtube: `<svg viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
      eye: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>`
    };
    this.iconElement.innerHTML = icons[type] || icons.eye;
  }

  showError(message) {
    this.viewerCount.classList.add('hidden');
    this.statusMessage.textContent = message;
    this.statusMessage.classList.remove('hidden');
    this.statusMessage.classList.add('error');
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  new ViewerCountWidget();
});

