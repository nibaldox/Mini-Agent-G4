"""Mini Agent G4 - Agno-based agent with tools and team support"""

__version__ = "0.1.0"

# Lazy imports — don't pull in agno/pydantic until actually used.
def __getattr__(name):
    if name in ("MiniAgent", "create_agent"):
        from mini_agent.core.agent import MiniAgent, create_agent
        return {"MiniAgent": MiniAgent, "create_agent": create_agent}[name]
    if name in ("MiniTeam", "create_team"):
        from mini_agent.core.team import MiniTeam, create_team
        return {"MiniTeam": MiniTeam, "create_team": create_team}[name]
    if name in ("AgentConfig", "DEFAULT_CONFIG", "load_config"):
        from mini_agent.core.config import AgentConfig, DEFAULT_CONFIG, load_config
        return {"AgentConfig": AgentConfig, "DEFAULT_CONFIG": DEFAULT_CONFIG, "load_config": load_config}[name]
    raise AttributeError(f"module 'mini_agent' has no attribute {name!r}")

__all__ = [
    "MiniAgent", "create_agent",
    "MiniTeam", "create_team",
    "AgentConfig", "DEFAULT_CONFIG", "load_config",
]
