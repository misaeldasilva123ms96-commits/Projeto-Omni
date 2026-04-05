Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$requiredCommands = @("node", "npm", "git", "code", "rg", "openclaude")
foreach ($command in $requiredCommands) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatório ausente: $command"
    }
}

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$codexAuthPath = Join-Path $HOME ".codex\auth.json"

if (-not (Test-Path -LiteralPath $codexAuthPath)) {
    throw "Arquivo de autenticação do Codex não encontrado: $codexAuthPath"
}

$openClaudeVersion = cmd /c openclaude --version
if (-not $openClaudeVersion) {
    throw "OpenClaude não retornou versão."
}

$ripgrepVersion = cmd /c rg --version | Select-Object -First 1
if (-not $ripgrepVersion) {
    throw "ripgrep não retornou versão."
}

Write-Host "Workspace:" $workspaceRoot
Write-Host "OpenClaude:" $openClaudeVersion
Write-Host "ripgrep:" $ripgrepVersion
Write-Host "Codex auth:" $codexAuthPath
