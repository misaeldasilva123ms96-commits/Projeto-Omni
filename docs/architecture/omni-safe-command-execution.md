# Omni Safe Command Execution

Omni Safe Command Execution is the future architecture boundary between
governance decisions and sandbox command execution.

Phase 16 implements only the decision gate. It returns structured policy
decisions describing whether command text is safe for future sandbox execution.
No command is executed in this phase.

## Future Flow

1. Receive command request metadata.
2. Normalize command text conservatively.
3. Redact secret-like markers.
4. Classify the command category.
5. Apply mode rules.
6. Apply main-branch and exception gates.
7. Return a decision requiring Runtime Truth and sandbox isolation for future
   eligible commands.

## Enforcement Boundaries

- Command execution remains disabled in this phase.
- `command_execution_allowed` remains false.
- Network access remains false.
- Secret access remains false.
- Production and destructive actions remain false.
- Git mutation flags remain false.
- Merge commands remain blocked in this gate.

Future execution must be implemented separately and must consume the gate
decision, Runtime Truth contract, sandbox isolation, autonomy policy, and human
exception gates.

Phase 17 adds the Sandbox Command Runner as that separate implementation. It is
denied by default, runs only in `sandbox_readonly`, uses `shell=False`, and
executes only read-safe commands that the gate approves.
