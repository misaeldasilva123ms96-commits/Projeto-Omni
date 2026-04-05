Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Import-OpenClaudeEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }

        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $name = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1).Trim()

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

function Get-OpenClaudeDistPath {
    $candidates = @(
        (Join-Path $env:APPDATA "npm\node_modules\@gitlawb\openclaude\dist\cli.mjs"),
        (Join-Path (Get-WorkspaceRoot) "vendor\openclaude-upstream\dist\cli.mjs")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "OpenClaude não foi localizado. Reinstale com 'npm install -g @gitlawb/openclaude'."
}

function Test-PlaceholderValue {
    param(
        [AllowNull()]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $true
    }

    $normalized = $Value.Trim().ToUpperInvariant()
    return $normalized -in @(
        "COLOCAR_CHAVE_AQUI",
        "YOUR_KEY_HERE",
        "SK-YOUR-KEY-HERE",
        "CHANGE_ME"
    )
}

function Assert-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName,
        [Parameter(Mandatory = $true)]
        [string]$InstallHint
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Comando '$CommandName' não encontrado. $InstallHint"
    }
}

function Assert-OpenAIReady {
    if (Test-PlaceholderValue $env:OPENAI_API_KEY) {
        throw "OPENAI_API_KEY ausente ou em placeholder. Preencha `.env.openclaude.local` ou exporte a variável antes de iniciar."
    }
}

function Assert-CodexReady {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_API_KEY)) {
        return
    }

    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_AUTH_JSON_PATH) -and (Test-Path -LiteralPath $env:CODEX_AUTH_JSON_PATH)) {
        return
    }

    $defaultAuth = Join-Path $HOME ".codex\auth.json"
    if (Test-Path -LiteralPath $defaultAuth) {
        $env:CODEX_AUTH_JSON_PATH = $defaultAuth
        return
    }

    throw "Credenciais Codex não encontradas. Garanta `$HOME\.codex\auth.json` ou defina CODEX_API_KEY / CODEX_AUTH_JSON_PATH."
}

function Assert-OllamaReady {
    Assert-CommandAvailable -CommandName "ollama" -InstallHint "Instale o Ollama e confirme que `ollama --version` responde."

    $portOpen = Test-NetConnection -ComputerName "localhost" -Port 11434 -WarningAction SilentlyContinue
    if (-not $portOpen.TcpTestSucceeded) {
        throw "Ollama não está respondendo em http://localhost:11434. Inicie o serviço antes de abrir o OpenClaude."
    }
}

function Start-OpenClaude {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    Assert-CommandAvailable -CommandName "node" -InstallHint "Instale o Node.js 20+."
    Assert-CommandAvailable -CommandName "rg" -InstallHint "Instale o ripgrep e confirme `rg --version`."

    $workspaceRoot = Get-WorkspaceRoot
    $localEnvPath = Join-Path $workspaceRoot ".env.openclaude.local"
    Import-OpenClaudeEnvFile -Path $localEnvPath

    $distPath = Get-OpenClaudeDistPath
    & node $distPath @Arguments
}
