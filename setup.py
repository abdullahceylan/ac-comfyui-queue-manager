#!/usr/bin/env python3
"""Setup script for ComfyUI Queue Manager development environment."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"Running: {description}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"  Command: {' '.join(cmd)}")
        print(f"  Error: {e.stderr}")
        return False
    else:
        print(f"✓ {description} completed successfully")
        return True


def main() -> None:
    """Set up the development environment."""
    print("Setting up AC ComfyUI Queue Manager development environment...")

    # Change to the project directory
    project_dir = Path(__file__).parent
    print(f"Working in: {project_dir}")

    # Install development dependencies
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Installing development dependencies",
    ):
        sys.exit(1)

    # Install pre-commit hooks
    if not run_command(["pre-commit", "install"], "Installing pre-commit hooks"):
        sys.exit(1)

    # Install commit-msg hook
    if not run_command(
        ["pre-commit", "install", "--hook-type", "commit-msg"],
        "Installing commit-msg hook",
    ):
        print("Warning: commit-msg hook installation failed (this is optional)")

    # Run initial formatting
    if not run_command(["ruff", "format", "."], "Running initial code formatting"):
        print("Warning: Initial formatting failed")

    # Run initial linting
    if not run_command(["ruff", "check", "--fix", "."], "Running initial linting"):
        print("Warning: Initial linting found issues")

    print("\n🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("1. Make your changes to the code")
    print("2. Run 'make format' to format your code")
    print("3. Run 'make check' to check for issues")
    print("4. Commit your changes (pre-commit hooks will run automatically)")


if __name__ == "__main__":
    main()
