#!/usr/bin/env python3

import subprocess
import os

def get_git_log_data(path):
    """Fetches git log data for a given path."""
    try:
        separator = "|||---|||"
        format_string = f"%an{separator}%ad"
        # Using '--' to separate paths from revisions is a good practice
        command = ["git", "log", "--follow", f"--pretty=format:{format_string}", "--", path]

        output = subprocess.check_output(
            command,
            stderr=subprocess.PIPE,
            text=True
        ).strip()

        if not output:
            return "N/A", "N/A", "N/A"

        lines = output.splitlines()

        last_committer = lines[0].split(separator)[0]
        first_committer = lines[-1].split(separator)[0]
        first_commit_date = lines[-1].split(separator)[1]

        return first_committer, last_committer, first_commit_date

    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return "N/A", "N/A", "N/A"

def find_recipe_dirs():
    """Dynamically finds recipe directories by identifying leaf directories."""
    recipe_dirs = []
    top_dirs = ["RL", "inference", "training"]
    for top_dir in top_dirs:
        if not os.path.isdir(top_dir):
            continue
        for root, dirs, files in os.walk(top_dir):
            # A recipe is a leaf directory within the top-level sections.
            if not dirs:
                recipe_dirs.append(root)
    return recipe_dirs

def main():
    """Generates a Markdown table of recipe commit history."""

    recipe_dirs = find_recipe_dirs()

    with open("recipe_commit_history.md", "w") as f:
        f.write("| Recipe Directory | First Committer | Last Committer | First Commit Date |\\n")
        f.write("|---|---|---|---|\\n")

        for directory in sorted(recipe_dirs):
            first_committer, last_committer, first_commit_date = get_git_log_data(directory)

            f.write(
                f"| {directory} | {first_committer} | {last_committer} | "
                f"{first_commit_date} |\\n"
            )

if __name__ == "__main__":
    main()
