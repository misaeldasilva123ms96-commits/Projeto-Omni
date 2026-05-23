param(
    [string]$ExpectedRoot = ""
)

$ErrorActionPreference = "Stop"

function Test-RequiredPath {
    param(
        [string]$BasePath,
        [string]$RelativePath
    )

    return Test-Path (Join-Path $BasePath $RelativePath)
}

function Normalize-PathString {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }
    return ($Value.TrimEnd("\") -replace '/', '\')
}

if ([string]::IsNullOrWhiteSpace($ExpectedRoot)) {
    $ExpectedRoot = Split-Path -Parent $PSScriptRoot
}

try {
    $currentPath = (Get-Location).Path
    $resolvedExpectedRoot = (Resolve-Path -LiteralPath $ExpectedRoot).Path
} catch {
    Write-Error "Nao foi possivel resolver o caminho canonico do repositorio: $ExpectedRoot"
    exit 1
}

$gitTopLevel = $null
try {
    $gitTopLevel = (git rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0) {
        $gitTopLevel = $null
    }
} catch {
    $gitTopLevel = $null
}

$requiredPaths = @(
    ".git",
    "backend\python",
    "backend\rust",
    "frontend",
    "tests"
)

$missingPaths = @(
    $requiredPaths | Where-Object { -not (Test-RequiredPath -BasePath $resolvedExpectedRoot -RelativePath $_) }
)

if ($missingPaths.Count -gt 0) {
    Write-Error "O repo canonico esta inconsistente. Faltam caminhos obrigatorios em '$resolvedExpectedRoot': $($missingPaths -join ', ')"
    exit 1
}

$normalizedCurrentPath = Normalize-PathString $currentPath
$normalizedExpectedRoot = Normalize-PathString $resolvedExpectedRoot
$normalizedGitTopLevel = Normalize-PathString $gitTopLevel

$isCorrectRoot = $normalizedCurrentPath -eq $normalizedExpectedRoot
$gitMatchesExpected = $normalizedGitTopLevel -eq $normalizedExpectedRoot

if (-not $isCorrectRoot -or -not $gitMatchesExpected) {
    Write-Host "Workspace incorreto detectado." -ForegroundColor Yellow
    Write-Host "Atual:    $currentPath"
    Write-Host "Canonico: $resolvedExpectedRoot"
    if ($gitTopLevel) {
        Write-Host "Git root: $gitTopLevel"
    } else {
        Write-Host "Git root: nao detectado"
    }
    Write-Host ""
    Write-Host "Entre no projeto certo com:"
    Write-Host "Set-Location -LiteralPath '$resolvedExpectedRoot'"
    exit 2
}

Write-Host "OK: workspace canonico confirmado em '$resolvedExpectedRoot'." -ForegroundColor Green
exit 0
