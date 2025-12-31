#!/usr/bin/env python3
"""
Fuzzy Finder Tool - A powerful fuzzy finder integrating fzf, ripgrep, and bat.

Modes:
  - files: Search files by name
  - grep: Search text within files (live grep)
  - commits: Browse git commits
  - status: Browse git changed files
"""

import subprocess
import sys
import os
import shutil
import argparse
import tempfile


class FuzzyFinder:
    """Main fuzzy finder class with multiple search modes."""

    # Keybindings - easily customizable
    KEYBINDINGS = {
        "toggle_ignore": "alt-i",
        "toggle_hidden": "alt-u",
        "switch_mode": "ctrl-space",
        "switch_last": "ctrl-y",
        "list_up": "ctrl-u",
        "list_down": "ctrl-d",
        "preview_up": "ctrl-b",
        "preview_down": "ctrl-f",
        "toggle_mode_rg_fzf": "ctrl-t",
        "clear_query": "ctrl-l",
        "history_prev": "ctrl-p",
        "history_next": "ctrl-n",
    }

    # Common fzf options
    FZF_COMMON_OPTS = [
        "--height",
        "100%",
        "--layout=reverse",
        "--border",
    ]

    # History directory
    HISTORY_DIR = os.path.expanduser("~/.local/share/fzfcs")

    def __init__(self):
        self._check_dependencies()
        self._ensure_history_dir()
        self.workspace_root = self._find_workspace_root()
        if self.workspace_root:
            os.chdir(self.workspace_root)

    def _ensure_history_dir(self):
        """Create history directory if it doesn't exist."""
        os.makedirs(self.HISTORY_DIR, exist_ok=True)

    def _get_history_file(self, mode):
        """Get history file path for a mode."""
        return os.path.join(self.HISTORY_DIR, f"{mode}_history")

    def _check_dependencies(self):
        """Check if required tools are installed."""
        required = ["fzf", "rg", "bat"]
        missing = [t for t in required if not shutil.which(t)]
        if missing:
            print(f"Error: Missing tools: {', '.join(missing)}")
            print("Install them to use this tool.")
            sys.exit(1)

    def _find_workspace_root(self):
        """Find git repository root or return current directory."""
        current = os.getcwd()
        while current != "/":
            if os.path.exists(os.path.join(current, ".git")):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    def _build_common_binds(self):
        """Build common keybinding options for fzf."""
        return [
            "--bind",
            f"{self.KEYBINDINGS['clear_query']}:clear-query",
            "--bind",
            f"{self.KEYBINDINGS['list_up']}:half-page-up",
            "--bind",
            f"{self.KEYBINDINGS['list_down']}:half-page-down",
            "--bind",
            f"{self.KEYBINDINGS['preview_up']}:preview-half-page-up",
            "--bind",
            f"{self.KEYBINDINGS['preview_down']}:preview-half-page-down",
            "--bind",
            f"{self.KEYBINDINGS['history_prev']}:prev-history",
            "--bind",
            f"{self.KEYBINDINGS['history_next']}:next-history",
        ]

    def _run_fzf(self, fzf_cmd, expect_keys):
        """Run fzf and parse output. Returns (action, data)."""
        try:
            proc = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = proc.communicate()

            if output:
                lines = output.decode("utf-8").splitlines()
                if lines:
                    key = lines[0]
                    selection = lines[1] if len(lines) > 1 else None

                    # Check for mode switch keys
                    for action, k in expect_keys.items():
                        if key == k:
                            return "switch", action

                    if selection and proc.returncode == 0:
                        return "select", selection

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")

        return "exit", None

    def _build_toggle_cmd(self, states, rg_commands):
        """Build toggle command using case statement.

        Args:
            states: List of (pattern, prompt, rg_key) tuples
            rg_commands: Dict of rg command variants
        """
        cases = " ".join(
            f"{pattern}) echo 'change-prompt({prompt})+reload({rg_commands[rg_key]})';;"
            for pattern, prompt, rg_key in states
        )
        return f"case $FZF_PROMPT in {cases} esac"

    def find_files(self):
        """Search files by name."""
        preview = "bat --style=numbers --color=always --line-range :500 {} 2>/dev/null"

        # rg command variants
        rg = {
            "base": "rg --files",
            "h": "rg --files --hidden",
            "i": "rg --files --no-ignore",
            "hi": "rg --files --hidden --no-ignore",
        }

        # Toggle hidden: cycle through states
        toggle_hidden = self._build_toggle_cmd(
            [
                ("*HI*", "Files I>", "i"),
                ("*H*", "Files >", "base"),
                ("*I*", "Files HI>", "hi"),
                ("*", "Files H>", "h"),
            ],
            rg,
        )

        # Toggle ignore: cycle through states
        toggle_ignore = self._build_toggle_cmd(
            [
                ("*HI*", "Files H>", "h"),
                ("*I*", "Files >", "base"),
                ("*H*", "Files HI>", "hi"),
                ("*", "Files I>", "i"),
            ],
            rg,
        )

        expect_keys = {
            "select": self.KEYBINDINGS["switch_mode"],
            "last": self.KEYBINDINGS["switch_last"],
        }

        header = " | ".join(
            [
                f"{self.KEYBINDINGS['toggle_ignore'].upper()}: Ignore",
                f"{self.KEYBINDINGS['toggle_hidden'].upper()}: Hidden",
                f"{self.KEYBINDINGS['clear_query'].upper()}: Clear",
                f"{self.KEYBINDINGS['switch_mode'].upper()}: Modes",
                f"{self.KEYBINDINGS['switch_last'].upper()}: Last",
            ]
        )

        fzf_cmd = [
            "fzf",
            "--preview",
            preview,
            *self.FZF_COMMON_OPTS,
            "--history",
            self._get_history_file("files"),
            "--prompt",
            "Files H>",
            "--bind",
            f"start:reload:{rg['h']}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_hidden']}:transform:{toggle_hidden}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_ignore']}:transform:{toggle_ignore}",
            *self._build_common_binds(),
            "--header",
            header,
            "--expect",
            ",".join(expect_keys.values()),
        ]

        action, data = self._run_fzf(fzf_cmd, expect_keys)
        if action == "select":
            return "open", data
        return action, data

    def live_grep(self):
        """Search text within files with live preview."""
        # Temp files for query state when switching rg/fzf modes
        rg_query = tempfile.NamedTemporaryFile(delete=False, prefix="fzf_rg_").name
        fzf_query = tempfile.NamedTemporaryFile(delete=False, prefix="fzf_fzf_").name

        try:
            rg_prefix = (
                "rg --column --line-number --no-heading --color=always --smart-case"
            )
            preview = "bat --color=always --highlight-line {2} {1} 2>/dev/null"

            # rg command variants with query placeholder
            rg = {
                "base": f"{rg_prefix} {{q}} || true",
                "h": f"{rg_prefix} --hidden {{q}} || true",
                "i": f"{rg_prefix} --no-ignore {{q}} || true",
                "hi": f"{rg_prefix} --hidden --no-ignore {{q}} || true",
            }

            # Toggle hidden
            toggle_hidden = (
                "case $FZF_PROMPT in "
                f"*HI*) echo 'change-prompt(rgI>)+reload({rg['i']})';; "
                f"*H*) echo 'change-prompt(rg>)+reload({rg['base']})';; "
                f"*I*) echo 'change-prompt(rgHI>)+reload({rg['hi']})';; "
                f"*rg*) echo 'change-prompt(rgH>)+reload({rg['h']})';; "
                "*) echo 'change-prompt(fzfH>)';; "
                "esac"
            )

            # Toggle ignore
            toggle_ignore = (
                "case $FZF_PROMPT in "
                f"*HI*) echo 'change-prompt(rgH>)+reload({rg['h']})';; "
                f"*I*) echo 'change-prompt(rg>)+reload({rg['base']})';; "
                f"*H*) echo 'change-prompt(rgHI>)+reload({rg['hi']})';; "
                f"*rg*) echo 'change-prompt(rgI>)+reload({rg['i']})';; "
                "*) echo 'change-prompt(fzfI>)';; "
                "esac"
            )

            # Switch between rg and fzf filtering
            switch_mode = (
                f"[[ $FZF_PROMPT == *rg* ]] && "
                f"echo 'unbind(change)+change-prompt(fzf>)+enable-search+transform-query:echo {{q}} > {rg_query}; cat {fzf_query}' || "
                f"echo 'rebind(change)+change-prompt(rgH>)+disable-search+transform-query:echo {{q}} > {fzf_query}; cat {rg_query}'"
            )

            expect_keys = {
                "select": self.KEYBINDINGS["switch_mode"],
                "last": self.KEYBINDINGS["switch_last"],
            }

            header = " | ".join(
                [
                    f"{self.KEYBINDINGS['toggle_mode_rg_fzf'].upper()}: rg/fzf",
                    f"{self.KEYBINDINGS['toggle_ignore'].upper()}: Ignore",
                    f"{self.KEYBINDINGS['toggle_hidden'].upper()}: Hidden",
                    f"{self.KEYBINDINGS['clear_query'].upper()}: Clear",
                    f"{self.KEYBINDINGS['switch_mode'].upper()}: Modes",
                    f"{self.KEYBINDINGS['switch_last'].upper()}: Last",
                ]
            )

            fzf_cmd = [
                "fzf",
                "--ansi",
                "--disabled",
                "--query",
                "",
                "--delimiter",
                ":",
                "--preview",
                preview,
                "--preview-window",
                "up,60%,border-bottom,+{2}+3/3,~3",
                *self.FZF_COMMON_OPTS,
                "--history",
                self._get_history_file("grep"),
                "--prompt",
                "rgH>",
                "--bind",
                f"start:reload:{rg['h']}",
                "--bind",
                f"change:reload:sleep 0.1; {rg['h']}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_hidden']}:transform:{toggle_hidden}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_ignore']}:transform:{toggle_ignore}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_mode_rg_fzf']}:transform:{switch_mode}",
                *self._build_common_binds(),
                "--header",
                header,
                "--expect",
                ",".join(expect_keys.values()),
            ]

            action, data = self._run_fzf(fzf_cmd, expect_keys)
            if action == "select" and data:
                parts = data.split(":")
                if len(parts) >= 2:
                    return "open", (parts[0], parts[1])
            return action, data

        finally:
            for f in [rg_query, fzf_query]:
                if os.path.exists(f):
                    os.remove(f)

    def git_commits(self):
        """Browse and search git commits."""
        git_cmd = "git log --oneline --color=always"
        preview = "git show {1} --color=always | bat --color=always --style=numbers 2>/dev/null"

        expect_keys = {
            "select": self.KEYBINDINGS["switch_mode"],
            "last": self.KEYBINDINGS["switch_last"],
        }

        header = " | ".join(
            [
                f"{self.KEYBINDINGS['clear_query'].upper()}: Clear",
                f"{self.KEYBINDINGS['switch_mode'].upper()}: Modes",
                f"{self.KEYBINDINGS['switch_last'].upper()}: Last",
                "Enter: Copy Hash",
            ]
        )

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--preview",
            preview,
            *self.FZF_COMMON_OPTS,
            "--history",
            self._get_history_file("commits"),
            "--prompt",
            "Commits>",
            "--bind",
            f"start:reload:{git_cmd}",
            *self._build_common_binds(),
            "--header",
            header,
            "--expect",
            ",".join(expect_keys.values()),
        ]

        action, data = self._run_fzf(fzf_cmd, expect_keys)
        if action == "select" and data:
            return "copy", data.split()[0]
        return action, data

    def git_status(self):
        """Browse git changed files."""
        git_cmd = "git status -s"
        preview = "git diff --color=always -- {2..} | bat --color=always --style=numbers 2>/dev/null"

        expect_keys = {
            "select": self.KEYBINDINGS["switch_mode"],
            "last": self.KEYBINDINGS["switch_last"],
        }

        header = " | ".join(
            [
                f"{self.KEYBINDINGS['clear_query'].upper()}: Clear",
                f"{self.KEYBINDINGS['switch_mode'].upper()}: Modes",
                f"{self.KEYBINDINGS['switch_last'].upper()}: Last",
            ]
        )

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--preview",
            preview,
            *self.FZF_COMMON_OPTS,
            "--history",
            self._get_history_file("status"),
            "--prompt",
            "Status>",
            "--bind",
            f"start:reload:{git_cmd}",
            *self._build_common_binds(),
            "--header",
            header,
            "--expect",
            ",".join(expect_keys.values()),
        ]

        action, data = self._run_fzf(fzf_cmd, expect_keys)
        if action == "select" and data:
            parts = data.strip().split()
            if len(parts) >= 2:
                return "open", parts[-1]
        return action, data

    def open_file(self, filename, line_num=None):
        """Open file in editor."""
        location = f"{filename}:{line_num}" if line_num else filename
        print(f"Opening: {location}")

        if os.environ.get("TERM_PROGRAM") == "vscode":
            subprocess.run(["code", "-r", "-g", location])
        else:
            editor = os.environ.get("EDITOR", "vim")
            cmd = [editor, f"+{line_num}", filename] if line_num else [editor, filename]
            subprocess.run(cmd)

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard."""
        try:
            if shutil.which("xclip"):
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
                )
                proc.communicate(input=text.encode())
                print(f"Copied: {text}")
            elif shutil.which("pbcopy"):
                proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                proc.communicate(input=text.encode())
                print(f"Copied: {text}")
            elif shutil.which("wl-copy"):
                proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                proc.communicate(input=text.encode())
                print(f"Copied: {text}")
            else:
                print(f"No clipboard tool found. Value: {text}")
        except Exception as e:
            print(f"Clipboard error: {e}")

    def print_completion(self):
        """Print shell completion scripts."""
        print("""
