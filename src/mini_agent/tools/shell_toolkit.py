"""Custom shell toolkit for Mini Agent G4"""

from typing import List

from agno.tools.shell import ShellTools as AgnoShellTools


class ShellToolkit(AgnoShellTools):
    """Extended shell toolkit for MiniAgent."""

    def run_shell_command(self, args: List[str], tail: int = 100) -> str:
        """Runs a shell command and returns the output or error.

        Args:
            args: The command to run as a list of strings.
            tail: The number of lines to return from the output.

        Returns:
            The output of the command.
        """
        return super().run_shell_command(args=args, tail=tail)