Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$cloneRoot = Join-Path $workspaceRoot "vendor\openclaude-upstream"
$extensionRoot = Join-Path $cloneRoot "vscode-extension\openclaude-vscode"

if (-not (Test-Path -LiteralPath $cloneRoot)) {
    git clone https://github.com/Gitlawb/openclaude.git $cloneRoot
} else {
    git -C $cloneRoot pull --ff-only
}

Push-Location $extensionRoot
try {
    cmd /c npm run package
    $vsix = Get-ChildItem -LiteralPath $extensionRoot -Filter "openclaude-vscode-*.vsix" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $vsix) {
        throw "Nenhum pacote VSIX foi gerado."
    }

    & code --install-extension $vsix.FullName
} finally {
    Pop-Location
}
