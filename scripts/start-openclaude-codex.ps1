param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OpenClaudeArgs
)

. (Join-Path $PSScriptRoot "openclaude-common.ps1")

$env:CLAUDE_CODE_USE_OPENAI = "1"
if ([string]::IsNullOrWhiteSpace($env:OPENAI_MODEL)) {
    $env:OPENAI_MODEL = "codexplan"
}
if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    $env:CODEX_HOME = (Join-Path $HOME ".codex")
}
if ([string]::IsNullOrWhiteSpace($env:CODEX_AUTH_JSON_PATH)) {
    $defaultAuth = Join-Path $HOME ".codex\auth.json"
    if (Test-Path -LiteralPath $defaultAuth) {
        $env:CODEX_AUTH_JSON_PATH = $defaultAuth
    }
}

Assert-CodexReady
Start-OpenClaude @OpenClaudeArgs
