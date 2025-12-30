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
        "switch_files": "ctrl-f",
        "switch_grep": "ctrl-g",
        "switch_commits": "ctrl-h",
        "switch_status": "ctrl-s",
        "list_up": "ctrl-u",
        "list_down": "ctrl-d",
        "preview_up": "ctrl-b",
        "preview_down": "ctrl-f",
        "toggle_mode_rg_fzf": "ctrl-t",
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
        # Preview command (suppress stderr for invalid digits bug)
        preview_cmd = (
            "bat --style=numbers --color=always --line-range :500 {} 2> /dev/null"
        )

        # Use prompt to store state: [H][I] = Hidden, Ignore flags
        # Default: Show hidden, Respect gitignore
        # Prompt format: "Files [H]> " means hidden enabled, ignore respected
        # "Files [H][I]> " means hidden enabled, no-ignore enabled

        # Build rg command based on prompt state
        rg_cmd_template = """
            FLAGS="--glob=!.git"
            [[ "$FZF_PROMPT" == *"[H]"* ]] && FLAGS="$FLAGS --hidden"
            [[ "$FZF_PROMPT" == *"[I]"* ]] && FLAGS="$FLAGS --no-ignore"
            rg --files $FLAGS
        """

        # Toggle hidden using transform action
        toggle_hidden = f"""transform:[[ "$FZF_PROMPT" == *"[H]"* ]] && \
            echo "change-prompt(Files> )+reload({rg_cmd_template})" || \
            echo "change-prompt(Files [H]> )+reload({rg_cmd_template})" """

        # Toggle ignore using transform action
        toggle_ignore = f"""transform:[[ "$FZF_PROMPT" == *"[I]"* ]] && \
            echo "change-prompt(${{FZF_PROMPT/\\[I\\]/}})+reload({rg_cmd_template})" || \
            echo "change-prompt(${{FZF_PROMPT/> /[I]> }})+reload({rg_cmd_template})" """

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
                "Files [H]> ",
                "--bind",
                f"start:reload:{rg_cmd_template}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_ignore']}:{toggle_ignore}",
                "--bind",
                f"{self.KEYBINDINGS['toggle_hidden']}:{toggle_hidden}",
                "--bind",
                f"{self.KEYBINDINGS['list_up']}:half-page-up",
                "--bind",
                f"{self.KEYBINDINGS['list_down']}:half-page-down",
                "--bind",
                f"{self.KEYBINDINGS['preview_up']}:preview-half-page-up",
                "--bind",
                f"{self.KEYBINDINGS['preview_down']}:preview-half-page-down",
                "--header",
                f"{self.KEYBINDINGS['toggle_ignore'].upper()}: Toggle Ignore | {self.KEYBINDINGS['toggle_hidden'].upper()}: Toggle Hidden | {self.KEYBINDINGS['switch_grep'].upper()}: Live Grep | {self.KEYBINDINGS['switch_commits'].upper()}: Commits | {self.KEYBINDINGS['switch_status'].upper()}: Status",
                "--expect",
                f"{self.KEYBINDINGS['switch_grep']},{self.KEYBINDINGS['switch_commits']},{self.KEYBINDINGS['switch_status']}",
            ]

            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            # Handle expect keys even when fzf exits with non-zero (e.g., no selection)
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

        # Use prompt to store state for hidden/ignore
        # Prompt format: "1. ripgrep [H]> " = hidden enabled in ripgrep mode
        rg_prefix = "rg --column --line-number --no-heading --color=always --smart-case"

        # Build rg command based on prompt state
        rg_cmd = f"""
            FLAGS=""
            [[ "$FZF_PROMPT" == *"[H]"* ]] && FLAGS="$FLAGS --hidden"
            [[ "$FZF_PROMPT" == *"[I]"* ]] && FLAGS="$FLAGS --no-ignore"
            {rg_prefix} $FLAGS {{q}} || true
        """

        # Preview command using delimiter to extract file and line
        preview_cmd = "bat --color=always --highlight-line {2} {1} 2>/dev/null"

        # Toggle hidden using transform
        toggle_hidden = f"""transform:[[ "$FZF_PROMPT" == *"[H]"* ]] && \
            echo "change-prompt(${{FZF_PROMPT/\\[H\\]/}})+reload({rg_cmd})" || \
            echo "change-prompt(${{FZF_PROMPT/ >/ [H]>}})+reload({rg_cmd})" """

        # Toggle ignore using transform
        toggle_ignore = f"""transform:[[ "$FZF_PROMPT" == *"[I]"* ]] && \
            echo "change-prompt(${{FZF_PROMPT/\\[I\\]/}})+reload({rg_cmd})" || \
            echo "change-prompt(${{FZF_PROMPT/ >/ [I]>}})+reload({rg_cmd})" """

        # Switch between ripgrep mode and fzf mode using transform
        switch_mode = f"""transform:[[ ! "$FZF_PROMPT" =~ ripgrep ]] && \
            echo "rebind(change)+change-prompt(1. ripgrep >)+disable-search+transform-query:echo {{q}} > {fzf_query_file}; cat {rg_query_file}" || \
            echo "unbind(change)+change-prompt(2. fzf >)+enable-search+transform-query:echo {{q}} > {rg_query_file}; cat {fzf_query_file}" """

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--disabled",
            "--query",
            "",
            "--bind",
            f"start:reload:{rg_cmd}",
            "--bind",
            f"change:reload:sleep 0.1; {rg_cmd}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_ignore']}:{toggle_ignore}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_hidden']}:{toggle_hidden}",
            "--bind",
            f"{self.KEYBINDINGS['toggle_mode_rg_fzf']}:{switch_mode}",
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
            "1. ripgrep >",
            "--header",
            f"{self.KEYBINDINGS['toggle_mode_rg_fzf'].upper()}: Toggle rg/fzf | {self.KEYBINDINGS['toggle_ignore'].upper()}: Ignore | {self.KEYBINDINGS['toggle_hidden'].upper()}: Hidden | {self.KEYBINDINGS['switch_files'].upper()}: Files | {self.KEYBINDINGS['switch_commits'].upper()}: Commits | {self.KEYBINDINGS['switch_status'].upper()}: Status",
            "--expect",
            f"{self.KEYBINDINGS['switch_files']},{self.KEYBINDINGS['switch_commits']},{self.KEYBINDINGS['switch_status']}",
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
            # Clean up temp files
            for f in [rg_query_file, fzf_query_file]:
                if os.path.exists(f):
                    os.remove(f)

        return "exit", None

    def git_commits(self):
        """
        Search git commits.
        Returns: (action, data)
        """
        # Git log command
        git_cmd = "git log --oneline --color=always"

        # Preview command
        preview_cmd = "git show {1} --color=always | bat --color=always --style=numbers 2> /dev/null"

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
            "Commits> ",
            "--bind",
            f"start:reload:{git_cmd}",
            "--bind",
            f"{self.KEYBINDINGS['list_up']}:half-page-up",
            "--bind",
            f"{self.KEYBINDINGS['list_down']}:half-page-down",
            "--bind",
            f"{self.KEYBINDINGS['preview_up']}:preview-half-page-up",
            "--bind",
            f"{self.KEYBINDINGS['preview_down']}:preview-half-page-down",
            "--header",
            f"{self.KEYBINDINGS['switch_files'].upper()}: Files | {self.KEYBINDINGS['switch_grep'].upper()}: Live Grep | {self.KEYBINDINGS['switch_status'].upper()}: Status | Enter: Copy Hash",
            "--expect",
            f"{self.KEYBINDINGS['switch_files']},{self.KEYBINDINGS['switch_grep']},{self.KEYBINDINGS['switch_status']}",
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
                    elif key == self.KEYBINDINGS["switch_status"]:
                        return "switch", "status"
                    elif selection and fzf_process.returncode == 0:
                        # Extract hash (first word)
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
        # Git status command
        git_cmd = "git status -s"

        # Preview command - extract filename from status line
        preview_cmd = "git diff --color=always -- {2..} | bat --color=always --style=numbers 2> /dev/null"

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
            "Status> ",
            "--bind",
            f"start:reload:{git_cmd}",
            "--bind",
            f"{self.KEYBINDINGS['list_up']}:half-page-up",
            "--bind",
            f"{self.KEYBINDINGS['list_down']}:half-page-down",
            "--bind",
            f"{self.KEYBINDINGS['preview_up']}:preview-half-page-up",
            "--bind",
            f"{self.KEYBINDINGS['preview_down']}:preview-half-page-down",
            "--header",
            f"{self.KEYBINDINGS['switch_files'].upper()}: Files | {self.KEYBINDINGS['switch_grep'].upper()}: Live Grep | {self.KEYBINDINGS['switch_commits'].upper()}: Commits",
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
