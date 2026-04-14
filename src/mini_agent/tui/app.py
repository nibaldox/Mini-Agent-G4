"""MiniAgent G4 — Modern minimal TUI"""

from __future__ import annotations

import io
import logging
import re
import sys
from datetime import datetime
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button, ContentSwitcher, Footer, Input, Label,
    ListItem, ListView, Markdown, RichLog, Static,
)


# ─── Stdout → RichLog bridge ─────────────────────────────────────────────────

class _RichLogStream(io.TextIOBase):
    """Redirect write() calls into a RichLog widget."""
    def __init__(self, rich_log: RichLog, original: io.TextIOBase) -> None:
        self._log      = rich_log
        self._original = original

    def write(self, text: str) -> int:
        if text.strip():
            try:
                self._log.write(text.rstrip())
            except Exception:
                self._original.write(text)
        return len(text)

    def flush(self) -> None:
        pass


class _RichLogHandler(logging.Handler):
    """Send Python log records to a RichLog widget."""
    def __init__(self, rich_log: RichLog) -> None:
        super().__init__()
        self._log = rich_log

    def emit(self, record: logging.LogRecord) -> None:
        try:
            lvl   = record.levelname
            color = {"DEBUG": "dim", "INFO": "green", "WARNING": "yellow", "ERROR": "red"}.get(lvl, "white")
            self._log.write(f"[{color}][{lvl}][/{color}] {record.name}: {self.format(record)}")
        except Exception:
            pass


def _split_thinking(content: str) -> tuple[str, str]:
    """Split <think>...</think> blocks from main response.

    Returns (thinking, response). Handles partial (in-progress) think blocks.
    """
    # Complete blocks
    thinking_parts = re.findall(r"<think>(.*?)</think>", content, re.DOTALL)
    # Remove complete blocks from content
    remainder = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)

    # Partial block still open (streaming in progress)
    if "<think>" in remainder:
        before, in_progress = remainder.split("<think>", 1)
        thinking_parts.append(in_progress)
        remainder = before

    thinking = "\n\n".join(thinking_parts).strip()
    response  = remainder.strip()
    return thinking, response


# ─── Palette ────────────────────────────────────────────────────────────────
# GitHub Dark-inspired

PALETTE = dict(
    bg      = "#0a0a0a",
    card    = "#111418",
    border  = "#1e2328",
    dim     = "#161a1f",
    text    = "#cdd9e5",
    muted   = "#4a5360",
    accent  = "#58a6ff",
    success = "#3fb950",
    warning = "#d29922",
    error   = "#f85149",
)

NAV_ITEMS = [
    ("chat",  "◉  Chat"),
    ("tools", "⬡  Tools"),
    ("debug", "⬖  Debug"),
    ("about", "◈  About"),
]


# ─── Sidebar nav item ────────────────────────────────────────────────────────

class NavItem(ListItem):
    """One sidebar navigation entry."""

    def __init__(self, view_id: str, label: str) -> None:
        super().__init__()
        self.view_id = view_id
        self._label = label

    def compose(self) -> ComposeResult:
        yield Label(self._label)


# ─── Message bubble ──────────────────────────────────────────────────────────

