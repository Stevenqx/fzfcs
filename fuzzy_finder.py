#!/usr/bin/env python3
import subprocess
import sys
import os
import shutil
import argparse


class FuzzyFinder:
    KEYBINDINGS = {
        "toggle_ignore": "alt-i",
        "toggle_hidden": "alt-u",
        "switch_files": "ctrl-j",
        "switch_grep": "ctrl-k",
        "switch_commits": "ctrl-g",
        "switch_status": "ctrl-h",
        "list_up": "ctrl-u",
        "list_down": "ctrl-d",
        "preview_up": "ctrl-b",
        "preview_down": "ctrl-f",
        "toggle_mode_rg_fzf": "ctrl-t",
        "clear_query": "ctrl-l",
    }

    def __init__(self):
        self.check_dependencies()
        self.workspace_root = self.find_workspace_root()
        if self.workspace_root:
            os.chdir(self.workspace_root)

    def check_dependencies(self):
        required_tools = ["fzf", "rg", "bat"]
        missing_tools = [tool for tool in required_tools if not shutil.which(tool)]
        if missing_tools:
            print(f"Error: The following tools are missing: {', '.join(missing_tools)}")
            print("Please install them to use this tool.")
            sys.exit(1)

    def find_workspace_root(self):
        # Simple check for .git directory
        current_dir = os.getcwd()
        while current_dir != "/":
            if os.path.exists(os.path.join(current_dir, ".git")):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        return os.getcwd()  # Fallback to current directory

    def find_files(self):
        """
        Search files in the current repository.
        Returns: (action, data)
        """
        preview_cmd = (
            "bat --style=numbers --color=always --line-range :500 {} 2>/dev/null"
        )

        # rg commands for each state
        rg_base = "rg --files"
        rg_h = "rg --files --hidden"
        rg_i = "rg --files --no-ignore"
        rg_hi = "rg --files --hidden --no-ignore"

        # Toggle hidden: H> <-> > or HI> <-> I>
        toggle_hidden_cmd = (
            "case $FZF_PROMPT in "
            f"*HI*) echo 'change-prompt(Files I>)+reload({rg_i})';; "
            f"*H*) echo 'change-prompt(Files >)+reload({rg_base})';; "
            f"*I*) echo 'change-prompt(Files HI>)+reload({rg_hi})';; "
            f"*) echo 'change-prompt(Files H>)+reload({rg_h})';; "
            "esac"
        )

        # Toggle ignore: I> <-> > or HI> <-> H>
        toggle_ignore_cmd = (
            "case $FZF_PROMPT in "
            f"*HI*) echo 'change-prompt(Files H>)+reload({rg_h})';; "
            f"*I*) echo 'change-prompt(Files >)+reload({rg_base})';; "
            f"*H*) echo 'change-prompt(Files HI>)+reload({rg_hi})';; "
            f"*) echo 'change-prompt(Files I>)+reload({rg_i})';; "
            "esac"
        )

        try:
            fzf_cmd = [
                "fzf",
                "--preview",
                preview_cmd,
                "--height",
                "100%",
                "--layout=reverse",
                "--border",
                "--prompt",
                "Files H>",
                "--bind",
                f"start:reload:{rg_h}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_hidden']}:transform:{toggle_hidden_cmd}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_ignore']}:transform:{toggle_ignore_cmd}",
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
                "--header",
                f"{self.KEYBINDINGS['toggle_ignore'].upper()}: Ignore | {self.KEYBINDINGS['toggle_hidden'].upper()}: Hidden | {self.KEYBINDINGS['clear_query'].upper()}: Clear | {self.KEYBINDINGS['switch_grep'].upper()}: Grep | {self.KEYBINDINGS['switch_commits'].upper()}: Commits | {self.KEYBINDINGS['switch_status'].upper()}: Status",
                "--expect",
                f"{self.KEYBINDINGS['switch_grep']},{self.KEYBINDINGS['switch_commits']},{self.KEYBINDINGS['switch_status']}",
            ]

            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            if output:
                lines = output.decode("utf-8").splitlines()
                if lines:
                    key = lines[0]
                    selection = lines[1] if len(lines) > 1 else None

                    if key == self.KEYBINDINGS["switch_grep"]:
                        return "switch", "grep"
                    elif key == self.KEYBINDINGS["switch_commits"]:
                        return "switch", "commits"
                    elif key == self.KEYBINDINGS["switch_status"]:
                        return "switch", "status"
                    elif selection and fzf_process.returncode == 0:
                        return "open", selection

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")

        return "exit", None

    def live_grep(self):
        """
        Search for text within files.
        Returns: (action, data)
        """
        import tempfile

        # Create temp files for query state when switching between rg/fzf modes
        tf = tempfile.NamedTemporaryFile(delete=False, prefix="fzf_rg_")
        rg_query_file = tf.name
        tf.close()
        tf = tempfile.NamedTemporaryFile(delete=False, prefix="fzf_fzf_")
        fzf_query_file = tf.name
        tf.close()

        rg_prefix = "rg --column --line-number --no-heading --color=always --smart-case"

        # rg commands for each state (with {q} placeholder for query)
        rg_base = f"{rg_prefix} {{q}} || true"
        rg_h = f"{rg_prefix} --hidden {{q}} || true"
        rg_i = f"{rg_prefix} --no-ignore {{q}} || true"
        rg_hi = f"{rg_prefix} --hidden --no-ignore {{q}} || true"

        preview_cmd = "bat --color=always --highlight-line {2} {1} 2>/dev/null"

        # Toggle hidden: rgH> <-> rg>, rgHI> <-> rgI>
        toggle_hidden_cmd = (
            "case $FZF_PROMPT in "
            f"*HI*) echo 'change-prompt(rgI>)+reload({rg_i})';; "
            f"*H*) echo 'change-prompt(rg>)+reload({rg_base})';; "
            f"*I*) echo 'change-prompt(rgHI>)+reload({rg_hi})';; "
            f"*rg*) echo 'change-prompt(rgH>)+reload({rg_h})';; "
            f"*) echo 'change-prompt(fzfH>)';; "
            "esac"
        )

        # Toggle ignore: rgI> <-> rg>, rgHI> <-> rgH>
        toggle_ignore_cmd = (
            "case $FZF_PROMPT in "
            f"*HI*) echo 'change-prompt(rgH>)+reload({rg_h})';; "
            f"*I*) echo 'change-prompt(rg>)+reload({rg_base})';; "
            f"*H*) echo 'change-prompt(rgHI>)+reload({rg_hi})';; "
            f"*rg*) echo 'change-prompt(rgI>)+reload({rg_i})';; "
            f"*) echo 'change-prompt(fzfI>)';; "
            "esac"
        )

        # Switch between ripgrep mode and fzf mode
        switch_mode_cmd = (
            f"[[ $FZF_PROMPT == *rg* ]] && "
            f"echo 'unbind(change)+change-prompt(fzf>)+enable-search+transform-query:echo {{q}} > {rg_query_file}; cat {fzf_query_file}' || "
            f"echo 'rebind(change)+change-prompt(rgH>)+disable-search+transform-query:echo {{q}} > {fzf_query_file}; cat {rg_query_file}'"
        )

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--disabled",
            "--query",
            "",
            "--bind",
            f"start:reload:{rg_h}",
            "--bind",
            f"change:reload:sleep 0.1; {rg_h}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_hidden']}:transform:{toggle_hidden_cmd}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_ignore']}:transform:{toggle_ignore_cmd}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_mode_rg_fzf']}:transform:{switch_mode_cmd}",
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
            "--delimiter",
            ":",
            "--preview",
            preview_cmd,
            "--preview-window",
            "up,60%,border-bottom,+{2}+3/3,~3",
            "--height",
            "100%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "rgH>",
            "--header",
            f"{self.KEYBINDINGS['toggle_mode_rg_fzf'].upper()}: rg/fzf | {self.KEYBINDINGS['toggle_ignore'].upper()}: Ignore | {self.KEYBINDINGS['toggle_hidden'].upper()}: Hidden | {self.KEYBINDINGS['clear_query'].upper()}: Clear | {self.KEYBINDINGS['switch_files'].upper()}: Files | {self.KEYBINDINGS['switch_commits'].upper()}: Commits | {self.KEYBINDINGS['switch_status'].upper()}: Status",
            "--expect",
            f"{self.KEYBINDINGS['switch_files']},{self.KEYBINDINGS['switch_commits']},{self.KEYBINDINGS['switch_status']}",
        ]

        try:
            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            if output:
                lines = output.decode("utf-8").splitlines()
                if lines:
                    key = lines[0]
                    selection = lines[1] if len(lines) > 1 else None

                    if key == self.KEYBINDINGS["switch_files"]:
                        return "switch", "files"
                    elif key == self.KEYBINDINGS["switch_commits"]:
                        return "switch", "commits"
                    elif key == self.KEYBINDINGS["switch_status"]:
                        return "switch", "status"
                    elif selection and fzf_process.returncode == 0:
                        parts = selection.split(":")
                        if len(parts) >= 2:
                            return "open", (parts[0], parts[1])

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            for f in [rg_query_file, fzf_query_file]:
                if os.path.exists(f):
                    os.remove(f)

        return "exit", None

    def git_commits(self):
        """
        Search git commits.
        Returns: (action, data)
        """
        git_cmd = "git log --oneline --color=always"
        preview_cmd = "git show {1} --color=always | bat --color=always --style=numbers 2>/dev/null"

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--preview",
            preview_cmd,
            "--height",
            "100%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "Commits>",
            "--bind",
            f"start:reload:{git_cmd}",
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
            "--header",
            f"{self.KEYBINDINGS['clear_query'].upper()}: Clear | {self.KEYBINDINGS['switch_files'].upper()}: Files | {self.KEYBINDINGS['switch_grep'].upper()}: Grep | {self.KEYBINDINGS['switch_status'].upper()}: Status | Enter: Copy Hash",
            "--expect",
            f"{self.KEYBINDINGS['switch_files']},{self.KEYBINDINGS['switch_grep']},{self.KEYBINDINGS['switch_status']}",
        ]

        try:
            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            if output:
                lines = output.decode("utf-8").splitlines()
                if lines:
                    key = lines[0]
                    selection = lines[1] if len(lines) > 1 else None

                    if key == self.KEYBINDINGS["switch_files"]:
                        return "switch", "files"
                    elif key == self.KEYBINDINGS["switch_grep"]:
                        return "switch", "grep"
                    elif key == self.KEYBINDINGS["switch_status"]:
                        return "switch", "status"
                    elif selection and fzf_process.returncode == 0:
                        commit_hash = selection.split()[0]
                        return "copy", commit_hash

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")

        return "exit", None

    def git_status(self):
        """
        Search changed files (git status).
        Returns: (action, data)
        """
        git_cmd = "git status -s"
        preview_cmd = "git diff --color=always -- {2..} | bat --color=always --style=numbers 2>/dev/null"

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--preview",
            preview_cmd,
            "--height",
            "100%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "Status>",
            "--bind",
            f"start:reload:{git_cmd}",
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
            "--header",
            f"{self.KEYBINDINGS['clear_query'].upper()}: Clear | {self.KEYBINDINGS['switch_files'].upper()}: Files | {self.KEYBINDINGS['switch_grep'].upper()}: Grep | {self.KEYBINDINGS['switch_commits'].upper()}: Commits",
            "--expect",
            f"{self.KEYBINDINGS['switch_files']},{self.KEYBINDINGS['switch_grep']},{self.KEYBINDINGS['switch_commits']}",
        ]

        try:
            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            # Handle expect keys even when fzf exits with non-zero
            if output:
                lines = output.decode("utf-8").splitlines()
                if lines:
                    key = lines[0]
                    selection = lines[1] if len(lines) > 1 else None

                    if key == self.KEYBINDINGS["switch_files"]:
                        return "switch", "files"
                    elif key == self.KEYBINDINGS["switch_grep"]:
                        return "switch", "grep"
                    elif key == self.KEYBINDINGS["switch_commits"]:
                        return "switch", "commits"
                    elif selection and fzf_process.returncode == 0:
                        # Extract filename from status line (XY Path)
                        parts = selection.strip().split()
                        if len(parts) >= 2:
                            filename = parts[-1]
                            return "open", filename

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")

        return "exit", None

    def open_file(self, filename, line_num=None):
        """
        Open the selected file.
        """
        print(f"Opening: {filename}" + (f":{line_num}" if line_num else ""))

        # Check for VSCode
        if os.environ.get("TERM_PROGRAM") == "vscode":
            cmd = [
                "code",
                "-r",
                "-g",
                f"{filename}:{line_num}" if line_num else filename,
            ]
            subprocess.run(cmd)
        else:
            # Fallback to printing or $EDITOR
            editor = os.environ.get("EDITOR", "vim")
            if line_num:
                cmd = [editor, f"+{line_num}", filename]
            else:
                cmd = [editor, filename]
            subprocess.run(cmd)

    def print_completion(self):
        """
        Print shell completion script.
        """
        script = """
# Bash completion for fuzzy_finder.py
_fuzzy_finder_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="files grep commits status"

    if [[ ${cur} == * ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _fuzzy_finder_completion fuzzy_finder.py

# Zsh completion
# autoload -U +X compinit && compinit
# compdef _fuzzy_finder_zsh fuzzy_finder.py
_fuzzy_finder_zsh() {
    local -a opts
    opts=('files' 'grep' 'commits' 'status')
    _describe 'command' opts
}

# Fish completion
# complete -c fuzzy_finder.py -f -a "files grep commits status"
"""
        print(script)

    def main(self):
        parser = argparse.ArgumentParser(description="Fuzzy Finder Tool")
        parser.add_argument(
            "mode",
            nargs="?",
            choices=["files", "grep", "commits", "status"],
            default="files",
            help="Mode: files (default), grep, commits, or status",
        )
        parser.add_argument(
            "--completion",
            action="store_true",
            help="Print shell completion script",
        )
        args = parser.parse_args()

        if args.completion:
            self.print_completion()
            return

        current_mode = args.mode

        while True:
            if current_mode == "files":
                action, data = self.find_files()
            elif current_mode == "grep":
                action, data = self.live_grep()
            elif current_mode == "commits":
                action, data = self.git_commits()
            elif current_mode == "status":
                action, data = self.git_status()
            else:
                break

            if action == "switch":
                current_mode = data
            elif action == "open":
                if isinstance(data, tuple):
                    self.open_file(data[0], data[1])
                else:
                    self.open_file(data)

                # Keep running if in VSCode
                if os.environ.get("TERM_PROGRAM") != "vscode":
                    break
            elif action == "copy":
                # Try to copy to clipboard (Linux/Mac)
                try:
                    if shutil.which("xclip"):
                        p = subprocess.Popen(
                            ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
                        )
                        p.communicate(input=data.encode("utf-8"))
                        print(f"Copied {data} to clipboard (xclip)")
                    elif shutil.which("pbcopy"):
                        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                        p.communicate(input=data.encode("utf-8"))
                        print(f"Copied {data} to clipboard (pbcopy)")
                    else:
                        print(f"Clipboard tool not found. Hash: {data}")
                except Exception as e:
                    print(f"Error copying to clipboard: {e}")
                break
            else:
                break


if __name__ == "__main__":
    finder = FuzzyFinder()
    finder.main()
