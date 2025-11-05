# UV Migration Guide

This document explains the migration from pip/requirements.txt to uv/pyproject.toml.

## What Changed?

### New Files

1. **[pyproject.toml](pyproject.toml)** - Modern Python project configuration
   - Replaces requirements.txt with proper dependency management
   - Includes project metadata, scripts, and optional dependencies
   - Supports multiple dependency groups (main, dev, gpu, etc.)

2. **[.python-version](.python-version)** - Python version specification
   - Tells uv which Python version to use (3.11)
   - Compatible with pyenv and other version managers

3. **[INSTALL_UV.md](INSTALL_UV.md)** - Installation guide using uv
   - Comprehensive guide for installing with uv
   - Includes GPU support, alternative backends, and troubleshooting

### Benefits of UV

- **10-100x faster** installation than pip
- **Better dependency resolution** with lockfile support
- **Built-in virtual environment management**
- **Reproducible builds** with uv.lock
- **Drop-in pip replacement** with familiar commands

## Quick Start

### For New Users

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project
cd audio_summary_app
uv sync

# Activate venv
source .venv/bin/activate

# Run the app
python main.py

# Or run without activating venv
uv run python main.py
```

### For Existing Users (Migrating from pip)

```bash
# Optional: Remove old venv
rm -rf venv/

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with uv
uv sync

# Your config.py, models, and summaries are preserved!
```

## Project Structure

```
audio_summary_app/
├── pyproject.toml          # NEW: Project configuration (replaces requirements.txt)
├── .python-version         # NEW: Python version for uv
├── uv.lock                 # NEW: Will be generated on first uv sync
├── INSTALL_UV.md           # NEW: Installation guide for uv
├── UV_MIGRATION.md         # NEW: This file
├── requirements.txt        # KEPT: For backward compatibility
├── README.md               # Existing documentation
├── ARCHITECTURE.md         # Existing architecture docs
├── DATA_FLOW.md           # Existing data flow docs
├── INSTALL.md             # Existing installation guide (pip-based)
├── main.py                # Application entry point
├── demo.py                # Demo script
├── config.py              # Configuration
├── audio_capture.py       # Audio capture
├── transcriber.py         # Speech-to-text
├── transcript_buffer.py   # Transcript storage
└── summarizer.py          # Summarization
```

## Dependency Changes

### requirements.txt → pyproject.toml

**Old (requirements.txt):**
```
sounddevice>=0.4.6
numpy>=1.24.0
faster-whisper>=0.10.0
llama-cpp-python>=0.2.0
python-dateutil>=2.8.2
```

**New (pyproject.toml):**
```toml
[project]
dependencies = [
    "sounddevice>=0.4.6",
    "numpy>=1.24.0",
    "faster-whisper>=0.10.0",
    "llama-cpp-python>=0.2.0",
    "python-dateutil>=2.8.2",
]
```

### Optional Dependencies (New!)

The pyproject.toml adds optional dependency groups:

**GPU Support:**
```bash
uv sync --extra gpu
```

**Alternative Whisper:**
```bash
uv sync --extra whisper-alternative
```

**Transformers Backend:**
```bash
uv sync --extra transformers
```

**Development Tools:**
```bash
uv sync --extra dev
```

**Everything:**
```bash
uv sync --extra all
```

## Command Comparison

| Task | pip | uv |
|------|-----|-----|
| Create venv | `python -m venv venv` | Automatic with `uv sync` |
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | `pip install pkg && pip freeze` | `uv add pkg` |
| Remove package | `pip uninstall pkg` | `uv remove pkg` |
| Update deps | `pip install -U -r requirements.txt` | `uv sync --upgrade` |
| Run script | `python main.py` | `uv run python main.py` |
| List packages | `pip list` | `uv pip list` |

## Entry Points (New!)

The pyproject.toml defines command-line entry points:

```toml
[project.scripts]
audio-summary = "main:main"
audio-summary-demo = "demo:main"
```

After installation, you can run:
```bash
audio-summary        # Runs main.py
audio-summary-demo   # Runs demo.py
```

## Lockfile (uv.lock)

After running `uv sync`, a `uv.lock` file will be created. This file:

- **Pins exact versions** of all dependencies (including transitive deps)
- **Ensures reproducibility** across different machines
- **Should be committed to git** for team projects
- **Speeds up installation** on subsequent runs

### Using the lockfile:

```bash
# Install exactly what's in the lockfile
uv sync --frozen

# Update lockfile with latest compatible versions
uv lock --upgrade
```

## Backward Compatibility

The **requirements.txt is kept** for users who prefer pip:

```bash
# Still works!
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration Changes

No changes needed! Your existing files work as-is:
- `config.py` - No changes
- `*.py` files - No changes
- `models/` directory - No changes
- `summaries/` directory - No changes

## GPU Support

The GPU installation is now easier with uv:

**Old way (pip):**
```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall
```

**New way (uv):**
```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" uv sync --reinstall-package llama-cpp-python
```

Or set it permanently:
```bash
export CMAKE_ARGS="-DLLAMA_CUBLAS=on"
uv sync --reinstall-package llama-cpp-python
```

## Development Workflow

### Adding a new dependency:

```bash
# Add to main dependencies
uv add package-name

# Add to dev dependencies
uv add --dev package-name

# Add to optional group
uv add --optional gpu package-name
```

### Running tests (when added):

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Or activate venv first
source .venv/bin/activate
pytest
```

### Code formatting:

```bash
# Install dev tools
uv sync --extra dev

# Format code
uv run black .

# Lint code
uv run ruff check .

# Type check
uv run mypy .
```

## CI/CD Integration

### GitHub Actions example:

```yaml
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest
```

## Troubleshooting

### "uv: command not found"

Install uv first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart your shell or source the profile
```

### Compilation errors during uv sync

Install build tools:
```bash
# macOS
brew install cmake

# Linux
sudo apt-get install build-essential cmake

# Windows
# Install Visual Studio Build Tools
```

### Import errors after migration

Make sure the venv is activated:
```bash
source .venv/bin/activate
```

Or use `uv run`:
```bash
uv run python main.py
```

### Different behavior than pip

Check Python version:
```bash
uv run python --version
```

Should match `.python-version` (3.11)

## Best Practices

1. **Commit uv.lock** to git for reproducible builds
2. **Use `uv sync --frozen`** in CI/CD and production
3. **Use `uv add/remove`** instead of manually editing pyproject.toml
4. **Use `uv run`** to avoid forgetting to activate venv
5. **Use optional dependencies** for platform-specific features

## Rollback (If Needed)

If you need to go back to pip:

```bash
# Deactivate and remove uv venv
deactivate
rm -rf .venv

# Create pip venv
python -m venv venv
source venv/bin/activate

# Install with pip
pip install -r requirements.txt
```

## Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [pyproject.toml Specification](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/)
- [Audio Summary App README](README.md)
- [Installation Guide (uv)](INSTALL_UV.md)

## Questions?

If you encounter issues:
1. Check [INSTALL_UV.md](INSTALL_UV.md) for detailed installation steps
2. Review [Troubleshooting](#troubleshooting) section above
3. Verify system requirements in [INSTALL.md](INSTALL.md)
4. Open an issue in the project repository
