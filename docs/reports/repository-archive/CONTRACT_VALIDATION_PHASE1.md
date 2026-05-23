# Contract Validation Phase 1

## Scope

Schema inspected:

- [runner-schema.v1.json](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project\contract\runner-schema.v1.json)

Runtime payload sources compared:

- [service_contracts.py](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project\backend\python\brain\runtime\service_contracts.py)
- [task_service.py](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project\backend\python\brain\runtime\task_service.py)
- [milestone_manager.py](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project\backend\python\brain\runtime\milestone_manager.py)

## Schema fields

Required root fields in `runner-schema.v1.json`:

- `message`
- `memory`
- `history`
- `summary`
- `capabilities`
- `session`

Schema role:

- validates the Node runner input payload
- does not currently model Python task envelopes or milestone/operator inspection payloads

## Runtime payload fields compared

### Task envelope

Observed from `TaskService.execute_task(...)`:

- `status`
- `user_id`
- `session_id`
- `task_id`
- `response`
- `links`

### Milestone state

Observed from `MilestoneManager.initialize_state(...)`:

- `root_milestone_id`
- `milestones`
- `completed_milestones`
- `blocked_milestones`

### Backward payload

Existing runner/fusion-compatible payload:

- `message`
- `memory`
- `history`
- `summary`
- `capabilities`
- `session`

## Forward validation result

Status: FAILED

Reason:

- Phase 10 Python service envelopes are not accepted by `runner-schema.v1.json`
- milestone state payloads are not accepted by `runner-schema.v1.json`

Representative validation errors:

- missing required property `message`
- missing required property `memory`
- missing required property `history`
- additional properties not allowed: `status`, `user_id`, `task_id`, `links`

## Backward validation result

Status: PASSED

Validated sample:

```json
{
  "message": "leia package.json",
  "memory": {},
  "history": [],
  "summary": "",
  "capabilities": [],
  "session": {
    "session_id": "backward-test"
  }
}
```

## Assessment

This is a contract-family mismatch, not a Phase 10 regression in the runner input contract.

`runner-schema.v1.json` still correctly validates the Node runner input payload.
It does not validate the Python service/operator payloads introduced and expanded across later phases.

## Schema diff

No schema change was applied in Phase 1.

Reason:

- making `runner-schema.v1.json` accept both Node runner input and Python service envelopes would require widening the root contract shape substantially
- that would go beyond the minimal-fix rule for this phase

## Conclusion

- backward validation: PASS
- forward validation against Phase 10 service envelopes: FAIL
- blocker status: OPEN

Recommended follow-up after Gate 1:

- add a separate service/operator schema for Python task envelopes and inspection payloads
- keep `runner-schema.v1.json` dedicated to Node runner input
