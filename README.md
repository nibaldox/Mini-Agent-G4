# Mini Agent G4

Agno-based agent with file, search, shell tools, memory, storage, MCP, and Skills.

## Model Providers

- **LM Studio** (default, local) - No API key needed
- **Ollama** (local) - No API key needed
- **Anthropic** - Requires `ANTHROPIC_API_KEY`
- **OpenAI** - Requires `OPENAI_API_KEY`

## Features

| Feature | Description |
|---------|-------------|
| **FileTools** | Read, write, list, search, and modify files |
| **WebSearchTools** | Search the web for information |
| **ShellTools** | Execute shell commands (bash, cmd) |
| **Storage** | Persistent conversation history (SQLite) |
| **Memory** | Remember user preferences across sessions |
| **MCP** | Connect to MCP servers for extended tools |
| **Skills** | Load custom skill definitions from directory |

## Setup

```bash
# Install dependencies
uv sync

# Run with LM Studio (default)
uv run python -m mini_agent

# Run with Anthropic
export ANTHROPIC_API_KEY=your_key
uv run python -m mini_agent
```

## Configuration

```python
from mini_agent.core.agent import create_agent
from mini_agent.core.config import AgentConfig

# Default config (LM Studio, all features enabled)
agent = create_agent()

# Custom configuration
config = AgentConfig(
    model_provider="lmstudio",
    model_id="google/gemma-4-26b-a4b",
    db_file="my_agent.db",
    enable_memory=True,
    enable_storage=True,
    enable_file_tools=True,
    enable_search_tools=True,
    enable_shell_tools=True,
)
agent = create_agent(config)

# With MCP servers
config = AgentConfig(
    mcp_servers=[
        {"url": "http://localhost:8000/mcp", "transport": "streamable-http"},
        {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}
    ]
)
agent = create_agent(config)

# With Skills directory
config = AgentConfig(skills_dir=Path("./skills"))
agent = create_agent(config)
```

## MCP Servers

Connect to MCP servers to extend agent capabilities:

```python
config = AgentConfig(
    mcp_servers=[
        # HTTP-based MCP server
        {"url": "http://localhost:8000/mcp", "transport": "streamable-http"},
        # SSE-based
        {"url": "http://localhost:8000/sse", "transport": "sse"},
        # Stdio-based (local command)
        {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}
    ]
)
```

## Skills

Load custom skills from a directory. Each skill is a folder containing:
- `SKILL.md` - Instructions for the agent
- `scripts/` - Optional helper scripts
- `references/` - Optional reference docs

```python
config = AgentConfig(skills_dir=Path("./my_skills"))
agent = create_agent(config)
```

## Interactive Commands

When running in interactive mode:
- `/memories` - Show stored user memories
- `/history` - Show session conversation history
- `quit` - Exit the agent

## LM Studio Setup

1. Download [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Gemma, Qwen2.5, Llama3)
3. Start the local server (click "Start Server" button)
4. Default endpoint: `http://127.0.0.1:1234/v1`

## Architecture

```
mini_agent/
├── core/
│   ├── agent.py      # Main agent implementation + model factory
│   └── config.py     # Configuration dataclass
├── tools/
│   ├── file_toolkit.py
│   ├── search_toolkit.py
│   └── shell_toolkit.py
└── __main__.py       # Entry point
```

## Database

The agent uses SQLite for:
- **Storage**: Conversation history and session state
- **Memory**: User preferences and facts

Database file: `mini_agent.db` (by default)