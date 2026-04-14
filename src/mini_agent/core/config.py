"""Configuración del Mini Agent G4"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal, List, Union, Dict, Any


@dataclass
class AgentConfig:
    """Configuración del agente."""

    name: str = "MiniAgentG4"
    model_provider: Literal["anthropic", "lmstudio", "ollama", "openai"] = "lmstudio"
    model_id: str = "qwen3.5-35b-a3b-claude-opus-reasoning-distilled-4.6@q8_0"
    base_dir: Path = Path.cwd()

    # Tools
    enable_file_tools: bool = True
    enable_search_tools: bool = True
    enable_shell_tools: bool = True
    enable_geometry_tools: bool = True
    enable_scheduling_tools: bool = True
    max_file_length: int = 10000000
    max_file_lines: int = 100000

    # MCP Servers
    mcp_servers: List[Dict[str, Any]] = field(default_factory=list)
    # Example:
    # [{"url": "http://localhost:8000/mcp", "transport": "streamable-http"}]
    # [{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}]

    # Skills
    skills_dir: Optional[Path] = Path("my_skills")
    # Path to skills directory (defaults to ./my_skills in project root)

    # Storage
    enable_storage: bool = True
    db_file: str = "mini_agent.db"

    # Memory
    enable_memory: bool = True

    # Session
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    # Behavior
    streaming: bool = True
    markdown: bool = True
    debug_mode: bool = False
    max_tool_result_tokens: int = 2000
    model_context_window: int = 32000
    add_history_to_context: bool = True
    num_history_runs: int = 5
    add_datetime_to_context: bool = True

    # Guardrails
    enable_pii_detection: bool = True
    enable_prompt_injection_detection: bool = True

    # Discord notifications
    enable_discord_tools: bool = False
    discord_bot_token: Optional[str] = None
    discord_default_alert_channel: Optional[str] = None

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "AgentConfig":
        """Load configuration from a JSON file, similar to Claude's config."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create AgentConfig from a dictionary."""
        # Handle Path conversion for skills_dir and base_dir
        if "skills_dir" in data and data["skills_dir"]:
            data["skills_dir"] = Path(data["skills_dir"])
        if "base_dir" in data and data["base_dir"]:
            data["base_dir"] = Path(data["base_dir"])

        # Extract known fields, ignore extras
        known_fields = {
            "name", "model_provider", "model_id", "base_dir",
            "enable_file_tools", "enable_search_tools", "enable_shell_tools",
            "max_file_length", "max_file_lines", "mcp_servers", "skills_dir",
            "enable_storage", "db_file", "enable_memory", "session_id",
            "user_id", "streaming", "markdown", "add_history_to_context",
            "num_history_runs", "add_datetime_to_context",
            "enable_pii_detection", "enable_prompt_injection_detection",
            "enable_geometry_tools", "enable_scheduling_tools",
            "enable_discord_tools", "discord_bot_token", "discord_default_alert_channel",
            "debug_mode", "max_tool_result_tokens", "model_context_window"
        }
        filtered_data = {k: v for k, v in data.items() if k in known_fields}

        return cls(**filtered_data)

    def to_json(self, path: Union[str, Path]) -> None:
        """Save configuration to a JSON file."""
        config_path = Path(path)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, default=str)


DEFAULT_CONFIG = AgentConfig()


def load_config(config_path: Optional[Union[str, Path]] = None) -> AgentConfig:
    """Load configuration from JSON file or return default.

    Args:
        config_path: Path to config.json. If None, looks for config.json in cwd.
    """
    if config_path is None:
        config_path = Path("config.json")
    else:
        config_path = Path(config_path)

    if config_path.exists():
        return AgentConfig.from_json(config_path)

    return DEFAULT_CONFIG