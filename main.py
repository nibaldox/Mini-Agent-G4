"""Main entry point for Mini Agent G4"""

from mini_agent.core.agent import create_agent


def main():
    """Run the Mini Agent."""
    agent = create_agent()
    print("Mini Agent G4 initialized!")


if __name__ == "__main__":
    main()
