#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TARGET_DIR="${HOME}/.local/bin"
mkdir -p "$TARGET_DIR"

echo "[*] Installing rtop"

MODE="${1:-}"

if [ "$MODE" = "--binary" ]; then
    echo "Compiling standalone binary with PyInstaller..."
    if ! command -v pyinstaller &>/dev/null; then
        echo "Error: pyinstaller is not installed." >&2
        exit 1
    fi

    pyinstaller --noconfirm --clean --onefile \
        --name rtop \
        --add-data "themes:themes" \
        rtop.py

    cp "$SCRIPT_DIR/dist/rtop" "$TARGET_DIR/rtop"
    chmod +x "$TARGET_DIR/rtop"
    echo "Standalone executable installed to $TARGET_DIR/rtop"

else
    echo "Compiling byte-code and linking launcher to $TARGET_DIR/rtop..."
    python3 -m compileall -q "$SCRIPT_DIR"

    # Create wrapper executable in ~/.local/bin
    cat <<EOF > "$TARGET_DIR/rtop"
#!/usr/bin/env bash
exec python3 "$SCRIPT_DIR/rtop.py" "\$@"
EOF
    chmod +x "$TARGET_DIR/rtop"
    echo "Launcher script created at $TARGET_DIR/rtop"
fi

# Check PATH
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo ""
    echo "Note: $TARGET_DIR is not currently in your PATH."
    echo "Add it by adding the following line to ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "[+] Installation complete"
echo "You can now run 'rtop --help'"
