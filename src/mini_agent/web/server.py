"""Web UI dashboard for MiniAgent G4 — FastAPI + vanilla HTML/JS."""

import asyncio
import threading
from pathlib import Path
from typing import Optional, Callable

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False


# ─── HTML Dashboard (embedded, no separate files needed) ───────────────────────

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MiniAgent G4 — Dashboard</title>
<style>
  :root {
    --bg: #0a0a0a; --card: #111418; --border: #1e2328;
    --text: #cdd9e5; --muted: #4a5360; --accent: #58a6ff;
    --success: #3fb950; --warning: #d29922; --error: #f85149;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: monospace; height: 100vh; display: flex; flex-direction: column; }

  /* ── Header ── */
  #header { background: var(--card); border-bottom: 1px solid var(--border); padding: 12px 20px; display: flex; align-items: center; gap: 16px; }
  #header h1 { color: var(--accent); font-size: 1.1rem; }
  #header h1 span { color: var(--muted); font-size: 0.8rem; margin-left: 8px; }
  .status-badge { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 4px 10px; font-size: 0.75rem; }
  .status-badge.online { border-color: var(--success); color: var(--success); }
  .status-badge.offline { border-color: var(--error); color: var(--error); }

  /* ── Main layout ── */
  #main { display: flex; flex: 1; overflow: hidden; }

  /* ── Sidebar ── */
  #sidebar { width: 220px; background: var(--card); border-right: 1px solid var(--border); padding: 16px 0; overflow-y: auto; }
  .nav-section { margin-bottom: 20px; }
  .nav-label { font-size: 0.65rem; text-transform: uppercase; color: var(--muted); padding: 0 16px; margin-bottom: 6px; letter-spacing: 1px; }
  .nav-item { padding: 8px 16px; cursor: pointer; font-size: 0.85rem; color: var(--muted); display: flex; align-items: center; gap: 8px; transition: color 0.15s; }
  .nav-item:hover { color: var(--text); }
  .nav-item.active { color: var(--accent); border-left: 2px solid var(--accent); }
  .nav-item .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); }
  .nav-item.active .dot { background: var(--accent); }

  /* ── Content ── */
  #content { flex: 1; overflow-y: auto; padding: 20px; }

  /* ── Chat ── */
  #chat-view { display: flex; flex-direction: column; height: 100%; }
  #messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 80%; padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; line-height: 1.5; }
  .msg.user { align-self: flex-end; background: var(--accent); color: #000; }
  .msg.agent { align-self: flex-start; background: var(--card); border: 1px solid var(--border); white-space: pre-wrap; }
  .msg .ts { font-size: 0.65rem; color: var(--muted); margin-top: 4px; }
  #input-bar { display: flex; gap: 8px; margin-top: 12px; }
  #msg-input { flex: 1; background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 0.9rem; outline: none; }
  #msg-input:focus { border-color: var(--accent); }
  #send-btn { background: var(--accent); color: #000; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-family: monospace; font-weight: bold; }
  #send-btn:hover { opacity: 0.85; }

  /* ── Skills grid ── */
  #skills-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .skill-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; transition: border-color 0.2s; }
  .skill-card:hover { border-color: var(--accent); }
  .skill-name { color: var(--accent); font-size: 0.9rem; font-weight: bold; margin-bottom: 6px; }
  .skill-desc { font-size: 0.8rem; color: var(--muted); line-height: 1.4; margin-bottom: 8px; }
  .skill-meta { font-size: 0.7rem; color: var(--muted); display: flex; gap: 10px; }
  .skill-tag { background: var(--bg); padding: 2px 6px; border-radius: 3px; }

  /* ── Memory ── */
  .memory-item { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 8px; }
  .memory-user { color: var(--accent); font-size: 0.8rem; margin-bottom: 4px; }
  .memory-content { font-size: 0.85rem; color: var(--text); }
  .memory-time { font-size: 0.7rem; color: var(--muted); margin-top: 4px; }

  /* ── Stats ── */
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
  .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  .stat-value { font-size: 1.8rem; color: var(--accent); font-weight: bold; }
  .stat-label { font-size: 0.75rem; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

  /* ── Sections ── */
  .section { display: none; }
  .section.active { display: block; }
  h2 { font-size: 1.1rem; color: var(--text); margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
</style>
</head>
<body>

<div id="header">
  <h1>◆ MiniAgent G4 <span>Dashboard</span></h1>
  <div id="agent-status" class="status-badge offline">● Offline</div>
</div>

<div id="main">
  <!-- Sidebar -->
  <div id="sidebar">
    <div class="nav-section">
      <div class="nav-label">Agent</div>
      <div class="nav-item active" data-view="chat"><span class="dot"></span> Chat</div>
      <div class="nav-item" data-view="memory"><span class="dot"></span> Memory</div>
      <div class="nav-item" data-view="skills"><span class="dot"></span> Skills</div>
    </div>
    <div class="nav-section">
      <div class="nav-label">System</div>
      <div class="nav-item" data-view="stats"><span class="dot"></span> Statistics</div>
      <div class="nav-item" data-view="config"><span class="dot"></span> Configuration</div>
      <div class="nav-item" data-view="channels"><span class="dot"></span> Channels</div>
    </div>
  </div>

  <!-- Content -->
  <div id="content">

    <!-- Chat -->
    <div id="chat" class="section active">
      <h2>Chat</h2>
      <div id="chat-view">
        <div id="messages"></div>
        <div id="input-bar">
          <input id="msg-input" placeholder="Message MiniAgent..." autocomplete="off">
          <button id="send-btn">Send</button>
        </div>
      </div>
    </div>

    <!-- Skills -->
    <div id="skills" class="section">
      <h2>Skills Registry</h2>
      <div id="skills-search" style="margin-bottom:16px;">
        <input id="skill-q" placeholder="Search skills..." style="background:var(--card);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:6px;width:300px;font-family:monospace;font-size:0.85rem;">
      </div>
      <div id="skills-grid"></div>
    </div>

    <!-- Memory -->
    <div id="memory" class="section">
      <h2>User Memories</h2>
      <div id="memory-list"></div>
    </div>

    <!-- Stats -->
    <div id="stats" class="section">
      <h2>Statistics</h2>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-value" id="stat-turns">—</div><div class="stat-label">Total Turns</div></div>
        <div class="stat-card"><div class="stat-value" id="stat-tokens-in">—</div><div class="stat-label">Tokens In</div></div>
        <div class="stat-card"><div class="stat-value" id="stat-tokens-out">—</div><div class="stat-label">Tokens Out</div></div>
        <div class="stat-card"><div class="stat-value" id="stat-skills">—</div><div class="stat-label">Skills</div></div>
        <div class="stat-card"><div class="stat-value" id="stat-memories">—</div><div class="stat-label">Memories</div></div>
        <div class="stat-card"><div class="stat-value" id="stat-ctx">—</div><div class="stat-label">Context %</div></div>
      </div>
    </div>

    <!-- Config -->
    <div id="config" class="section">
      <h2>Configuration</h2>
      <pre id="config-json" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px;font-size:0.8rem;overflow:auto;max-height:60vh;color:var(--text);"></pre>
    </div>

    <!-- Channels -->
    <div id="channels" class="section">
      <h2>Messaging Channels</h2>
      <div id="channels-list"></div>
    </div>

  </div>
</div>

<script>
  const API = window.location.protocol === 'https:' ? 'wss://' + window.location.host : 'ws://' + window.location.host;
  let ws = null;
  let agentReady = false;

  // ── WebSocket ──
  function connect() {
    ws = new WebSocket(API + '/ws');
    ws.onopen = () => {
      setStatus(true);
      requestStats();
    };
    ws.onclose = () => { setStatus(false); setTimeout(connect, 3000); };
    ws.onerror = () => ws.close();
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'chat') addMessage('agent', msg.text);
      if (msg.type === 'stats') updateStats(msg);
      if (msg.type === 'skills') renderSkills(msg.skills);
      if (msg.type === 'memory') renderMemory(msg.memories);
      if (msg.type === 'config') document.getElementById('config-json').textContent = JSON.stringify(msg.config, null, 2);
      if (msg.type === 'channels') renderChannels(msg.channels);
    };
  }
  connect();

  function setStatus(online) {
    const el = document.getElementById('agent-status');
    if (online) { el.textContent = '● Online'; el.className = 'status-badge online'; agentReady = true; }
    else { el.textContent = '● Offline'; el.className = 'status-badge offline'; agentReady = false; }
  }

  // ── Chat ──
  function addMessage(who, text) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'msg ' + who;
    const time = new Date().toLocaleTimeString();
    div.innerHTML = `<div class="text">${escapeHtml(text)}</div><div class="ts">${time}</div>`;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function sendMessage() {
    const input = document.getElementById('msg-input');
    const text = input.value.trim();
    if (!text || !agentReady) return;
    input.value = '';
    addMessage('user', text);
    ws && ws.send(JSON.stringify({ type: 'chat', text }));
  }

  document.getElementById('send-btn').onclick = sendMessage;
  document.getElementById('msg-input').onkeydown = (e) => { if (e.key === 'Enter') sendMessage(); };

  // ── Navigation ──
  document.querySelectorAll('.nav-item').forEach(item => {
    item.onclick = () => {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      item.classList.add('active');
      const view = item.dataset.view;
      document.getElementById(view).classList.add('active');
      if (view === 'stats') requestStats();
      if (view === 'skills') ws && ws.send(JSON.stringify({ type: 'list_skills' }));
      if (view === 'memory') ws && ws.send(JSON.stringify({ type: 'list_memory' }));
      if (view === 'config') ws && ws.send(JSON.stringify({ type: 'get_config' }));
      if (view === 'channels') ws && ws.send(JSON.stringify({ type: 'get_channels' }));
    };
  });

  // ── Skills search ──
  document.getElementById('skill-q').oninput = (e) => {
    ws && ws.send(JSON.stringify({ type: 'search_skills', query: e.target.value }));
  };

  function renderSkills(skills) {
    const grid = document.getElementById('skills-grid');
    if (!skills || !skills.length) { grid.innerHTML = '<p style="color:var(--muted)">No skills found.</p>'; return; }
    grid.innerHTML = skills.map(s => `
      <div class="skill-card">
        <div class="skill-name">${escapeHtml(s.name)}</div>
        <div class="skill-desc">${escapeHtml(s.description || '')}</div>
        <div class="skill-meta">
          <span class="skill-tag">${escapeHtml(s.category || 'general')}</span>
          ${(s.tags || []).map(t => `<span class="skill-tag">${escapeHtml(t)}</span>`).join('')}
        </div>
      </div>`).join('');
  }

  function renderMemory(memories) {
    const list = document.getElementById('memory-list');
    if (!memories || !memories.length) { list.innerHTML = '<p style="color:var(--muted)">No memories stored.</p>'; return; }
    list.innerHTML = memories.map(m => `
      <div class="memory-item">
        <div class="memory-user">${escapeHtml(m.user_id || 'user')}</div>
        <div class="memory-content">${escapeHtml(m.content || '')}</div>
        ${m.created_at ? `<div class="memory-time">${new Date(m.created_at).toLocaleString()}</div>` : ''}
      </div>`).join('');
  }

  function renderChannels(channels) {
    const list = document.getElementById('channels-list');
    if (!channels || !channels.length) { list.innerHTML = '<p style="color:var(--muted)">No channels configured.</p>'; return; }
    list.innerHTML = channels.map(c => `
      <div class="memory-item">
        <div class="memory-user" style="text-transform:uppercase">${escapeHtml(c.name)}</div>
        <div class="memory-content">${c.enabled ? '🟢 Enabled' : '🔴 Disabled'}</div>
      </div>`).join('');
  }

  function updateStats(stats) {
    document.getElementById('stat-turns').textContent = stats.turns || 0;
    document.getElementById('stat-tokens-in').textContent = formatNum(stats.tokens_in || 0);
    document.getElementById('stat-tokens-out').textContent = formatNum(stats.tokens_out || 0);
    document.getElementById('stat-skills').textContent = stats.skills || 0;
    document.getElementById('stat-memories').textContent = stats.memories || 0;
    document.getElementById('stat-ctx').textContent = (stats.ctx_pct || 0) + '%';
  }

  function requestStats() { ws && ws.send(JSON.stringify({ type: 'get_stats' })); }

  function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  function formatNum(n) { return n >= 1000 ? (n/1000).toFixed(1) + 'k' : String(n); }

  // Refresh stats every 10s
  setInterval(requestStats, 10000);
</script>
</body>
</html>
"""


# ─── FastAPI app ──────────────────────────────────────────────────────────────

def create_app(agent_fn: Optional[Callable] = None, config=None):
    """Create the FastAPI app, optionally wired to an agent."""
    app = FastAPI(title="MiniAgent G4 Dashboard")

    _agent_fn = agent_fn
    _config = config
    _connections: list[WebSocket] = []

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML

    @app.get("/api/status")
    async def status():
        return {"online": _agent_fn is not None, "version": "0.1.0"}

    @app.get("/api/stats")
    async def stats():
        if _agent_fn:
            agent = _agent_fn()
            return {
                "turns": getattr(agent, "_ctx_turns", 0),
                "tokens_in": getattr(agent, "_tokens_in", 0),
                "tokens_out": getattr(agent, "_tokens_out", 0),
                "ctx_pct": 0,
                "skills": 0,
                "memories": 0,
            }
        return {"turns": 0, "tokens_in": 0, "tokens_out": 0, "ctx_pct": 0, "skills": 0, "memories": 0}

    @app.get("/api/skills")
    async def list_skills():
        from mini_agent.skills.registry import SkillsRegistry
        reg = SkillsRegistry()
        reg.index()
        return {"skills": [s.__dict__ for s in reg.all()]}

    @app.get("/api/config")
    async def get_config():
        if _config:
            import json
            return json.loads(json.dumps(_config.__dict__, default=str))
        return {}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        _connections.append(ws)
        try:
            while True:
                data = await ws.receive_json()
                msg_type = data.get("type")

                if msg_type == "chat":
                    text = data.get("text", "")
                    if _agent_fn:
                        agent = _agent_fn()
                        # Run synchronously in a thread pool
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(None, lambda: agent.run(text))
                        await ws.send_json({"type": "chat", "text": str(response) if response else "Done."})

                elif msg_type == "get_stats":
                    stats = await stats()
                    await ws.send_json({"type": "stats", **stats})

                elif msg_type == "list_skills":
                    skills_data = await list_skills()
                    await ws.send_json({"type": "skills", "skills": skills_data.get("skills", [])})

                elif msg_type == "search_skills":
                    from mini_agent.skills.registry import SkillsRegistry
                    reg = SkillsRegistry()
                    reg.index()
                    results = reg.search(data.get("query", ""), limit=20)
                    await ws.send_json({"type": "skills", "skills": [s.__dict__ for s in results]})

                elif msg_type == "list_memory":
                    await ws.send_json({"type": "memory", "memories": []})

                elif msg_type == "get_config":
                    cfg = await get_config()
                    await ws.send_json({"type": "config", "config": cfg})

                elif msg_type == "get_channels":
                    await ws.send_json({"type": "channels", "channels": [
                        {"name": "telegram", "enabled": False},
                        {"name": "slack", "enabled": False},
                        {"name": "discord", "enabled": True},
                    ]})

        except WebSocketDisconnect:
            pass
        finally:
            _connections.remove(ws)

    return app


def run(host: str = "0.0.0.0", port: int = 8451, agent_fn: Optional[Callable] = None, config=None):
    """Run the web dashboard server."""
    if not UVICORN_AVAILABLE:
        print("Error: uvicorn not installed. Run: uv add uvicorn")
        return

    app = create_app(agent_fn=agent_fn, config=config)
    import uvicorn
    print(f"MiniAgent G4 Dashboard → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