class MessageBubble(Vertical):
    """A chat message with thinking, tool calls, and response sections."""

    DEFAULT_CSS = ""

    def __init__(self, who: str, text: str, ts: str) -> None:
        super().__init__()
        self.who   = who
        self._text = text
        self._ts   = ts
        self.add_class(who)

    def compose(self) -> ComposeResult:
        name = "You" if self.who == "user" else "MiniAgent"
        with Horizontal(classes="bubble-header-row"):
            yield Label(f"{name}  {self._ts}", classes="bubble-header")
            yield Button("⎘", classes="copy-btn", id=f"copy-{id(self)}")
        # thinking + tools mounted dynamically — nothing pre-rendered here
        yield Markdown(self._text, classes="bubble-body")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if "copy-btn" in event.button.classes:
            event.stop()
            self.app.copy_to_clipboard(self._text)
            self.app.notify("Copied", severity="information", timeout=2)

    def _ensure_thinking(self) -> tuple:
        """Mount thinking section once, return (label, md)."""
        if self.query(".thinking-label"):
            return (
                self.query_one(".thinking-label", Label),
                self.query_one(".thinking-body",  Markdown),
            )
        body = self.query_one(".bubble-body", Markdown)
        lbl  = Label("◌ thinking", classes="thinking-label")
        md   = Markdown("",        classes="thinking-body")
        # mount as siblings of body, ordered before it
        self.mount(lbl, before=body)
        self.mount(md,  before=body)
        return lbl, md

    def _ensure_tools(self) -> Vertical:
        """Mount tools container once, return it."""
        existing = list(self.query(".tools-section"))
        if existing:
            return existing[0]
        body    = self.query_one(".bubble-body", Markdown)
        section = Vertical(classes="tools-section")
        self.mount(section, before=body)
        return section

    def add_tool_call(self, name: str, preview: str = "") -> None:
        section    = self._ensure_tools()
        label_text = f"⚙ {name}" + (f"  {preview}" if preview else "")
        section.mount(Label(label_text, classes="tool-call"))
        if isinstance(self.parent, VerticalScroll):
            self.parent.scroll_end(duration=0.05)

    def mark_tool_done(self, name: str) -> None:
        try:
            for lbl in reversed(list(self.query(".tool-call"))):
                txt = str(lbl.renderable)
                if name in txt and txt.startswith("⚙"):
                    lbl.update(txt.replace("⚙", "✓", 1))
                    break
        except Exception:
            pass

    def update_content(self, text: str, thinking: str = "") -> None:
        self._text = text
        try:
            self.query_one(".bubble-body", Markdown).update(text or "_…_")
        except Exception:
            pass

        if thinking:
            try:
                lbl, md = self._ensure_thinking()
                md.update(thinking)
                lbl.update("✓ thinking" if text else "◌ thinking")
            except Exception:
                pass

        try:
            if isinstance(self.parent, VerticalScroll):
                self.parent.scroll_end(duration=0.05)
        except Exception:
            pass


# ─── Chat view ───────────────────────────────────────────────────────────────

class ChatView(Vertical):
    """Scrollable message list."""

    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="messages")
        with Horizontal(id="input-bar"):
            yield Input(placeholder="Message MiniAgent…", id="msg-input")
            yield Button("Send", id="send-btn", variant="primary")

    def add_message(self, who: str, text: str) -> None:
        ts = datetime.now().strftime("%H:%M")
        scroll = self.query_one("#messages", VerticalScroll)
        bubble = MessageBubble(who, text, ts)
        scroll.mount(bubble)
        scroll.scroll_end(duration=0.2)

    def add_streaming_bubble(self, who: str) -> "MessageBubble":
        """Mount an empty bubble for streaming; caller fills it via update_content."""
        ts = datetime.now().strftime("%H:%M")
        scroll = self.query_one("#messages", VerticalScroll)
        bubble = MessageBubble(who, "_…_", ts)
        scroll.mount(bubble)
        scroll.scroll_end(duration=0.1)
        return bubble


# ─── Tools view ──────────────────────────────────────────────────────────────

class ToolsView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Markdown(
            "# Tools\n\n"
            "| Tool | Status |\n"
            "|------|--------|\n"
            "| Geometry | 🟢 Active |\n"
            "| Scheduling | 🟢 Active |\n"
            "| File R/W | 🟢 Active |\n"
            "| Web Search | 🟢 Active |\n"
            "| Shell | 🟢 Active |\n"
            "| Discord | 🔴 Disabled |\n"
            "| PII Guard | 🟢 Active |\n"
            "| Prompt Guard | 🟢 Active |\n"
        )


# ─── About view ──────────────────────────────────────────────────────────────

