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
        """
        print("Mode: Find Files")

        # Base rg command parts
        rg_base = "rg --files --hidden --glob '!.git'"

        # Preview command
        preview_cmd = "bat --style=numbers --color=always --line-range :500 {}"

        # Reload commands
        reload_default = f"reload({rg_base})+change-prompt(Files> )"
        reload_no_ignore = f"reload({rg_base} --no-ignore)+change-prompt(All Files> )"

        try:
            # Initial command
            initial_cmd = rg_base

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
                f"ctrl-i:{reload_no_ignore}",
                "--bind",
                f"ctrl-x:{reload_default}",
                "--header",
                "CTRL-I: Include ignored files | CTRL-X: Exclude ignored files",
            ]

            # We need to run the initial command and pipe it, OR use FZF_DEFAULT_COMMAND
            # Using FZF_DEFAULT_COMMAND is easier for the initial load if we want to use subprocess.
            # But here we can just pipe the output of the initial rg run.
            # However, if we use reload, fzf will take over.

            # Let's use subprocess to pipe initial input, and fzf handles reloads.
            rg_process = subprocess.Popen(
                initial_cmd, shell=True, stdout=subprocess.PIPE
            )
            fzf_process = subprocess.Popen(
                fzf_cmd, stdin=rg_process.stdout, stdout=subprocess.PIPE
            )
            rg_process.stdout.close()

            output, _ = fzf_process.communicate()

            if fzf_process.returncode == 0 and output:
                selected_file = output.decode("utf-8").strip()
                self.open_file(selected_file)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")

    def live_grep(self):
        """
        Search for text within files.
        """
        print("Mode: Live Grep")

        # State file for ignore toggle
        import tempfile

        # Create a temp file to get a unique name, then close and remove it
        tf = tempfile.NamedTemporaryFile(delete=False)
        state_file = tf.name
        tf.close()
        os.remove(state_file)

        # Command to check state and run rg
        # We use a shell command that checks for existence of state_file
        # If exists -> --no-ignore

        rg_cmd_template = "rg --column --line-number --no-heading --color=always --smart-case {ignore_flag} {{q}} || true"

        # We construct a shell command for reload
        # Note: We need to escape properly for fzf binding

        shell_cmd = f"if [ -f {state_file} ]; then {rg_cmd_template.format(ignore_flag='--no-ignore')}; else {rg_cmd_template.format(ignore_flag='')}; fi"

        preview_cmd = "bat --style=numbers --color=always --highlight-line {2} {1}"

        # Toggle command: touch/rm file and trigger reload
        toggle_cmd = f"execute(if [ -f {state_file} ]; then rm {state_file}; else touch {state_file}; fi)+reload({shell_cmd})"

        fzf_cmd = [
            "fzf",
            "--ansi",
            "--disabled",
            "--bind",
            f"change:reload:{shell_cmd}",
            "--bind",
            'start:reload:echo "Type to search..."',
            "--bind",
            f"ctrl-i:{toggle_cmd}",
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
            "CTRL-I: Toggle ignored files",
        ]

        try:
            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()

            if fzf_process.returncode == 0 and output:
                selected_line = output.decode("utf-8").strip()
                parts = selected_line.split(":")
                if len(parts) >= 2:
                    filename = parts[0]
                    line_num = parts[1]
                    self.open_file(filename, line_num)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if os.path.exists(state_file):
                os.remove(state_file)

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

    def main(self):
        parser = argparse.ArgumentParser(description="Fuzzy Finder Tool")
        parser.add_argument(
            "mode",
            nargs="?",
            choices=["files", "grep"],
            default="files",
            help="Mode: files (default) or grep",
        )
        args = parser.parse_args()

        if args.mode == "files":
            self.find_files()
        elif args.mode == "grep":
            self.live_grep()


if __name__ == "__main__":
    finder = FuzzyFinder()
    finder.main()
