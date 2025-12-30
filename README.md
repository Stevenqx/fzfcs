# Fuzzy Finder Tool

A powerful fuzzy finder tool for the command line, written in Python. It integrates `fzf`, `rg` (ripgrep), and `bat` to provide a seamless file searching and code navigation experience.

## Features

- **Find Files**: Quickly search for files in the current repository.
- **Live Grep**: Search for text within files using ripgrep with live updates.
- **Preview**: View file contents with syntax highlighting using `bat`.
- **Ignore Toggling**: Toggle between respecting `.gitignore` and searching all files.
- **VSCode Integration**: Open selected files directly in VSCode if running from its terminal.
- **Workspace Detection**: Automatically identifies the workspace root.

## Prerequisites

Ensure the following tools are installed and available in your PATH:

- [fzf](https://github.com/junegunn/fzf)
- [ripgrep (rg)](https://github.com/BurntSushi/ripgrep)
- [bat](https://github.com/sharkdp/bat)

## Usage

Run the script directly:

```bash
./fuzzy_finder.py [mode]
```

### Modes

- `files` (default): Search for files by name.
- `grep`: Search for text within files.

### Examples

Search for files:
```bash
./fuzzy_finder.py
# or
./fuzzy_finder.py files
```

Search within files:
```bash
./fuzzy_finder.py grep
```

### Key Bindings

| Mode | Key | Action |
|------|-----|--------|
| Find Files | `CTRL-I` | Include ignored files (reload) |
| Find Files | `CTRL-X` | Exclude ignored files (reload) |
| Live Grep | `CTRL-I` | Toggle ignored files |
| All | `Enter` | Open selected file |
| All | `Esc` | Cancel |

## Installation

Simply copy `fuzzy_finder.py` to a directory in your PATH.
