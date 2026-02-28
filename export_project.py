#!/usr/bin/env python3
"""
Export entire project structure and contents to a single text file.
"""

import os
from pathlib import Path
from datetime import datetime

# Extensions to parse and include content
PARSABLE_EXTENSIONS = {
    '.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini',
    '.sh', '.bash', '.zsh', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
    '.xml', '.sql', '.env', '.gitignore', '.dockerignore', '.editorconfig',
    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.rb', '.php',
    '.swift', '.kt', '.r', '.m', '.mm', '.scala', '.clj', '.ex', '.exs'
}

# Directories to skip
SKIP_DIRS = {
    '.git', '.svn', '.hg', '__pycache__', 'node_modules', '.venv', 'venv',
    'env', '.env', 'dist', 'build', '.idea', '.vscode', '.DS_Store',
    'eggs', '.eggs', '*.egg-info', '.pytest_cache', '.mypy_cache', '.tox'
}


def should_skip_dir(dir_name: str) -> bool:
    """Check if directory should be skipped"""
    return dir_name in SKIP_DIRS or dir_name.startswith('.')


def is_parsable(file_path: Path) -> bool:
    """Check if file should have its content included"""
    # Check extension
    if file_path.suffix.lower() in PARSABLE_EXTENSIONS:
        return True
    
    # Check for files without extension that are typically text
    if not file_path.suffix and file_path.name in {
        'Makefile', 'Dockerfile', 'Vagrantfile', 'Procfile', 'LICENSE', 'README'
    }:
        return True
    
    return False


def is_binary(file_path: Path) -> bool:
    """Quick check if file is binary"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(512)  # Try to read first 512 bytes as text
        return False
    except (UnicodeDecodeError, PermissionError):
        return True


def get_tree_structure(root_path: Path, prefix: str = "", is_last: bool = True) -> list[str]:
    """Generate tree structure representation"""
    lines = []
    
    # Current item
    connector = "└── " if is_last else "├── "
    lines.append(f"{prefix}{connector}{root_path.name}")
    
    if root_path.is_dir() and not should_skip_dir(root_path.name):
        # Get children
        try:
            children = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            children = [c for c in children if not (c.is_dir() and should_skip_dir(c.name))]
            
            for i, child in enumerate(children):
                is_last_child = i == len(children) - 1
                extension = "    " if is_last else "│   "
                lines.extend(get_tree_structure(child, prefix + extension, is_last_child))
        except PermissionError:
            pass
    
    return lines


def export_project(root_dir: str, output_file: str = "project_export.txt"):
    """Export entire project to a single text file"""
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists():
        print(f"Error: Directory {root_dir} does not exist")
        return
    
    output_path = root_path / output_file
    
    with open(output_path, 'w', encoding='utf-8') as out:
        # Header
        out.write("=" * 80 + "\n")
        out.write("PROJECT EXPORT\n")
        out.write("=" * 80 + "\n")
        out.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"Root Directory: {root_path}\n")
        out.write("=" * 80 + "\n\n")
        
        # Directory Tree
        out.write("DIRECTORY STRUCTURE\n")
        out.write("-" * 80 + "\n")
        out.write(f"{root_path.name}/\n")
        
        try:
            children = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            children = [c for c in children if not (c.is_dir() and should_skip_dir(c.name))]
            children = [c for c in children if c.name != output_file]  # Skip output file itself
            
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                tree_lines = get_tree_structure(child, "", is_last)
                for line in tree_lines:
                    out.write(line + "\n")
        except PermissionError:
            out.write("(Permission Denied)\n")
        
        out.write("\n" + "=" * 80 + "\n\n")
        
        # File Contents
        out.write("FILE CONTENTS\n")
        out.write("=" * 80 + "\n\n")
        
        # Walk through all files
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip hidden directories and common ignore patterns
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
            
            # Sort for consistent output
            filenames.sort()
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                
                # Skip the output file itself
                if file_path == output_path:
                    continue
                
                # Get relative path for display
                try:
                    rel_path = file_path.relative_to(root_path)
                except ValueError:
                    rel_path = file_path
                
                # Check if we should parse this file
                if is_parsable(file_path) and not is_binary(file_path):
                    file_count += 1
                    out.write("-" * 80 + "\n")
                    out.write(f"FILE: {rel_path}\n")
                    out.write("-" * 80 + "\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            out.write(content)
                            if not content.endswith('\n'):
                                out.write('\n')
                    except Exception as e:
                        out.write(f"(Error reading file: {e})\n")
                    
                    out.write("\n\n")
                else:
                    # Just list binary/non-parsable files
                    out.write(f"[BINARY/SKIPPED] {rel_path}\n")
        
        # Footer
        out.write("=" * 80 + "\n")
        out.write(f"Export complete. {file_count} files exported.\n")
        out.write("=" * 80 + "\n")
    
    print(f"✅ Project exported to: {output_path}")
    print(f"📁 {file_count} files included")


if __name__ == "__main__":
    import sys
    
    # Get current directory or use provided argument
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.getcwd()
    
    # Output file name
    if len(sys.argv) > 2:
        output = sys.argv[2]
    else:
        output = "project_export.txt"
    
    export_project(directory, output)
