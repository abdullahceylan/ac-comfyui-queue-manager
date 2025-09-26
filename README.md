# AC ComfyUI Queue Manager

A comprehensive queue management system for ComfyUI workflows with persistence, control features, and a web-based interface.

## Features

- Queue workflow executions with persistence
- Pause/resume queue processing
- Archive and restore completed workflows
- Web-based management interface
- Export/import queue configurations
- Filtering and search capabilities

## Development Setup

### Prerequisites

- Python 3.8+
- ComfyUI installation

### Installation

1. Clone or copy this custom node to your ComfyUI custom_nodes directory:
   ```bash
   cd ComfyUI/custom_nodes/
   # Copy the comfyui-queue-manager directory here
   ```

2. Set up the development environment (recommended):
   ```bash
   cd comfyui-queue-manager
   python setup.py
   ```

   Or manually install dependencies:
   ```bash
   make install-dev
   make setup-hooks
   ```

### Development Commands

- **Format code**: `make format`
- **Lint code**: `make lint`
- **Run all checks**: `make check`
- **Clean cache files**: `make clean`
- **Show help**: `make help`

### Code Quality

This project uses modern Python tooling for code quality:

- **Ruff** - Fast Python linter and formatter (replaces flake8, black, isort, and more)
- **Pre-commit hooks** - Automatic code quality checks before commits
- **MyPy** - Optional static type checking

#### Ruff Configuration

The project is configured with:
- Modern Python 3.8+ syntax (using `|` for unions instead of `Union`)
- PEP 585 collection types (`list[str]` instead of `List[str]`)
- Comprehensive rule set covering code style, security, and best practices
- ComfyUI-specific exceptions (e.g., allowing uppercase method names like `INPUT_TYPES`)

#### Pre-commit Hooks

The hooks automatically:
- Format code with Ruff
- Fix common linting issues
- Check for trailing whitespace and file endings
- Validate YAML, JSON, and TOML files
- Check for merge conflicts and large files
- Run type checking with MyPy

#### Manual Commands

```bash
# Format code
make format

# Check for issues
make lint

# Run all checks
make check

# Clean cache files
make clean
```

### Project Structure

```
comfyui-queue-manager/
├── __init__.py              # Node registration
├── queue_manager_node.py    # Main ComfyUI custom node
├── models.py               # Data models and enums
├── interfaces.py           # Abstract interfaces
├── web/                    # Frontend assets
│   ├── index.html
│   ├── queue_manager.js
│   └── styles.css
├── pyproject.toml          # Project configuration
├── .pre-commit-config.yaml # Pre-commit hooks
├── Makefile               # Development commands
└── README.md              # This file
```

## Usage

After installation, the Queue Manager node will be available in ComfyUI under the "Queue Management" category. The web interface can be accessed through ComfyUI's web server.

## Contributing

1. Make sure pre-commit hooks are installed: `make setup-hooks`
2. Format your code: `make format`
3. Run checks: `make check`
4. Commit your changes (pre-commit hooks will run automatically)

## License

MIT License