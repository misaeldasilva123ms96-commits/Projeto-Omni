param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OpenClaudeArgs
)

. (Join-Path $PSScriptRoot "openclaude-common.ps1")

$env:CLAUDE_CODE_USE_OPENAI = "1"
$env:OPENAI_BASE_URL = if ([string]::IsNullOrWhiteSpace($env:OLLAMA_BASE_URL)) { "http://localhost:11434/v1" } else { $env:OLLAMA_BASE_URL }
$env:OPENAI_MODEL = if ([string]::IsNullOrWhiteSpace($env:OLLAMA_MODEL)) { "qwen2.5-coder:7b" } else { $env:OLLAMA_MODEL }

Assert-OllamaReady
Start-OpenClaude @OpenClaudeArgs
