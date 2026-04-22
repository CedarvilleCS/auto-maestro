# Frontend (NiceGUI)

The Frontend provides the user interaction layer for AutoMaestro.
Built with NiceGUI, it serves as the visual interface for monitoring agent orchestration, confidence scoring, sandbox execution, and system state transitions in real time.
The frontend is intentionally lightweight and Python-native to maintain architectural cohesion with the backend.

---

## Overview

The frontend enables users to:

- Submit high-level task requests to the agent orchestration layer
- View real-time agent transitions
- Monitor confidence scores for each response
- Observe sandbox command execution output
- Inspect logs and debugging information
- Interact with backend endpoints via persistent connections

The UI is designed to support transparency and human-in-the-loop oversight, reinforcing AutoMaestro’s reliability-first architecture.

---

## Architectural Role

The frontend supports architectural transparency by exposing:

- Active agent identity
- Agent transition flow
- Confidence scoring metadata
- Structured execution output from the MCP server

Rather than hiding AI reasoning, the interface surfaces operational context to the operator.
This design promotes calibrated trust instead of blind automation.

---

## Structure

```
packages/frontend/
├── src/
│   ├── main.py        # Application entry point
│   ├── pages/         # UI page definitions
│   ├── components/    # Reusable UI components
│   └── assets/        # Static assets (CSS, images)
└── README.md
```

## Running the Frontend (Development)

From the project root:
```bash
uv run --env-file .env.dev -- py packages/frontend/src/frontend/main.py
```
The application will start a local web server and display the access URL in the console.
---

## Design Philosophy

The frontend avoids heavy JavaScript frameworks in favor of:
- Python-based UI logic
- Rapid iteration
- Tight backend integration
- Minimal cross-language complexity
This keeps the project maintainable and consistent across the stack.

---

## Related READMEs
[MAIN](../../README.md)

[Backend](../backend/README.md)

[MCP](../../sandbox_setup/mcp/README.md)


