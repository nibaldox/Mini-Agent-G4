"""Main entry point for Mini Agent G4"""

import os
import sys
import argparse
from pathlib import Path

from mini_agent.core.agent import create_agent, MiniAgent
from mini_agent.core.team import create_team, MiniTeam
from mini_agent.core.config import AgentConfig, DEFAULT_CONFIG, load_config

# Load .env if exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_api_key_or_none(provider: str) -> str:
    """Get API key for the given provider, or empty string if not needed."""
    if provider == "lmstudio":
        return ""  # LM Studio no requiere API key
    elif provider == "ollama":
        return ""  # Ollama no requiere API key
    elif provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY", "")
    elif provider == "openai":
        return os.environ.get("OPENAI_API_KEY", "")
    return ""


def print_features(config: AgentConfig):
    """Print enabled features."""
    features = []
    if config.enable_file_tools:
        features.append("File")
    if config.enable_search_tools:
        features.append("Search")
    if config.enable_shell_tools:
        features.append("Shell")
    if config.enable_storage:
        features.append("Storage")
    if config.enable_memory:
        features.append("Memory")
    if config.mcp_servers:
        features.append(f"MCP({len(config.mcp_servers)})")
    return ", ".join(features) if features else "None"


def run_single_agent(config: AgentConfig):
    """Run as single agent mode."""
    agent = create_agent(config)

    print("=" * 60)
    print("Mini Agent G4 - Single Agent Mode")
    print("=" * 60)
    print(f"Model Provider: {agent.config.model_provider}")
    print(f"Model ID: {agent.config.model_id}")
    print(f"Features: {print_features(agent.config)}")
    print("=" * 60)
    print()

    print("Enter your message (or 'quit' to exit):")
    print("Commands: /memories, /history, /team - switch to team mode")
    print()

    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if user_input.lower() == "/team":
                print("\n[Switching to Team Mode...]\n")
                return "team"

            if user_input.lower() == "/memories":
                print("\n--- Stored Memories ---")
                memories = agent.get_user_memories()
                if memories:
                    for m in memories:
                        print(f"  - {m}")
                else:
                    print("  No memories stored yet.")
                print()
                continue

            if user_input.lower() == "/history":
                print("\n--- Session History ---")
                history = agent.get_session_history()
                if history:
                    for h in history[:10]:
                        print(f"  - {h[:100]}...")
                else:
                    print("  No history yet.")
                print()
                continue

            if not user_input.strip():
                continue

            print()
            agent.run(user_input)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

    return "exit"


def run_team_mode(config: AgentConfig):
    """Run as team mode."""
    team = create_team(config)

    print("=" * 60)
    print("Mini Agent G4 - Team Mode")
    print("=" * 60)
    print(f"Model Provider: {config.model_provider}")
    print(f"Model ID: {config.model_id}")
    print("Team Members: Researcher, Writer, Analyst, Reviewer")
    print("=" * 60)
    print()
    print("Enter your message (or 'quit' to exit):")
    print("Commands: /single - switch to single agent mode, /complex - force team for complex tasks")
    print()

    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if user_input.lower() == "/single":
                print("\n[Switching to Single Agent Mode...]\n")
                return "single"

            use_team = user_input.lower() == "/complex"

            if not user_input.strip():
                continue

            print()
            team.run(user_input, use_team=use_team)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

    return "exit"


def main():
    """Main function to run the agent."""
    parser = argparse.ArgumentParser(description="Mini Agent G4")
    parser.add_argument("--mode", choices=["single", "team", "auto"], default="auto",
                        help="Run mode: single (one agent), team (multiple agents), auto (decides based on task)")
    args = parser.parse_args()

    # Load config
    config_path = Path("config.json")
    if config_path.exists():
        print(f"Loading configuration from {config_path}")
        config = load_config(config_path)
    else:
        print("No config.json found, using default configuration")
        config = DEFAULT_CONFIG

    # Check API key if needed
    api_key = get_api_key_or_none(config.model_provider)
    if not api_key and config.model_provider not in ["lmstudio", "ollama"]:
        print(f"Error: {config.model_provider} requires an API key.")
        print(f"Please set the appropriate environment variable:")
        if config.model_provider == "anthropic":
            print("  export ANTHROPIC_API_KEY=your_key")
        elif config.model_provider == "openai":
            print("  export OPENAI_API_KEY=your_key")
        sys.exit(1)

    mode = args.mode

    # Auto mode: start with single agent, allow switching
    if mode == "auto":
        print("\nStarting in AUTO mode (single agent with team fallback)")
        print("Use /team to explicitly use the multi-agent team\n")
        mode = "single"

    while True:
        if mode == "single":
            result = run_single_agent(config)
            if result == "exit":
                break
            elif result == "team":
                mode = "team"
        elif mode == "team":
            result = run_team_mode(config)
            if result == "exit":
                break
            elif result == "single":
                mode = "single"


if __name__ == "__main__":
    main()