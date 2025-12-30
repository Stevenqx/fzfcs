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
        Returns: (action, data)
        """
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
                "CTRL-I: Include ignored | CTRL-X: Exclude ignored | CTRL-G: Live Grep | CTRL-H: Commits",
                "--expect",
                "ctrl-g,ctrl-h",
            ]
            
            rg_process = subprocess.Popen(initial_cmd, shell=True, stdout=subprocess.PIPE)
            fzf_process = subprocess.Popen(fzf_cmd, stdin=rg_process.stdout, stdout=subprocess.PIPE)
            rg_process.stdout.close()
            
            output, _ = fzf_process.communicate()
            
            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").strip().split("\n")
                if not lines:
                    return "exit", None
                
                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None
                
                if key == "ctrl-g":
                    return "switch", "grep"
                elif key == "ctrl-h":
                    return "switch", "commits"
                elif selection:
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
        # State file for ignore toggle
        import tempfile

        # Create a temp file to get a unique name, then close and remove it
        tf = tempfile.NamedTemporaryFile(delete=False)
        state_file = tf.name
        tf.close()
        os.remove(state_file)

        # Command to check state and run rg
        rg_cmd_template = "rg --column --line-number --no-heading --color=always --smart-case {ignore_flag} {{q}} || true"
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
            "CTRL-I: Toggle ignored | CTRL-F: Files | CTRL-H: Commits",
            "--expect",
            "ctrl-f,ctrl-h",
        ]
        
        try:
            fzf_process = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE)
            output, _ = fzf_process.communicate()
            
            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").strip().split("\n")
                if not lines:
                    return "exit", None
                    
                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None
                
                if key == "ctrl-f":
                    return "switch", "files"
                elif key == "ctrl-h":
                    return "switch", "commits"
                elif selection:
                    parts = selection.split(":")
                    if len(parts) >= 2:
                        return "open", (parts[0], parts[1])
                    
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if os.path.exists(state_file):
                os.remove(state_file)
                
        return "exit", None

    def git_commits(self):
        """
        Search git commits.
        Returns: (action, data)
        """
        # Git log command
        git_cmd = "git log --oneline --color=always"
        
        # Preview command
        preview_cmd = "git show {1} --color=always | bat --color=always --style=numbers"
        
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
            "CTRL-F: Files | CTRL-G: Live Grep | Enter: Copy Hash",
            "--expect",
            "ctrl-f,ctrl-g",
        ]
        
        try:
            git_process = subprocess.Popen(git_cmd, shell=True, stdout=subprocess.PIPE)
            fzf_process = subprocess.Popen(fzf_cmd, stdin=git_process.stdout, stdout=subprocess.PIPE)
            git_process.stdout.close()
            
            output, _ = fzf_process.communicate()
            
            if fzf_process.returncode == 0 and output:
                lines = output.decode("utf-8").strip().split("\n")
                if not lines:
                    return "exit", None
                
                key = lines[0]
                selection = lines[1] if len(lines) > 1 else None
                
                if key == "ctrl-f":
                    return "switch", "files"
                elif key == "ctrl-g":
                    return "switch", "grep"
                elif selection:
                    # Extract hash (first word)
                    commit_hash = selection.split()[0]
                    return "copy", commit_hash
                    
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
    opts="files grep commits"

    if [[ ${cur} == * ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _fuzzy_finder_completion fuzzy_finder.py
"""
        print(script)

    def main(self):
        parser = argparse.ArgumentParser(description="Fuzzy Finder Tool")
        parser.add_argument(
            "mode",
            nargs="?",
            choices=["files", "grep", "commits"],
            default="files",
            help="Mode: files (default), grep, or commits",
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
                        p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
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
