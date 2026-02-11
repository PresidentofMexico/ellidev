import os
import datetime
from pathlib import Path

# Files/Folders to ignore to keep the update clean
IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'env', '.idea', '.vscode', 'node_modules'}
IGNORE_FILES = {'.DS_Store', 'snapshot.py', '.env', 'GEMINI.md'}

def generate_snapshot():
    output = []
    
    # 1. Generate Tree Structure
    output.append("=== PROJECT STRUCTURE ===")
    for root, dirs, files in os.walk("."):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        level = root.replace(".", "").count(os.sep)
        indent = " " * 4 * (level)
        output.append(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 4 * (level + 1)
        for f in files:
            # Ignore this script, hidden files, and previous snapshots
            if f not in IGNORE_FILES and not f.endswith('.pyc') and not f.startswith('elli_snapshot_'):
                output.append(f"{subindent}{f}")

    output.append("\n=== FILE CONTENTS ===")

    # 2. Add File Contents
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            # Skip ignored files and previous snapshots
            if file in IGNORE_FILES or file.endswith('.pyc') or file.startswith('elli_snapshot_'):
                continue
                
            file_path = os.path.join(root, file)
            output.append(f"\n--- START FILE: {file_path} ---")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    output.append(f.read())
            except Exception as e:
                output.append(f"[Error reading file: {e}]")
                
            output.append(f"--- END FILE: {file_path} ---\n")

    # 3. Determine Output Path (Downloads Folder)
    # Using pathlib for cross-platform home directory resolution
    home = Path.home()
    downloads_dir = home / "Downloads"
    
    # Fallback to Desktop if Downloads doesn't exist
    if not downloads_dir.exists():
        downloads_dir = home / "Desktop"

    # 4. Generate Timestamped Filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"elli_snapshot_{timestamp}.txt"
    full_path = downloads_dir / filename

    # 5. Write to file
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(output))
        
        print(f"✅ Snapshot generated: {full_path}")
        print("📋 You can drag and drop this file into Gemini/Claude.")
    except Exception as e:
        print(f"❌ Error writing to {downloads_dir}: {e}")
        # Fallback to local if permission fails
        local_filename = f"elli_snapshot_{timestamp}.txt"
        with open(local_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(output))
        print(f"⚠️ Saved to local folder instead: {local_filename}")

if __name__ == "__main__":
    generate_snapshot()