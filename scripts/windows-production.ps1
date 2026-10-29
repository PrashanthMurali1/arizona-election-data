# Local-only operations. This helper never starts the public tunnel or scheduler.
[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'Build', 'Start', 'Verify', 'Status', 'Logs', 'Backup', 'Stop')]
    [string]$Action = 'Preflight'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker operation failed (exit $LASTEXITCODE)." }
}

Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install Docker Desktop with the WSL 2 backend, start it, then open a new PowerShell terminal. See docs/windows-deployment.md.'
    }
    $engine = & docker info --format '{{.OSType}}/{{.Architecture}}'
    if ($LASTEXITCODE -ne 0 -or $engine -notlike 'linux/*') {
        throw 'Docker must be running in Linux container mode.'
    }
    Invoke-Docker compose version
    # Validate without printing resolved environment values.
    Invoke-Docker compose config --quiet
    switch ($Action) {
        'Preflight' {
            Write-Host "Docker engine: $engine"
            Write-Host 'Configuration valid. Next: import the Mac export, then Build and Start. Public tunnel remains stopped.'
        }
        'Build' { Invoke-Docker compose build backend frontend }
        'Start' {
            foreach ($path in @('.production/seed/elections.db', '.production/raw', '.production/backups')) {
                if (-not (Test-Path -LiteralPath $path)) { throw "Missing $path; import the Mac export first." }
            }
            Invoke-Docker compose up -d --wait backend frontend
        }
        'Verify' {
            $configuration = & docker compose config --format json | ConvertFrom-Json
            if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve Compose configuration.' }
            $port = $configuration.services.frontend.ports[0].published
            $base = "http://127.0.0.1:$port"
            $health = Invoke-RestMethod "$base/api/health" -TimeoutSec 15
            $catalog = Invoke-RestMethod "$base/api/elections" -TimeoutSec 30
            $catalog = @($catalog)
            if ($catalog.Count -eq 0) { throw 'Election catalog is empty.' }
            $null = Invoke-RestMethod "$base/api/elections/az-2026-early-voting/activity" -TimeoutSec 30
            foreach ($election in $catalog) {
                if ($election.year -lt 2026) {
                    $null = Invoke-RestMethod "$base/api/elections/$($election.id)" -TimeoutSec 30
                }
            }
            foreach ($path in @('/', '/elections/az-2024-us-senate')) {
                $response = Invoke-WebRequest ($base + $path) -UseBasicParsing -TimeoutSec 15
                if ($response.StatusCode -ne 200 -or $response.Content -notmatch '<!doctype html>') {
                    throw "Frontend route check failed: $path"
                }
            }
            Write-Host "PASS health, $($catalog.Count) catalog entries, historical detail APIs, activity API and frontend deep link at $base"
            Invoke-Docker compose ps -a
        }
        'Status' { Invoke-Docker compose --profile scheduled --profile public ps -a }
        'Logs' { Invoke-Docker compose logs --tail 100 backend frontend }
        'Backup' { Invoke-Docker compose exec -T backend python production/manage_db.py backup }
        'Stop' { Invoke-Docker compose stop backend frontend }
    }
}
finally { Pop-Location }
