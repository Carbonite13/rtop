# API Explorer

A terminal user interface (TUI) tool to inspect, explore, and debug OpenAPI 3.1 endpoints and schemas directly from the command line.

## Purpose

The purpose of this tool is to provide an interactive, terminal-based viewer for OpenAPI specifications. It parses OpenAPI definitions from either a remote URL or a local file and displays the discovered routes, HTTP methods, summaries, parameters, request bodies, and responses in a keyboard-navigable interface.

## Command Line Usage

### Synopsis

```text
rtop (-u URL | -f FILE) [-s {route,method}] [-t THEME] [--version] [-h]
```

### Options

- `-u URL`, `--url URL`  
  Base URL for fetching the OpenAPI specification. The tool automatically resolves and queries the specification endpoint.

- `-f FILE`, `--file FILE`  
  Path to a local OpenAPI-compatible JSON file.

- `-s {route,method}`, `--sort {route,method}`  
  Sort listed routes either by path (`route`, default) or HTTP verb (`method`).

- `-i INTERVAL`, `--interval INTERVAL`  
  Polling interval in seconds (default: `5.0`) to periodically re-fetch the OpenAPI documentation in the background when loading from a URL.

- `-t THEME`, `--theme THEME`  
  Path to a theme configuration file (e.g. `theme.yaml`, `theme.json`) or a built-in theme name (`dark`, `light`).

- `--version`  
  Display the application version.

- `-h`, `--help`  
  Show the help message and exit.

### Examples

Load a specification from a remote server with a 10-second refresh interval:

```bash
./rtop -u http://localhost:8000 -i 10.0
```

Load a specification from a local file:

```bash
./rtop -f ./openapi.json
```

Load a specification with a custom theme file:

```bash
./rtop -f ./openapi.json -t ./theme.yaml
```

Load a specification and sort endpoints by HTTP method:

```bash
./rtop -f ./openapi.json -s method
```

