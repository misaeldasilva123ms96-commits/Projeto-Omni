Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "openclaude-common.ps1")

$workspaceRoot = Get-WorkspaceRoot
$checks = @()

function Add-CheckResult {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Details,
        [bool]$Critical = $true
    )

    $script:checks += [pscustomobject]@{
        Name = $Name
        Ok = $Ok
        Details = $Details
        Critical = $Critical
    }
}

function Get-VersionText {
    param(
        [string]$CommandLine
    )

    try {
        $value = Invoke-Expression $CommandLine 2>$null | Select-Object -First 1
        return [string]$value
    } catch {
        return ""
    }
}

Add-CheckResult -Name "Node.js" -Ok ([bool](Get-Command node -ErrorAction SilentlyContinue)) -Details (Get-VersionText "node -v")
Add-CheckResult -Name "npm" -Ok ([bool](Get-Command npm -ErrorAction SilentlyContinue)) -Details (Get-VersionText "cmd /c npm -v")
Add-CheckResult -Name "Git" -Ok ([bool](Get-Command git -ErrorAction SilentlyContinue)) -Details (Get-VersionText "git --version")
Add-CheckResult -Name "VS Code CLI" -Ok ([bool](Get-Command code -ErrorAction SilentlyContinue)) -Details (Get-VersionText "code --version")
Add-CheckResult -Name "ripgrep" -Ok ([bool](Get-Command rg -ErrorAction SilentlyContinue)) -Details (Get-VersionText "cmd /c rg --version")
Add-CheckResult -Name "OpenClaude CLI" -Ok ([bool](Get-Command openclaude -ErrorAction SilentlyContinue)) -Details (Get-VersionText "cmd /c openclaude --version")
Add-CheckResult -Name "Bun (optional)" -Ok ([bool](Get-Command bun -ErrorAction SilentlyContinue)) -Details (Get-VersionText "bun --version") -Critical $false
Add-CheckResult -Name "Codex auth file" -Ok (Test-Path -LiteralPath (Join-Path $HOME ".codex\auth.json")) -Details (Join-Path $HOME ".codex\auth.json")
Add-CheckResult -Name ".env.openclaude.local (optional)" -Ok (Test-Path -LiteralPath (Join-Path $workspaceRoot ".env.openclaude.local")) -Details (Join-Path $workspaceRoot ".env.openclaude.local") -Critical $false
Add-CheckResult -Name "OpenClaude VS Code extension" -Ok ([bool]((code --list-extensions) -match "devnull-bootloader.openclaude-vscode")) -Details "devnull-bootloader.openclaude-vscode"
Add-CheckResult -Name "OpenAI / Codex VS Code extension" -Ok ([bool]((code --list-extensions) -match "openai.chatgpt")) -Details "openai.chatgpt"

$checks | Select-Object Name, Ok, Details | Format-Table -AutoSize

$failedCritical = @($checks | Where-Object { $_.Critical -and -not $_.Ok })
if ($failedCritical.Count -gt 0) {
    exit 1
}
