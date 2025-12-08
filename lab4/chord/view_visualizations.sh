#!/bin/bash
# View Chord Ring Visualizations in VS Code

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VISUALISATION_DIR="$SCRIPT_DIR/visualisation"

# Check if visualisation folder exists
if [ ! -d "$VISUALISATION_DIR" ]; then
    echo "Generating visualizations first..."
    cd "$SCRIPT_DIR"
    pipenv run python visualize_matplotlib.py
fi

# Count generated files
PNG_COUNT=$(find "$VISUALISATION_DIR" -name "*.png" 2>/dev/null | wc -l)

if [ $PNG_COUNT -eq 0 ]; then
    echo "Error: No PNG files found in $VISUALISATION_DIR"
    exit 1
fi

echo ""
echo "=========================================="
echo "CHORD RING VISUALIZATIONS"
echo "=========================================="
echo ""
echo "Location: $VISUALISATION_DIR"
echo "Files: $PNG_COUNT PNG images"
echo ""
echo "Opening in VS Code..."
echo ""

# Open visualisation folder in VS Code
code "$VISUALISATION_DIR"

# List the files
echo "Available visualizations:"
ls -1 "$VISUALISATION_DIR"/*.png | while read file; do
    echo "  ✓ $(basename "$file")"
done

echo ""
echo "VS Code has been opened with the visualisation folder."
echo ""
