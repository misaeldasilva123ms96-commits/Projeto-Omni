# Agent instructions

## Git worktree policy

All Git worktrees for Projeto-Omni MUST be created using an absolute path
under:

```text
D:\Dev\Worktrees
```

The required naming convention is:

```text
D:\Dev\Worktrees\Projeto-Omni-<sanitized-branch-name>
```

Sanitize only the directory name. Do not rename or otherwise modify the Git
branch. Replace `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`, and whitespace
with `-`. Collapse repeated `-` characters and trim leading or trailing `-`
characters from the sanitized component.

Examples:

```text
feat/external-api
=> D:\Dev\Worktrees\Projeto-Omni-feat-external-api

audit/runtime
=> D:\Dev\Worktrees\Projeto-Omni-audit-runtime

feat/external-api/open-meteo
=> D:\Dev\Worktrees\Projeto-Omni-feat-external-api-open-meteo
```

Before creating a worktree, verify that the destination does not already exist.

Always pass the absolute target path explicitly to `git worktree add`.

For a new branch:

```powershell
git worktree add `
  "D:\Dev\Worktrees\Projeto-Omni-feat-example" `
  -b "feat/example"
```

For an existing branch:

```powershell
git worktree add `
  "D:\Dev\Worktrees\Projeto-Omni-feat-example" `
  "feat/example"
```

Never create worktrees:

- inside the main repository;
- beside `D:\Dev\Projetos\Projeto-Omni`;
- under `C:`;
- under `%TEMP%`;
- under `.worktrees`;
- under a relative `worktrees` directory;
- with an implicit or relative target path;
- anywhere outside `D:\Dev\Worktrees`.

Never move a registered worktree manually with Windows Explorer. Use
`git worktree move`.
