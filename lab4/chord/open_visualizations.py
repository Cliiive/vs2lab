#!/usr/bin/env python3
"""
Launch VS Code to view Chord Ring Visualizations
Usage:
  python open_visualizations.py
  
This script:
1. Generates visualizations if they don't exist
2. Opens the visualisation folder in VS Code
3. Displays all available visualizations
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    visualisation_dir = script_dir / "visualisation"
    
    print("\n" + "="*50)
    print("CHORD RING VISUALIZATIONS - VS CODE")
    print("="*50 + "\n")
    
    # Check if visualisation folder exists
    if not visualisation_dir.exists():
        print("Generating visualizations first...")
        try:
            result = subprocess.run(
                ["pipenv", "run", "python", "visualize_matplotlib.py"],
                cwd=str(script_dir),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Error generating visualizations:\n{result.stderr}")
                return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    # Count PNG files
    png_files = list(visualisation_dir.glob("*.png"))
    
    if not png_files:
        print(f"Error: No PNG files found in {visualisation_dir}")
        return 1
    
    print(f"✓ Found {len(png_files)} visualization files")
    print(f"✓ Location: {visualisation_dir}")
    print("")
    
    # List files
    print("Available visualizations:")
    for png_file in sorted(png_files):
        size_mb = png_file.stat().st_size / (1024 * 1024)
        print(f"  ✓ {png_file.name} ({size_mb:.1f} MB)")
    
    print("")
    print("Opening VS Code with visualisation folder...")
    print("")
    
    # Open in VS Code
    try:
        subprocess.Popen(["code", str(visualisation_dir)])
        print("✓ VS Code launched!")
        print("")
        print("Tips:")
        print("  • Use image preview to view the visualizations")
        print("  • Click on any PNG to see details")
        print("  • Hover over images to see file info")
        print("")
    except FileNotFoundError:
        print("Error: VS Code (code) command not found.")
        print("Make sure VS Code is installed and in PATH.")
        return 1
    except Exception as e:
        print(f"Error launching VS Code: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
