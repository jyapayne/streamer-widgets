from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Platform(str, Enum):
    TWITCH = "twitch"
    YOUTUBE = "youtube"


class UserRole(str, Enum):
    BROADCASTER = "broadcaster"
    MODERATOR = "moderator"
    VIP = "vip"
    SUBSCRIBER = "subscriber"
    VIEWER = "viewer"


@dataclass
class Emote:
    """Represents an emote that can be rendered in chat."""
    code: str
    url: str
    provider: str  # "twitch", "ffz", "bttv", "7tv", "youtube"
    is_animated: bool = False
    scale: int = 1


@dataclass
class ChatBadge:
    """User badge (mod, subscriber, etc.)."""
    name: str
    icon_url: Optional[str] = None


@dataclass
class ChatUser:
    """Represents a chat user."""
    id: str
    username: str
    display_name: str
    platform: Platform
    color: Optional[str] = None
    roles: List[UserRole] = field(default_factory=list)
    badges: List[ChatBadge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "platform": self.platform.value,
            "color": self.color,
            "roles": [r.value for r in self.roles],
            "badges": [{"name": b.name, "icon_url": b.icon_url} for b in self.badges],
        }


@dataclass
class ChatMessage:
    """Represents a single chat message from either platform."""
    id: str
    platform: Platform
    user: ChatUser
    message: str
    timestamp: datetime
    emotes: List[Emote] = field(default_factory=list)
    is_deleted: bool = False
    is_action: bool = False  # /me messages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "user": self.user.to_dict(),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "emotes": [
                {
                    "code": e.code,
                    "url": e.url,
                    "provider": e.provider,
                    "is_animated": e.is_animated,
                    "scale": e.scale,
                }
                for e in self.emotes
            ],
            "is_deleted": self.is_deleted,
            "is_action": self.is_action,
        }


@dataclass
class AuthTokens:
    """OAuth tokens for a platform."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope,
        }


@dataclass
class ChatConfig:
    """Configuration for the chat widget."""
    # Authentication
    twitch_enabled: bool = False
    youtube_enabled: bool = False

    # Display settings
    max_messages: int = 50
    show_timestamps: bool = True
    show_badges: bool = True
    show_platform_icons: bool = True
    unified_view: bool = True  # True = mixed, False = separate columns

    # Emote providers
    enable_ffz: bool = True
    enable_bttv: bool = True
    enable_7tv: bool = True

    # Filtering
    filter_by_roles: List[UserRole] = field(default_factory=list)
    blocked_keywords: List[str] = field(default_factory=list)
    min_message_length: int = 0

    # Twitch specific
    twitch_channel: str = ""

    # YouTube specific
    youtube_video_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
