# RTOP

A command-line tool to inspect, explore, and debug OpenAPI 3.1 endpoints and schemas directly from the command line.

## Purpose

The purpose of this tool is to provide an interactive, terminal-based viewer for OpenAPI specifications. It parses OpenAPI definitions from either a remote URL or a local file (JSON or YAML) and displays the discovered routes, HTTP methods, summaries, parameters, request bodies, and responses in a keyboard-navigable interface.

## Installation

An automated compilation and installation script is provided in [`install.sh`](./install.sh):

```bash
# Enable execution bit for the installation script
chmod +x install.sh

# Standard installation (compiles byte-code and links rtop to ~/.local/bin/rtop)
./install.sh

# Optional: compile a standalone binary using PyInstaller
./install.sh --binary
```

Ensure `~/.local/bin` is in your `PATH` by adding it to your shell configuration (`~/.bashrc` or `~/.zshrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

You can also run directly from source:

```bash
rtop --help
```

## Command Line Usage

### Synopsis

```text
rtop (-u URL | -f FILE) [-s {route,method}] [-i INTERVAL] [-t THEME] [--version] [-h]
```

### Options

- `-u URL`, `--url URL`  
  Base URL for fetching the OpenAPI specification. The tool automatically resolves and queries `/openapi.json`.

- `-f FILE`, `--file FILE`  
  Path to a local OpenAPI specification file (supports both JSON and YAML formats).

- `-s {route,method}`, `--sort {route,method}`  
  Sort listed routes either by path (`route`, default) or HTTP verb (`method`).

- `-i INTERVAL`, `--interval INTERVAL`  
  Polling interval in seconds (default: `5.0`) to periodically re-fetch and live-update the OpenAPI documentation in the background when loading from a URL.

- `-t THEME`, `--theme THEME`  
  Path to a theme file (e.g. `theme.yaml`, `theme.json`) or a theme name.

- `--version`  
  Display the application version.

- `-h`, `--help`  
  Show the help message and exit.

### Keybindings & Controls

- `Up` / `Down`: Navigate through routes list or menu items.
- `Enter`: View detailed information for the highlighted route.
- `/`: Open the Command Menu in the middle of the screen (switch theme, change sorting).
- `q` / `Q`: Close active panel or quit application.

## Themes Configuration

Themes customize colors and text styling for the interface. You can copy the template at [`themes/template.yaml`](file:///home/datura/Desktop/.tmp/rtop/themes/template.yaml) to create custom themes.

### Theme Discovery & Resolution Order

When resolving themes, `rtop` looks for theme files in the following priority:

1. **Local Working Directory** (highest preference):
   - `./<theme>`
   - `./<theme>.yaml` / `./<theme>.yml` / `./<theme>.json`
   - `./themes/<theme>`
2. **Global User Configuration Directory**:
   - **Linux / macOS**: `~/.config/rtop/` (or `$XDG_CONFIG_HOME/rtop/`)
   - **Windows**: `%APPDATA%\rtop\`
3. **Bundled Themes**:
   - Packaged default themes inside `themes/` (`dark.yaml`, `light.json`).

If `-t` is omitted, `rtop` checks for a `theme.yaml` or `theme.json` in your local working directory first, then in your global config directory, falling back to the bundled `dark.yaml`.

## Examples

Load a specification from a remote server with a 10-second refresh interval:

```bash
rtop -u http://localhost:8000 -i 10.0
```

Load a specification from a local JSON or YAML file:

```bash
rtop -f ./openapi.json
rtop -f ./openapi.yaml
```

Load a specification using a custom theme file from the local directory or global config:

```bash
rtop -f ./openapi.json -t ./my_theme.yaml
rtop -f ./openapi.json -t light
```

Load a specification and sort endpoints by HTTP method:

```bash
rtop -f ./openapi.json -s method
```

>[!NOTE] Certain features are bound to break in windows