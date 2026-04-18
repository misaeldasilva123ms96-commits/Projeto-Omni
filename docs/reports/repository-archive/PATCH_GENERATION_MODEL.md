# Patch Generation Model

## Patch object

`patch_generator.py` produces patch objects with:
- `file_path`
- `original_content_hash`
- `patch_diff`
- `confidence_score`
- `original_content`
- `new_content`

## Live behavior

- patches are generated from proposed file content
- patch diffs are persisted for operator inspection
- patches can be applied
- failed verification can trigger rollback

## Safety

- patch review runs through `review_patch_risk(...)`
- sensitive/generated targets can be rejected
- patch application remains explicit and reversible

## Boundaries

- this phase uses whole-file replacement with diff generation rather than a full multi-hunk patch planner
- confidence is explicit, but still heuristic
