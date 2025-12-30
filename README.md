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
- `commits`: Search git commits.
- `status`: Search changed files (git status).

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

Search commits:
```bash
./fuzzy_finder.py commits
```

Search changed files:
```bash
./fuzzy_finder.py status
```

### Key Bindings

| Mode | Key | Action |
|------|-----|--------|
| Find Files | `CTRL-I` | Toggle Ignore (reload) |
| Find Files | `CTRL-Y` | Toggle Hidden (reload) |
| Find Files | `CTRL-G` | Switch to Live Grep |
| Find Files | `CTRL-H` | Switch to Commits |
| Find Files | `CTRL-S` | Switch to Status |
| Live Grep | `CTRL-I` | Toggle Ignore |
| Live Grep | `CTRL-Y` | Toggle Hidden |
| Live Grep | `CTRL-F` | Switch to Find Files |
| Live Grep | `CTRL-H` | Switch to Commits |
| Live Grep | `CTRL-S` | Switch to Status |
| Commits | `CTRL-F` | Switch to Find Files |
| Commits | `CTRL-G` | Switch to Live Grep |
| Commits | `CTRL-S` | Switch to Status |
| Commits | `Enter` | Copy commit hash to clipboard |
| Status | `CTRL-F` | Switch to Find Files |
| Status | `CTRL-G` | Switch to Live Grep |
| Status | `CTRL-H` | Switch to Commits |
| All | `Enter` | Open selected file (Files/Grep/Status) |
| All | `Esc` | Cancel |

## Installation

Simply copy `fuzzy_finder.py` to a directory in your PATH.

### Auto-completion

To enable bash completion, add the following to your `.bashrc`:

```bash
source <(/path/to/fuzzy_finder.py --completion)
```
