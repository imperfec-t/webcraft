# Copy the webcraft skills into an agent's skills folder, no Python needed.
#   .\install.ps1 [claude|codex|gemini|copilot|agents] [-Project] [-Dest C:\dir]
# With Python, prefer: webcraft install <agent>  (also does Cursor, Windsurf and AGENTS.md).
param(
    [ValidateSet('claude', 'codex', 'gemini', 'copilot', 'agents')]
    [string]$Agent = 'claude',
    [switch]$Project,
    [string]$Dest
)
$ErrorActionPreference = 'Stop'
if (-not $Dest) {
    $userPaths = @{ claude = '.claude\skills'; codex = '.agents\skills'; agents = '.agents\skills'; gemini = '.gemini\skills'; copilot = '.copilot\skills' }
    $projectPaths = @{ claude = '.claude\skills'; codex = '.agents\skills'; agents = '.agents\skills'; gemini = '.gemini\skills'; copilot = '.github\skills' }
    if ($Project) { $Dest = Join-Path (Get-Location) $projectPaths[$Agent] }
    else { $Dest = Join-Path $env:USERPROFILE $userPaths[$Agent] }
}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$count = 0
foreach ($d in Get-ChildItem -Path (Join-Path $PSScriptRoot 'skills') -Directory) {
    if (-not (Test-Path (Join-Path $d.FullName 'SKILL.md'))) { continue }
    $target = Join-Path $Dest $d.Name
    if ((Test-Path $target) -and -not (Test-Path (Join-Path $target '.webcraft'))) {
        Write-Host "skip   $target (exists and was not installed by webcraft)"; continue
    }
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    Copy-Item -Recurse -Path $d.FullName -Destination $target
    Set-Content -Path (Join-Path $target '.webcraft') -Value 'installed by webcraft (install.ps1)' -Encoding utf8
    Write-Host "install $target"
    $count++
}
Write-Host "Done: $count skill(s) in $Dest. Restart the agent to pick them up."