class AboutView(VerticalScroll):
    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model

    def compose(self) -> ComposeResult:
        yield Markdown(
            f"# MiniAgent G4\n\n"
            "A minimal, composable AI agent built with **Agno**.\n\n"
            "---\n\n"
            "## Runtime\n\n"
            f"| Key | Value |\n"
            f"|-----|-------|\n"
            f"| Model | `{self._model}` |\n"
            "| Provider | LM Studio |\n"
            "| Memory | SQLite |\n"
            "| Storage | Enabled |\n\n"
            "## Keybindings\n\n"
            "| Key | Action |\n"
            "|-----|--------|\n"
            "| `Enter` | Send message |\n"
            "| `Ctrl+L` | Clear chat |\n"
            "| `Ctrl+C` | Quit |\n"
        )


# ─── Debug view ──────────────────────────────────────────────────────────────

class DebugView(Vertical):
    """Live debug log — captures stdout + logging + raw chunks."""
    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield Static("Debug log", classes="debug-title")
        yield RichLog(id="debug-log", highlight=True, markup=True, wrap=True)


# ─── App ─────────────────────────────────────────────────────────────────────

class MiniAgentTUI(App):
    """MiniAgent G4 — clean minimal TUI."""

    CSS = f"""
    $bg:      {PALETTE['bg']};
    $card:    {PALETTE['card']};
    $border:  {PALETTE['border']};
    $dim:     {PALETTE['dim']};
    $text:    {PALETTE['text']};
    $muted:   {PALETTE['muted']};
    $accent:  {PALETTE['accent']};
    $success: {PALETTE['success']};

    /* ── Canvas ── */
    Screen {{ background: $bg; layout: vertical; }}

    /* Make every container match the canvas */
    Horizontal  {{ background: $bg; }}
    Vertical    {{ background: $bg; }}
    VerticalScroll  {{ background: $bg; }}
    ContentSwitcher {{ background: $bg; }}
    ChatView        {{ background: $bg; layout: vertical; height: 1fr; }}
    ToolsView       {{ background: $bg; }}
    AboutView       {{ background: $bg; }}
    DebugView       {{ background: $bg; }}

    /* ── Top bar: floating text only ── */
    #topbar {{ height: 3; padding: 0 2; align: left middle; }}
    .brand  {{ color: $accent; text-style: bold; }}
    .model  {{ color: $muted;  margin-left: 2; }}
    .status {{ color: $success; dock: right; margin-right: 1; }}

    /* ── Body ── */
    #body {{ height: 1fr; }}

    /* ── Sidebar ── */
    #sidebar     {{ width: 16; padding: 1 0; border-right: solid $dim; }}
    ListView     {{ background: $bg; border: none; height: 1fr; }}
    ListItem     {{ background: $bg; height: 3; padding: 0 2; }}
    ListItem:hover {{ background: $bg; }}
    ListItem.--highlight {{ background: $bg; border-left: solid $accent; }}
    ListItem Label             {{ color: $muted; }}
    ListItem:hover Label       {{ color: $text; }}
    ListItem.--highlight Label {{ color: $accent; }}

    /* ── Content ── */
    ContentSwitcher {{ height: 1fr; width: 1fr; }}
    ContentSwitcher > * {{ height: 1fr; }}

    /* ── Messages area ── */
    #messages {{ height: 1fr; padding: 1 2; background: $bg; }}

    /* ── Messages: no card, only a bottom separator line ── */
    MessageBubble {{
        margin-bottom: 1;
        padding: 0 2 1 2;
        background: $bg;
        border-bottom: solid $border;
        height: auto;
    }}
    MessageBubble.user {{
        background: $bg;
        border-bottom: solid $accent;
    }}
    .bubble-header-row {{
        layout: horizontal;
        background: $bg;
        height: auto;
        margin-bottom: 1;
    }}
    .bubble-header {{
        color: $muted;
        text-style: bold;
        width: 1fr;
    }}
    MessageBubble.user .bubble-header {{ color: $accent; }}
    .copy-btn {{
        background: $bg;
        color: $muted;
        border: none;
        min-width: 3;
        height: 1;
        padding: 0 1;
    }}
    .copy-btn:hover {{ color: $accent; background: $bg; }}
    .bubble-body {{ color: $text; }}

    /* ── Input bar ── */
    #input-bar {{
        height: auto;
        min-height: 5;
        padding: 1 2;
        background: $bg;
        border-top: solid $dim;
        align: left middle;
    }}
    #msg-input {{
        width: 1fr;
        background: $bg;
        border: round $border;
        color: $text;
        padding: 0 1;
        height: 3;
    }}
    #msg-input:focus {{ border: round $accent; }}
    #send-btn {{
        width: 8;
        height: 3;
        margin-left: 1;
        background: $bg;
        color: $accent;
        border: round $border;
    }}
    #send-btn:hover {{ border: round $accent; color: $text; }}

    /* ── Thinking block (mounted dynamically) ── */
    .thinking-label {{
        color: $muted;
        text-style: italic;
        margin-top: 1;
    }}
    .thinking-body {{
        color: $muted;
        background: $bg;
        padding: 0 0 0 2;
        border-left: solid $muted;
        margin-bottom: 1;
        height: auto;
    }}

    /* ── Tool calls (mounted dynamically) ── */
    .tools-section {{
        background: $bg;
        height: auto;
        margin-bottom: 1;
    }}
    .tool-call {{
        color: $warning;
        text-style: italic;
        padding: 0 0 0 2;
    }}

    /* ── Debug panel ── */
    DebugView     {{ layout: vertical; height: 1fr; padding: 1 2; }}
    .debug-title  {{ color: $muted; text-style: bold; margin-bottom: 1; }}
    #debug-log    {{ height: 1fr; background: $bg; border: solid $border; padding: 0 1; }}

    /* ── Tools / About ── */
    ToolsView {{ padding: 2 4; }}
    AboutView {{ padding: 2 4; }}
    Markdown        {{ background: $bg; color: $text; }}
    .bubble-body    {{ background: $bg; padding: 0; margin: 0; }}

    /* ── Status bar ── */
    #statusbar {{ height: 1; padding: 0 2; background: $bg; }}
    .info        {{ color: $muted; width: 1fr; }}
    #stat-tokens {{ color: $muted; margin-right: 2; }}
    #stat-ctx    {{ color: $muted; }}

    Footer {{ display: none; }}
    """

    BINDINGS = [
        Binding("ctrl+c", "quit",      "Quit",  show=False),
        Binding("ctrl+l", "clear_chat","Clear", show=False),
        Binding("ctrl+y", "copy_last", "Copy",  show=False),
    ]

    def __init__(self, config=None) -> None:
        super().__init__()
        self.config = config
        self.model = config.model_id if config else "qwen3.5-35b"
        self._active_view = "chat"
        self._agent       = None    # initialized lazily in on_mount worker
        self._tokens_in   = 0
        self._tokens_out  = 0
        self._ctx_turns   = 0
        self._dbg_log     = None

    # ── Layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # Top bar
        with Horizontal(id="topbar"):
            yield Static("◆ MiniAgent G4", classes="brand")
            yield Static(self.model, classes="model")
            yield Static("● Ready", classes="status")

        # Body: sidebar + content
        with Horizontal(id="body"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield ListView(
                    *[NavItem(vid, label) for vid, label in NAV_ITEMS],
                    id="nav",
                )

            # Main content panels
            with ContentSwitcher(initial="chat"):
                yield ChatView(id="chat")
                yield ToolsView(id="tools")
                yield DebugView(id="debug")
                yield AboutView(self.model, id="about")

        # Status bar
        with Horizontal(id="statusbar"):
            yield Static("Ctrl+C quit  ·  Ctrl+L clear  ·  Ctrl+Y copy last", classes="info")
            yield Static("", id="stat-tokens")
            yield Static("", id="stat-ctx")

    def on_mount(self) -> None:
        self.title = "MiniAgent G4"
        self.query_one("#msg-input").focus()
        self.query_one("#nav", ListView).index = 0
        self._setup_debug()
        self.run_worker(self._init_agent(), exclusive=False)

    def _setup_debug(self) -> None:
        """Wire stdout + Python logging into the debug RichLog."""
        rlog = self.query_one("#debug-log", RichLog)
        # Redirect stdout
        sys.stdout = _RichLogStream(rlog, sys.__stdout__)
        # Capture Python logging (agno uses this)
        handler = _RichLogHandler(rlog)
        handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        logging.getLogger("agno").setLevel(logging.DEBUG)
        self._dbg_log = rlog

    def _dbg(self, text: str) -> None:
        """Write a line to the debug log (no-op if not yet ready)."""
        if self._dbg_log is None:
            return
        try:
            self._dbg_log.write(text)
        except Exception:
            pass

    async def _init_agent(self) -> None:
        """Initialize the real agent in the background."""
        status = self.query_one(".status", Static)
        status.update("◌ Loading…")
        try:
            from mini_agent.core.agent import MiniAgent
            self._agent = MiniAgent(config=self.config)
            status.update("● Ready")
        except Exception as exc:
            status.update(f"⚠ {exc.__class__.__name__}")
            chat = self.query_one(ChatView)
            chat.add_message("agent", f"**Agent init failed:** `{exc}`\n\nCheck that LM Studio is running.")

    # ── Navigation ───────────────────────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, NavItem):
            self.query_one(ContentSwitcher).current = item.view_id
            self._active_view = item.view_id
            if item.view_id == "chat":
                self.query_one("#msg-input").focus()

    # ── Messaging ────────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._send_message()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            self._send_message()

    def _send_message(self) -> None:
        inp = self.query_one("#msg-input", Input)
        text = inp.value.strip()
        if not text:
            return
        inp.value = ""

        # Switch to chat if needed
        self.query_one(ContentSwitcher).current = "chat"
        self.query_one("#nav", ListView).index = 0

        chat = self.query_one(ChatView)
        chat.add_message("user", text)

        # Update status
        self.query_one(".status", Static).update("◌ Thinking…")

        self.run_worker(self._agent_response(text), exclusive=True)

    def _update_stats(self, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self._tokens_in  += tokens_in
        self._tokens_out += tokens_out
        self._ctx_turns  += 1
        tok_w = self.query_one("#stat-tokens", Static)
        ctx_w = self.query_one("#stat-ctx",    Static)
        tok_w.update(f"↑{self._tokens_in:,} ↓{self._tokens_out:,} tok")
        total  = self._tokens_in + self._tokens_out
        max_ctx = self.config.model_context_window if self.config else 32000
        pct    = min(100, round(total / max_ctx * 100)) if max_ctx else 0
        ctx_w.update(f"ctx {pct}%")

    async def _agent_response(self, text: str) -> None:
        status = self.query_one(".status", Static)
        chat   = self.query_one(ChatView)

        if self._agent is None:
            chat.add_message("agent", "_Agent still loading — try again in a moment._")
            status.update("● Ready")
            return

        bubble      = chat.add_streaming_bubble("agent")
        accumulated = ""
        tokens_in   = 0
        tokens_out  = 0

        try:
            response = await self._agent.agent.arun(
                text,
                stream=True,
                user_id=self.config.user_id if self.config else "tui-user",
            )
            thinking_acc = ""

            async for chunk in response:
                event_type = getattr(chunk, "event", None)

                # ── Debug: log raw chunk ───────────────────────────────────
                chunk_attrs = {
                    k: getattr(chunk, k, None)
                    for k in ("event", "content", "thinking", "reasoning_content",
                              "tool_calls", "metrics", "role", "model", "content_type")
                    if getattr(chunk, k, None) is not None
                }
                if chunk_attrs:
                    self._dbg(
                        f"[dim]── chunk ──[/dim] "
                        + "  ".join(
                            f"[cyan]{k}[/cyan]=[yellow]{repr(v)[:120]}[/yellow]"
                            for k, v in chunk_attrs.items()
                        )
                    )

                # ── Tool events ────────────────────────────────────────────
                if event_type in ("ToolCallStarted", "tool_call_started"):
                    for tc in (getattr(chunk, "tool_calls", None) or []):
                        tname   = getattr(tc, "name", None) or getattr(tc, "function", {}).get("name", "?")
                        args    = getattr(tc, "arguments", None) or {}
                        preview = ", ".join(f"{k}={str(v)[:20]}" for k, v in (args.items() if isinstance(args, dict) else []))
                        self._dbg(f"[yellow]⚙ TOOL_START[/yellow] {tname}({preview})")
                        bubble.add_tool_call(tname, preview)
                        status.update(f"⚙ {tname}…")

                elif event_type in ("ToolCallCompleted", "tool_call_completed"):
                    for tc in (getattr(chunk, "tool_calls", None) or []):
                        tname = getattr(tc, "name", None) or getattr(tc, "function", {}).get("name", "?")
                        result = getattr(tc, "result", None)
                        self._dbg(f"[green]✓ TOOL_DONE[/green] {tname} → {repr(result)[:200]}")
                        bubble.mark_tool_done(tname)

                # ── Collect content & thinking from every chunk ────────────
                raw_thinking = (
                    getattr(chunk, "thinking", None)
                    or getattr(chunk, "reasoning_content", None)
                    or ""
                )
                if raw_thinking:
                    thinking_acc += raw_thinking

                piece = getattr(chunk, "content", None) or ""
                if piece:
                    accumulated += piece

                # ── Update bubble on new content ───────────────────────────
                if piece or raw_thinking:
                    tag_thinking, reply = _split_thinking(accumulated)
                    combined = (thinking_acc + "\n\n" + tag_thinking).strip()
                    display  = reply if combined else accumulated
                    bubble.update_content(display, combined)

                # ── Metrics ───────────────────────────────────────────────
                metrics = getattr(chunk, "metrics", None)
                if metrics:
                    tin  = getattr(metrics, "input_tokens",  0) or 0
                    tout = getattr(metrics, "output_tokens", 0) or 0
                    tokens_in  = max(tokens_in,  tin)
                    tokens_out = max(tokens_out, tout)
                    self._dbg(f"[blue]◈ METRICS[/blue] in={tin} out={tout}")

            # ── Final clean render after stream ends ───────────────────────
            tag_thinking, reply = _split_thinking(accumulated)
            combined = (thinking_acc + "\n\n" + tag_thinking).strip()
            display  = reply if combined else accumulated
            bubble.update_content(display or "_No response received._", combined)

        except Exception:
            try:
                resp    = await self._agent.run_async(text)
                content = getattr(resp, "content", None) or str(resp)
                thinking, reply = _split_thinking(content or "")
                bubble.update_content(reply or "_No response._", thinking)
                metrics = getattr(resp, "metrics", None)
                if metrics:
                    tokens_in  = getattr(metrics, "input_tokens",  0) or 0
                    tokens_out = getattr(metrics, "output_tokens", 0) or 0
            except Exception as exc2:
                bubble.update_content(f"**Error:** `{exc2}`")

        self._update_stats(tokens_in, tokens_out)
        status.update("● Ready")

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        self.query_one("#messages", VerticalScroll).remove_children()
        self._tokens_in = self._tokens_out = self._ctx_turns = 0
        self.query_one("#stat-tokens", Static).update("")
        self.query_one("#stat-ctx",    Static).update("")

    def action_copy_last(self) -> None:
        """Copy the last agent message to clipboard."""
        bubbles = [b for b in self.query(MessageBubble) if b.who == "agent"]
        if not bubbles:
            self.notify("No agent message to copy", severity="warning", timeout=2)
            return
        text = bubbles[-1]._text
        if text:
            self.copy_to_clipboard(text)
            self.notify("Copied", severity="information", timeout=2)


# ─── Entry point ─────────────────────────────────────────────────────────────

def run_tui(config=None) -> None:
    MiniAgentTUI(config).run()


if __name__ == "__main__":
    run_tui()
