# TODO List for Fuzzy Finder Tool

## Phase 1: Basic Implementation
- [x] Create `fuzzy_finder.py` script structure.
- [x] Implement "Search Files" mode using `rg --files` and `fzf`.
- [x] Implement "Search Within Files" (Live Grep) mode using `fzf`'s `reload` feature with `rg`.
- [x] Add preview support using `bat`.
- [x] Implement file opening logic (print to stdout or open in editor).

## Phase 2: Enhanced Features
- [x] Add support for ignoring/unignoring files (toggle `--no-ignore` in `rg`).
- [x] Identify workspace root automatically.
- [x] VSCode integration (detect if running in VSCode terminal and use `code -r` or similar).
- [x] Add keyboard shortcuts for switching modes or toggling options within `fzf`.

## Phase 3: Advanced Features (Optional)
- [x] Command line argument parsing for initial mode selection.
- [x] Support for other resources (git commits, etc.).
- [x] Auto-completion support.
