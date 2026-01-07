from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from app.paths import get_data_dir


# =============================================================================
# BUNDLED OAUTH CREDENTIALS
# =============================================================================
# These are the default OAuth credentials bundled with the app.
# Users can click "Login with Twitch/YouTube" without any setup.
#
# To configure: Replace these with your own OAuth app credentials before
# building the executable. Leave empty to require users to provide their own.
# =============================================================================

BUNDLED_TWITCH_CLIENT_ID = ""
BUNDLED_TWITCH_CLIENT_SECRET = ""

BUNDLED_YOUTUBE_CLIENT_ID = ""
BUNDLED_YOUTUBE_CLIENT_SECRET = ""

# =============================================================================


@dataclass
class OAuthConfig:
    """OAuth configuration for a platform."""
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""

    # Placeholder values that indicate unconfigured credentials
    _PLACEHOLDER_VALUES = frozenset({
        "",
        "YOUR_TWITCH_CLIENT_ID",
        "YOUR_TWITCH_CLIENT_SECRET",
        "YOUR_YOUTUBE_CLIENT_ID",
        "YOUR_YOUTUBE_CLIENT_SECRET",
    })

    def is_configured(self) -> bool:
        """Check if OAuth is properly configured (not placeholder values)."""
        return (
            bool(self.client_id and self.client_secret and self.redirect_uri)
            and self.client_id not in self._PLACEHOLDER_VALUES
            and self.client_secret not in self._PLACEHOLDER_VALUES
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AppConfig:
    """Application configuration including OAuth credentials."""
    twitch_oauth: OAuthConfig
    youtube_oauth: OAuthConfig
    server_host: str = "127.0.0.1"
    server_port: int = 8765

    def to_dict(self) -> dict:
        return {
            "twitch_oauth": self.twitch_oauth.to_dict(),
            "youtube_oauth": self.youtube_oauth.to_dict(),
            "server_host": self.server_host,
            "server_port": self.server_port,
        }


def get_config_file() -> Path:
    """Get path to configuration file."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "config.json"


def _get_effective_credential(user_value: str, bundled_value: str) -> str:
    """Return user value if set, otherwise fall back to bundled value."""
    if user_value and user_value not in OAuthConfig._PLACEHOLDER_VALUES:
        return user_value
    return bundled_value


def load_config() -> AppConfig:
    """Load configuration from file, with bundled credentials as fallback.
    
    Priority: User config file > Bundled credentials > Empty
    """
    config_file = get_config_file()

    # Start with bundled defaults
    twitch_client_id = BUNDLED_TWITCH_CLIENT_ID
    twitch_client_secret = BUNDLED_TWITCH_CLIENT_SECRET
    youtube_client_id = BUNDLED_YOUTUBE_CLIENT_ID
    youtube_client_secret = BUNDLED_YOUTUBE_CLIENT_SECRET
    server_host = "127.0.0.1"
    server_port = 8765

    # Override with user config if it exists
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                data = json.load(f)

            twitch_data = data.get("twitch_oauth", {})
            youtube_data = data.get("youtube_oauth", {})

            # User values override bundled values (if user has set them)
            twitch_client_id = _get_effective_credential(
                twitch_data.get("client_id", ""), BUNDLED_TWITCH_CLIENT_ID
            )
            twitch_client_secret = _get_effective_credential(
                twitch_data.get("client_secret", ""), BUNDLED_TWITCH_CLIENT_SECRET
            )
            youtube_client_id = _get_effective_credential(
                youtube_data.get("client_id", ""), BUNDLED_YOUTUBE_CLIENT_ID
            )
            youtube_client_secret = _get_effective_credential(
                youtube_data.get("client_secret", ""), BUNDLED_YOUTUBE_CLIENT_SECRET
            )
            server_host = data.get("server_host", "127.0.0.1")
            server_port = data.get("server_port", 8765)

        except Exception as e:
            print(f"Error loading config: {e}")

    return AppConfig(
        twitch_oauth=OAuthConfig(
            client_id=twitch_client_id,
            client_secret=twitch_client_secret,
            redirect_uri="http://localhost:8765/auth/twitch/callback",
        ),
        youtube_oauth=OAuthConfig(
            client_id=youtube_client_id,
            client_secret=youtube_client_secret,
            redirect_uri="http://localhost:8765/auth/youtube/callback",
        ),
        server_host=server_host,
        server_port=server_port,
    )


def save_config(config: AppConfig) -> None:
    """Save configuration to file."""
    config_file = get_config_file()

    try:
        with open(config_file, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def create_example_config() -> None:
    """Create an example configuration file if none exists."""
    config_file = get_config_file()

    if config_file.exists():
        return

    example_config = AppConfig(
        twitch_oauth=OAuthConfig(
            client_id="YOUR_TWITCH_CLIENT_ID",
            client_secret="YOUR_TWITCH_CLIENT_SECRET",
            redirect_uri="http://localhost:8765/auth/twitch/callback",
        ),
        youtube_oauth=OAuthConfig(
            client_id="YOUR_YOUTUBE_CLIENT_ID",
            client_secret="YOUR_YOUTUBE_CLIENT_SECRET",
            redirect_uri="http://localhost:8765/auth/youtube/callback",
        ),
    )

    save_config(example_config)
    print(f"Created example config at: {config_file}")
    print("Please edit this file with your OAuth credentials.")


def open_config_directory() -> bool:
    """Open the config directory in the system file explorer."""
    import platform
    import subprocess

    config_dir = get_data_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", str(config_dir)], check=False)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(config_dir)], check=False)
        else:  # Linux
            subprocess.run(["xdg-open", str(config_dir)], check=False)
        return True
    except Exception as e:
        print(f"Error opening config directory: {e}")
        return False


# =============================================================================
# CHAT SETTINGS PERSISTENCE
# =============================================================================

def get_chat_settings_file() -> Path:
    """Get path to chat settings file."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "chat_settings.json"


def load_chat_settings() -> dict:
    """Load chat settings from file."""
    settings_file = get_chat_settings_file()
    
    if not settings_file.exists():
        return {}
    
    try:
        with open(settings_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading chat settings: {e}")
        return {}


def save_chat_settings(settings: dict) -> None:
    """Save chat settings to file."""
    settings_file = get_chat_settings_file()
    
    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving chat settings: {e}")
