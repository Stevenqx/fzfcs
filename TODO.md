# TODO List for Fuzzy Finder Tool

## Phase 1: Basic Implementation
- [ ] Create `fuzzy_finder.py` script structure.
- [ ] Implement "Search Files" mode using `rg --files` and `fzf`.
- [ ] Implement "Search Within Files" (Live Grep) mode using `fzf`'s `reload` feature with `rg`.
- [ ] Add preview support using `bat`.
- [ ] Implement file opening logic (print to stdout or open in editor).

## Phase 2: Enhanced Features
- [ ] Add support for ignoring/unignoring files (toggle `--no-ignore` in `rg`).
- [ ] Identify workspace root automatically.
- [ ] VSCode integration (detect if running in VSCode terminal and use `code -r` or similar).
- [ ] Add keyboard shortcuts for switching modes or toggling options within `fzf`.

## Phase 3: Advanced Features (Optional)
- [ ] Command line argument parsing for initial mode selection.
- [ ] Support for other resources (git commits, etc.).
- [ ] Auto-completion support.
