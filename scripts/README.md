# Scripts

This folder contains utility and orchestration scripts used to manage the AutoMaestro environment.  
They simplify common setup, teardown, and maintenance tasks for both developers and automated workflows.

## Overview

These scripts control Docker Compose services and the sandbox environment.  
They ensure consistent startup and shutdown behavior across all modules — backend, frontend, and MCP.

## Notes

- use `chmod +x <scriptname.sh>` to make it executable

## up.sh

- safely builds the SEED Lab environment, automaestro agent, and mcp server 
- keeps SEED containers separate

## down.sh

- safely removes all containers and networks

## install_llama._cpp.bat

## run_llama_server.bat

## Related README.md

[MAIN](../README.md)

[SANDBOX](../sandbox_setup/README.md)

[MCP](../sandbox_setup/mcp/README/md)
