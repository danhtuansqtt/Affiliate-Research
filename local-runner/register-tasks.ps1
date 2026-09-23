# Tao lich chay hang ngay trong Windows Task Scheduler cho 2 luot scout doi agent.
#
# Cach dung (khong can quyen Administrator):
#   powershell -ExecutionPolicy Bypass -File register-tasks.ps1
#   powershell -ExecutionPolicy Bypass -File register-tasks.ps1 -AiTime 08:15 -TaiChinhTime 09:15
# Xoa lich:
#   powershell -ExecutionPolicy Bypass -File register-tasks.ps1 -Remove
#
# Task chay duoi tai khoan Windows hien tai, chi khi ban dang dang nhap.
# Neu may tat/ngu dung gio, task se chay bu ngay khi may bat lai (StartWhenAvailable).

param(
    [string]$AiTime = "08:15",
    [string]$TaiChinhTime = "09:15",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$Runner = Join-Path $PSScriptRoot "run-scout.ps1"
$Tasks = @(
    @{ Name = "Affiliate Scout - AI (doi agent)";        Topic = "ai";        Time = $AiTime },
    @{ Name = "Affiliate Scout - Tai chinh (doi agent)"; Topic = "tai-chinh"; Time = $TaiChinhTime }
)

foreach ($t in $Tasks) {
    $existing = Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false
        Write-Host "Da xoa lich cu: $($t.Name)"
    }
    if ($Remove) { continue }

    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Topic {1}" -f $Runner, $t.Topic) `
        -WorkingDirectory $PSScriptRoot
    $trigger = New-ScheduledTaskTrigger -Daily -At $t.Time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger -Settings $settings `
        -Description "Scout affiliate bang doi agent (repo Affiliate-Research). Log: local-runner\logs" | Out-Null
    Write-Host "Da tao lich: $($t.Name) luc $($t.Time) hang ngay"
}

if (-not $Remove) {
    Write-Host ""
    Write-Host "Kiem tra: mo Task Scheduler (taskschd.msc), hoac chay thu ngay:"
    Write-Host "  Start-ScheduledTask -TaskName `"Affiliate Scout - AI (doi agent)`""
}
