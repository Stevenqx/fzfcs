#!/usr/bin/env python3
import subprocess
import sys
import os
import shutil
import argparse


class FuzzyFinder:
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
        # State files
        import tempfile

        tf = tempfile.NamedTemporaryFile(delete=False)
        base_state = tf.name
        tf.close()
        os.remove(base_state)

        state_hidden = base_state + "_hidden"
        state_no_ignore = base_state + "_no_ignore"

        # Default: Show hidden (create file), Respect ignore (no file)
        open(state_hidden, "w").close()
        if os.path.exists(state_no_ignore):
            os.remove(state_no_ignore)

        # Base rg command parts
        # We construct the command dynamically based on state files
        rg_cmd = f"""
            FLAGS=""
            if [ -f {state_hidden} ]; then FLAGS="$FLAGS --hidden"; fi
            if [ -f {state_no_ignore} ]; then FLAGS="$FLAGS --no-ignore"; fi
            rg --files $FLAGS --glob '!.git'
        """

        # Preview command (suppress stderr for invalid digits bug)
        preview_cmd = (
            "bat --style=numbers --color=always --line-range :500 {} 2> /dev/null"
        )

        # Toggle commands
        toggle_hidden = f"execute(if [ -f {state_hidden} ]; then rm {state_hidden}; else touch {state_hidden}; fi)+reload({rg_cmd})"
        toggle_ignore = f"execute(if [ -f {state_no_ignore} ]; then rm {state_no_ignore}; else touch {state_no_ignore}; fi)+reload({rg_cmd})"

        try:
            # Initial command
            # We need to run the shell command to get initial output
            # But subprocess.Popen needs a string for shell=True
            initial_cmd = f"bash -c '{rg_cmd}'"

            fzf_cmd = [
                "fzf",
                "--preview",
                preview_cmd,
                "--height",
                "80%",
                "--layout=reverse",
                "--border",
                "--prompt",
                "Files> ",
                "--bind",
                f"ctrl-i:{toggle_ignore}",
                "--bind",
                f"ctrl-y:{toggle_hidden}",
                "--header",
                "CTRL-I: Toggle Ignore | CTRL-Y: Toggle Hidden | CTRL-G: Live Grep | CTRL-H: Commits | CTRL-S: Status",
                "--expect",
                "ctrl-g,ctrl-h,ctrl-s",
            ]

            rg_process = subprocess.Popen(
                initial_cmd, shell=True, stdout=subprocess.PIPE
            )
            fzf_process = subprocess.Popen(
                fzf_cmd, stdin=rg_process.stdout, stdout=subprocess.PIPE
            )
            rg_process.stdout.close()

            output, _ = fzf_process.communicate()

            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").splitlines()
                if not lines:
                    return "exit", None

                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None

                if key == "ctrl-g":
                    return "switch", "grep"
                elif key == "ctrl-h":
                    return "switch", "commits"
                elif key == "ctrl-s":
                    return "switch", "status"
                elif selection:
                    return "open", selection

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if os.path.exists(state_hidden):
                os.remove(state_hidden)
            if os.path.exists(state_no_ignore):
                os.remove(state_no_ignore)

        return "exit", None

    def live_grep(self):
        """
        Search for text within files.
        Returns: (action, data)
        """
        # State files
        import tempfile

        tf = tempfile.NamedTemporaryFile(delete=False)
        base_state = tf.name
        tf.close()
        os.remove(base_state)

        state_hidden = base_state + "_hidden"
        state_no_ignore = base_state + "_no_ignore"

        # Default: Hide hidden (no file), Respect ignore (no file) - Standard grep behavior
        # But user might want to toggle hidden.
        if os.path.exists(state_hidden):
            os.remove(state_hidden)
        if os.path.exists(state_no_ignore):
            os.remove(state_no_ignore)

        # Command to check state and run rg
        rg_cmd_template = "rg --column --line-number --no-heading --color=always --smart-case {flags} {{q}} || true"

        shell_cmd = f"""
            FLAGS=""
            if [ -f {state_hidden} ]; then FLAGS="$FLAGS --hidden"; fi
            if [ -f {state_no_ignore} ]; then FLAGS="$FLAGS --no-ignore"; fi
            {rg_cmd_template.format(flags="$FLAGS")}
        """

        preview_cmd = (
            "bat --style=numbers --color=always --highlight-line {2} {1} 2> /dev/null"
        )

        # Toggle commands
        toggle_hidden = f"execute(if [ -f {state_hidden} ]; then rm {state_hidden}; else touch {state_hidden}; fi)+reload({shell_cmd})"
        toggle_ignore = f"execute(if [ -f {state_no_ignore} ]; then rm {state_no_ignore}; else touch {state_no_ignore}; fi)+reload({shell_cmd})"

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--disabled",
            "--bind",
            f"change:reload:{shell_cmd}",
            "--bind",
            'start:reload:echo "Type to search..."',
            "--bind",
            f"ctrl-i:{toggle_ignore}",
            "--bind",
            f"ctrl-y:{toggle_hidden}",
            "--preview",
            preview_cmd,
            "--preview-window",
            "up,60%,border-bottom,+{2}+3/3,~3",
            "--height",
            "80%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "Grep> ",
            "--header",
            "CTRL-I: Toggle Ignore | CTRL-Y: Toggle Hidden | CTRL-F: Files | CTRL-H: Commits | CTRL-S: Status",
            "--expect",
            "ctrl-f,ctrl-h,ctrl-s",
        ]

        try:
            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").splitlines()
                if not lines:
                    return "exit", None

                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None

                if key == "ctrl-f":
                    return "switch", "files"
                elif key == "ctrl-h":
                    return "switch", "commits"
                elif key == "ctrl-s":
                    return "switch", "status"
                elif selection:
                    parts = selection.split(":")
                    if len(parts) >= 2:
                        return "open", (parts[0], parts[1])

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if os.path.exists(state_hidden):
                os.remove(state_hidden)
            if os.path.exists(state_no_ignore):
                os.remove(state_no_ignore)

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
            "80%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "Commits> ",
            "--header",
            "CTRL-F: Files | CTRL-G: Live Grep | CTRL-S: Status | Enter: Copy Hash",
            "--expect",
            "ctrl-f,ctrl-g,ctrl-s",
        ]

        try:
            git_process = subprocess.Popen(git_cmd, shell=True, stdout=subprocess.PIPE)
            fzf_process = subprocess.Popen(
                fzf_cmd, stdin=git_process.stdout, stdout=subprocess.PIPE
            )
            git_process.stdout.close()

            output, _ = fzf_process.communicate()

            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").splitlines()
                if not lines:
                    return "exit", None

                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None

                if key == "ctrl-f":
                    return "switch", "files"
                elif key == "ctrl-g":
                    return "switch", "grep"
                elif key == "ctrl-s":
                    return "switch", "status"
                elif selection:
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
        # -s: short format
        git_cmd = "git status -s --color=always"

        # Preview command
        # We need to extract filename from status line.
        # Status line: " M file.py" or "?? file.py"
        # {2} usually works if there are 2 columns.
        # But sometimes filenames have spaces.
        # Let's try to use {2..}
        preview_cmd = "git diff --color=always -- {2..} | bat --color=always --style=numbers 2> /dev/null"

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--preview",
            preview_cmd,
            "--height",
            "80%",
            "--layout=reverse",
            "--border",
            "--prompt",
            "Status> ",
            "--header",
            "CTRL-F: Files | CTRL-G: Live Grep | CTRL-H: Commits",
            "--expect",
            "ctrl-f,ctrl-g,ctrl-h",
        ]

        try:
            git_process = subprocess.Popen(git_cmd, shell=True, stdout=subprocess.PIPE)
            fzf_process = subprocess.Popen(
                fzf_cmd, stdin=git_process.stdout, stdout=subprocess.PIPE
            )
            git_process.stdout.close()

            output, _ = fzf_process.communicate()

            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").splitlines()
                if not lines:
                    return "exit", None

                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None

                if key == "ctrl-f":
                    return "switch", "files"
                elif key == "ctrl-g":
                    return "switch", "grep"
                elif key == "ctrl-h":
                    return "switch", "commits"
                elif selection:
                    # Extract filename.
                    # Format: XY Path
                    # XY is 2 chars, then space, then path.
                    # But sometimes there are arrows for renames.
                    # For simplicity, let's take the last part or everything after index 3.
                    parts = selection.strip().split()
                    if len(parts) >= 2:
                        filename = parts[-1]  # Simple case
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
