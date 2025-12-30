# Fuzzy Finder Tool

A powerful fuzzy finder tool for the command line, written in Python. It integrates `fzf`, `rg` (ripgrep), and `bat` to provide a seamless file searching and code navigation experience.

## Features

- **Find Files**: Quickly search for files in the current repository
- **Live Grep**: Search for text within files using ripgrep with live updates
- **Git Commits**: Browse and search git commit history
- **Git Status**: Browse changed files with diff preview
- **Preview**: View file contents with syntax highlighting using `bat`
- **Toggle Options**: Toggle hidden files and gitignore on/off
- **VSCode Integration**: Open selected files directly in VSCode if running from its terminal
- **Workspace Detection**: Automatically identifies the git repository root

## Prerequisites

Ensure the following tools are installed and available in your PATH:

- [fzf](https://github.com/junegunn/fzf) (0.59.0+)
- [ripgrep (rg)](https://github.com/BurntSushi/ripgrep)
- [bat](https://github.com/sharkdp/bat)

## Usage

```bash
./fuzzy_finder.py [mode]
```

### Modes

| Mode | Description |
|------|-------------|
| `files` | Search for files by name (default) |
| `grep` | Search for text within files |
| `commits` | Browse git commits |
| `status` | Browse changed files (git status) |

### Examples

```bash
./fuzzy_finder.py              # Start in files mode
./fuzzy_finder.py files        # Same as above
./fuzzy_finder.py grep         # Start in grep mode
./fuzzy_finder.py commits      # Browse git commits
./fuzzy_finder.py status       # Browse changed files
./fuzzy_finder.py --completion # Print shell completion script
```

## Key Bindings

### Navigation

| Key | Action |
|-----|--------|
| `Ctrl+U` | Scroll list up (half page) |
| `Ctrl+D` | Scroll list down (half page) |
| `Ctrl+B` | Scroll preview up (half page) |
| `Ctrl+F` | Scroll preview down (half page) |
| `Ctrl+L` | Clear query |
| `Enter` | Select item / Copy commit hash |
| `Esc` | Cancel |

### Mode Switching

| Key | Action |
|-----|--------|
| `Ctrl+J` | Switch to Files mode |
| `Ctrl+K` | Switch to Grep mode |
| `Ctrl+G` | Switch to Commits mode |
| `Ctrl+H` | Switch to Status mode |

### Toggle Options (Files/Grep modes)

| Key | Action |
|-----|--------|
| `Alt+I` | Toggle gitignore (show ignored files) |
| `Alt+U` | Toggle hidden files |
| `Ctrl+T` | Toggle between ripgrep and fzf filtering (grep mode only) |

### Prompt Indicators

The prompt shows current state:

- `Files H>` - Hidden files shown
- `Files I>` - Gitignore bypassed
- `Files HI>` - Both hidden and ignored files shown
- `rgH>` - Ripgrep mode with hidden files
- `fzf>` - Fuzzy filtering mode

## Customization

### Key Bindings

Edit the `KEYBINDINGS` dictionary at the top of the script to customize keys:

```python
KEYBINDINGS = {
    "toggle_ignore": "alt-i",
    "toggle_hidden": "alt-u",
    "switch_files": "ctrl-j",
    "switch_grep": "ctrl-k",
    # ... etc
}
```

## Installation

1. Copy `fuzzy_finder.py` to a directory in your PATH
2. Make it executable: `chmod +x fuzzy_finder.py`
3. Optionally create an alias: `alias ff='fuzzy_finder.py'`

### Shell Completion

Add completion support to your shell:

```bash
# Bash - add to ~/.bashrc
source <(fuzzy_finder.py --completion)

# Zsh - add to ~/.zshrc
eval "$(fuzzy_finder.py --completion)"
```

## License

MIT
