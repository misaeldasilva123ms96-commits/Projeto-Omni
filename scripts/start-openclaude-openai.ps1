param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OpenClaudeArgs
)

. (Join-Path $PSScriptRoot "openclaude-common.ps1")

$env:CLAUDE_CODE_USE_OPENAI = "1"
if ([string]::IsNullOrWhiteSpace($env:OPENAI_MODEL)) {
    $env:OPENAI_MODEL = "gpt-4o"
}
if ([string]::IsNullOrWhiteSpace($env:OPENAI_BASE_URL)) {
    $env:OPENAI_BASE_URL = "https://api.openai.com/v1"
}

Assert-OpenAIReady
Start-OpenClaude @OpenClaudeArgs
