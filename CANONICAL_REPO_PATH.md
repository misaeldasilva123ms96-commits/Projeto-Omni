# Canonical Repo Path

## Path to use

Use this repository root as the canonical workspace:

`C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project`

This is the real Git repository root. It contains:

- `.git`
- `backend/python`
- `backend/rust`
- `frontend`
- `tests`

## Path to avoid

Do not use this incomplete workspace as the project root:

`C:\ORÇAMETOS ANUAIS\Projeto omini`

It is not the real Git repository and can cause edits to land outside the tracked project.

## Safe check before working

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ensure-omni-root.ps1
```

Expected result:

```text
OK: workspace canonico confirmado ...
```

If the script reports `Workspace incorreto detectado`, switch to the canonical path first:

```powershell
Set-Location -LiteralPath "C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project"
```

## Practical recommendation

Before any coding, test, staging, or release step:

1. run `ensure-omni-root.ps1`
2. confirm the Git root matches the canonical path
3. only then continue with edits, tests, commits, or pushes
