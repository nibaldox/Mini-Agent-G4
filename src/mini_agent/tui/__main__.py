"""TUI entry point - standalone, no agent dependencies."""

import sys
import os

# Run from src directory
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from mini_agent.tui.app import run_tui

if __name__ == "__main__":
    run_tui()