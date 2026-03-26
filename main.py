"""
Role:
- Simple local startup entrypoint for the project.

Called by:
- Developers running the project directly.

Calls:
- `config.logging`
- `app.cli`
"""

from app.cli import run_cli
from config.logging import setup_logging


def main() -> None:
    """Start the project."""
    setup_logging()
    run_cli()


if __name__ == "__main__":
    main()