# Bash completion
_fuzzy_finder() {
    COMPREPLY=($(compgen -W "files grep commits status" -- "${COMP_WORDS[COMP_CWORD]}"))
}
complete -F _fuzzy_finder fuzzy_finder.py

# Zsh completion
_fuzzy_finder_zsh() {
    _describe 'command' '(files grep commits status)'
}
compdef _fuzzy_finder_zsh fuzzy_finder.py

# Fish completion
# complete -c fuzzy_finder.py -f -a "files grep commits status"
""")

    def select_mode(self, current_mode):
        """Show interactive mode selection screen."""
        modes = [
            ("1. Files", "files", "Search files by name"),
            ("2. Grep", "grep", "Search text within files"),
            ("3. Commits", "commits", "Browse git commits"),
            ("4. Status", "status", "Browse changed files"),
        ]

        # Build input for fzf
        items = "\n".join(f"{name}\t{desc}" for name, _, desc in modes)

        fzf_cmd = [
            "fzf",
            "--height",
            "40%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "Select Mode> ",
            "--header",
            "Choose a mode (or press Esc to cancel)",
            "--with-nth",
            "1",
            "--delimiter",
            "\t",
            "--ansi",
        ]

        try:
            proc = subprocess.Popen(
                fzf_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            output, _ = proc.communicate(input=items.encode())

            if proc.returncode == 0 and output:
                selected = output.decode().strip().split("\t")[0]
                for name, mode_key, _ in modes:
                    if name == selected:
                        return mode_key
        except Exception:
            pass

        return None

    def run(self, initial_mode="files"):
        """Main loop to run the fuzzy finder."""
        mode = initial_mode
        last_mode = None
        modes = {
            "files": self.find_files,
            "grep": self.live_grep,
            "commits": self.git_commits,
            "status": self.git_status,
        }

        while mode in modes:
            action, data = modes[mode]()

            if action == "switch":
                if data == "select":
                    # Show mode selection screen
                    new_mode = self.select_mode(mode)
                    if new_mode and new_mode != mode:
                        last_mode = mode
                        mode = new_mode
                elif data == "last" and last_mode:
                    # Switch to last mode
                    mode, last_mode = last_mode, mode
                else:
                    last_mode = mode
                    mode = data
            elif action == "open":
                if isinstance(data, tuple):
                    self.open_file(data[0], data[1])
                else:
                    self.open_file(data)
                # Continue in VSCode, exit otherwise
                if os.environ.get("TERM_PROGRAM") != "vscode":
                    break
            elif action == "copy":
                self.copy_to_clipboard(data)
                break
            else:
                break


def main():
    parser = argparse.ArgumentParser(
        description="Fuzzy Finder - Search files, text, and git objects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  files    Search files by name (default)
  grep     Search text within files
  commits  Browse git commits
  status   Browse git changed files

Examples:
  %(prog)s              # Start in files mode
  %(prog)s grep         # Start in grep mode
  %(prog)s --completion # Print shell completion script
""",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["files", "grep", "commits", "status"],
        default="files",
        help="Initial mode (default: files)",
    )
    parser.add_argument(
        "--completion",
        action="store_true",
        help="Print shell completion script",
    )
    args = parser.parse_args()

    finder = FuzzyFinder()

    if args.completion:
        finder.print_completion()
    else:
        finder.run(args.mode)


if __name__ == "__main__":
    main()
