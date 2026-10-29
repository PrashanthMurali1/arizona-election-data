[CmdletBinding()]
param(
    [ValidateSet('Prepare','Install','Status','Verify','Pause','Resume','Run','Retry','Rollback','Recover','AcceptRecovery','Uninstall')]
    [string]$Action = 'Status'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$workerHome = Join-Path $root '.production/deploy'
$snapshot = Join-Path $workerHome 'worker'
$configPath = Join-Path $workerHome 'config.json'
$taskName = 'Arizona Election Explorer - Deploy main'

function Invoke-Worker([string]$Operation) {
    $configuration = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    & $configuration.python (Join-Path $snapshot 'scripts/deploy_worker.py') --config $configPath $Operation
    if ($LASTEXITCODE -ne 0) { throw "Worker $Operation failed (exit $LASTEXITCODE). See .production/deploy/logs/deploy.jsonl." }
}

switch ($Action) {
    { $_ -in @('Install','Prepare') } {
        $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($existing) { $null = Disable-ScheduledTask -TaskName $taskName; $existing = Get-ScheduledTask -TaskName $taskName }
        if ($existing -and $existing.State -eq 'Running') { throw 'A deployment is active. Wait for it to finish before updating the worker.' }
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $sid = $identity.User.Value
        $python = & (Join-Path $root '.venv/Scripts/python.exe') -c 'import sys;print(sys._base_executable)'
        if ($LASTEXITCODE -ne 0) { throw 'Cannot find the installed Python interpreter.' }
        $python = $python.Trim()
        $pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
        if (-not (Test-Path -LiteralPath $pythonw)) { throw 'pythonw.exe is required for hidden operation.' }
        $null = New-Item -ItemType Directory -Path $snapshot -Force
        # Keep resolved configuration, state and logs private to this Windows user.
        & icacls $workerHome /inheritance:r /grant:r ($identity.Name + ':(OI)(CI)F') | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot protect the worker directory.' }
        foreach ($relative in @('scripts/deploy_worker.py','backend/app/observability.py','backend/app/log_export.py')) {
            $destination = Join-Path $snapshot $relative
            $null = New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force
            Copy-Item -LiteralPath (Join-Path $root $relative) -Destination $destination
        }
        Push-Location $root
        try {
            $resolved = & docker compose --profile public --profile scheduled config --format json | ConvertFrom-Json
            if ($LASTEXITCODE -ne 0) { throw 'Cannot read the existing Compose configuration.' }
        } finally { Pop-Location }
        $configuration = [ordered]@{
            home=$workerHome; production_root=$root; python=$python
            docker=(Get-Command docker.exe).Source; git=(Get-Command git.exe).Source; npm=(Get-Command npm.cmd).Source
            docker_desktop='C:\Program Files\Docker\Docker\Docker Desktop.exe'; start_docker=$true
            local_port=[int]$resolved.services.frontend.ports[0].published
            public_url='https://azelections.app'
            log_region=[string]$resolved.services.backend.environment.NEW_RELIC_LOGS_REGION
            log_limit=[int]$resolved.services.backend.environment.NEW_RELIC_LOGS_PER_MINUTE
        }
        $configuration | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
        if (-not (Test-Path -LiteralPath (Join-Path $workerHome 'state.json'))) { Invoke-Worker 'adopt' }
        if ($Action -eq 'Prepare') { Write-Output 'Worker prepared and live deployment adopted; no task registered.'; break }
        $start = (Get-Date).AddMinutes(2).ToString('s')
        $program = [Security.SecurityElement]::Escape($pythonw)
        $arguments = [Security.SecurityElement]::Escape(('"{0}" --config "{1}" run' -f (Join-Path $snapshot 'scripts/deploy_worker.py'), $configPath))
        $directory = [Security.SecurityElement]::Escape($snapshot)
        $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Checks origin/main every two minutes; serial, verified Docker deployments under the Docker-owning user.</Description></RegistrationInfo>
  <Triggers>
    <TimeTrigger><Repetition><Interval>PT2M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>$start</StartBoundary><Enabled>true</Enabled></TimeTrigger>
    <LogonTrigger><Enabled>true</Enabled><UserId>$sid</UserId><Delay>PT15S</Delay></LogonTrigger>
  </Triggers>
  <Principals><Principal id="Owner"><UserId>$sid</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>false</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><Enabled>true</Enabled><Hidden>false</Hidden><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT0S</ExecutionTimeLimit></Settings>
  <Actions Context="Owner"><Exec><Command>$program</Command><Arguments>$arguments</Arguments><WorkingDirectory>$directory</WorkingDirectory></Exec></Actions>
</Task>
"@
        Register-ScheduledTask -TaskName $taskName -Xml $xml -Force | Select-Object TaskName,State
        Write-Output 'Installed. Task uses pythonw.exe and runs only while its owner is signed in. No password was stored.'
    }
    'Status' {
        Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State,Principal,Actions,Triggers
        Get-ScheduledTaskInfo -TaskName $taskName | Select-Object LastRunTime,LastTaskResult,NextRunTime
        Invoke-Worker 'status'
    }
    'Verify' {
        $task = Get-ScheduledTask -TaskName $taskName
        $currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $taskSid = $task.Principal.UserId
        if (-not $taskSid.StartsWith('S-1-')) { $taskSid = ([Security.Principal.NTAccount]::new($taskSid)).Translate([Security.Principal.SecurityIdentifier]).Value }
        if ($taskSid -ne $currentSid) { throw 'Task belongs to a different Windows user.' }
        if ($task.Principal.LogonType -ne 'Interactive' -and $task.Principal.LogonType -ne 'InteractiveToken') { throw 'Unexpected task identity mode.' }
        if ($task.Settings.MultipleInstances -ne 'IgnoreNew') { throw 'Unexpected overlapping-instance policy.' }
        if (-not ($task.Actions.Execute -like '*pythonw.exe')) { throw 'Task must run without a console window.' }
        if ($task.Actions.WorkingDirectory -ne $snapshot) { throw 'Unexpected working directory.' }
        $timers = @($task.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskTimeTrigger' -and $_.Repetition.Interval -eq 'PT2M' })
        $logons = @($task.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger' })
        if ($timers.Count -ne 1 -or $logons.Count -ne 1) { throw 'Expected two-minute and sign-in triggers.' }
        $requestedAt = Get-Date
        Start-ScheduledTask -TaskName $taskName
        $deadline = (Get-Date).AddSeconds(50)
        do { Start-Sleep -Seconds 2; $task = Get-ScheduledTask -TaskName $taskName } while ($task.State -eq 'Running' -and (Get-Date) -lt $deadline)
        $info = Get-ScheduledTaskInfo -TaskName $taskName
        $info | Select-Object LastRunTime,LastTaskResult,NextRunTime
        if ($info.LastRunTime -lt $requestedAt.AddSeconds(-2)) { throw 'Task has not completed a new requested run.' }
        if ($task.State -eq 'Running') { Write-Output 'Worker is still active; it has not been interrupted.' }
        elseif ($info.LastTaskResult -ne 0) { throw 'Scheduled run failed; inspect the worker log.' }
        Invoke-Worker 'status'
    }
    'Pause' { Disable-ScheduledTask -TaskName $taskName | Select-Object TaskName,State; Write-Output 'An active deployment, if any, will finish.' }
    'Resume' { Enable-ScheduledTask -TaskName $taskName | Select-Object TaskName,State; Start-ScheduledTask -TaskName $taskName }
    'Uninstall' {
        if ((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') { throw 'Wait for the active worker to finish before uninstalling.' }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output 'Task removed. Production containers, recovery state, images and logs were retained.'
    }
    'Run' { Invoke-Worker 'run' }
    'Retry' { Invoke-Worker 'retry' }
    'Rollback' { Invoke-Worker 'rollback' }
    'Recover' { Invoke-Worker 'recover' }
    'AcceptRecovery' { Invoke-Worker 'accept-recovery' }
}
