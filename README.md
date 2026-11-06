# API Explorer

A terminal user interface (TUI) tool to inspect, explore, and debug OpenAPI 3.1 endpoints and schemas directly from the command line.

## Purpose

The purpose of this tool is to provide an interactive, terminal-based viewer for OpenAPI specifications. It parses OpenAPI definitions from either a remote URL or a local file and displays the discovered routes, HTTP methods, summaries, parameters, request bodies, and responses in a keyboard-navigable interface.

## Command Line Usage

### Synopsis

```text
python term.py (-u URL | -f FILE) [-s {route,method}] [-t THEME] [--version] [-h]
```

### Options

- `-u URL`, `--url URL`  
  Base URL for fetching the OpenAPI specification. The tool automatically resolves and queries the specification endpoint.

- `-f FILE`, `--file FILE`  
  Path to a local OpenAPI-compatible JSON file.

- `-s {route,method}`, `--sort {route,method}`  
  Sort listed routes either by path (`route`, default) or HTTP verb (`method`).

- `-t THEME`, `--theme THEME`  
  Specify a custom theme definition file.

- `--version`  
  Display the application version.

- `-h`, `--help`  
  Show the help message and exit.

### Examples

Load a specification from a remote server:

```bash
python term.py -u http://localhost:8000
```

Load a specification from a local file:

```bash
python term.py -f ./openapi.json
```

Load a specification and sort endpoints by HTTP method:

```bash
python term.py -f ./openapi.json -s method
```

