# Omni Overview

Omni is a software project that tries to turn an AI assistant into a runtime system instead of a simple chatbot.

A normal chatbot mostly receives text and returns text. Omni tries to do more than that. It tries to:

- understand the request
- decide what kind of runtime path is appropriate
- use memory and context
- plan actions when needed
- execute tool-backed work
- report what really happened

The project exists because many AI tools sound useful but are hard to trust. They may return a confident answer even when they actually used a shortcut, fell back to a safe template, or never executed the intended action path. Omni is being built to make those differences visible.

At a high level, Omni works like this:

1. A request enters through the API layer.
2. The Python runtime coordinates the turn.
3. The Node/Bun layer can provide a shortcut answer, a local answer, or a structured execution request.
4. The runtime may execute actions and then build the final response.
5. Observability data records which path really happened.

What makes Omni different from a chatbot is that it treats response generation as only one part of the system. The project also cares about execution, provenance, fallback behavior, runtime truth, and debugging.

Omni is still under active recovery and is not yet a fully stable system. The repository is open because understanding and improving the runtime behavior in public is part of the project itself.
