# Chay mot luot scout affiliate bang doi agent tren may nay (Claude Code, che do khong tuong tac).
#
# Cach dung:
#   powershell -ExecutionPolicy Bypass -File run-scout.ps1 -Topic ai
#   powershell -ExecutionPolicy Bypass -File run-scout.ps1 -Topic tai-chinh
# Tham so tuy chon:
#   -Model <ten model>   de trong = model mac dinh cua Claude Code
#   -DryRun              chi in lenh se chay, khong goi Claude
#
# Log ghi vao local-runner\logs\scout-<topic>-<yyyy-MM-dd_HHmm>.log

param(
    [Parameter(Mandatory = $true)][ValidateSet("ai", "tai-chinh")][string]$Topic,
    [string]$Model = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Repo = Split-Path $Here -Parent
$PromptFile = Join-Path $Here "prompts\$Topic.txt"
$LogDir = Join-Path $Here "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir ("scout-{0}-{1}.log" -f $Topic, (Get-Date -Format "yyyy-MM-dd_HHmm"))

function Say($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

if (-not (Test-Path $PromptFile)) { throw "Khong tim thay prompt: $PromptFile" }
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) { throw "Khong tim thay lenh 'claude'. Cai Claude Code va dang nhap truoc." }

# Prompt chi gom ky tu ASCII va khong co dau ngoac kep, nen truyen qua tham so
# an toan tren ca PowerShell 5 lan 7.
$Prompt = Get-Content $PromptFile -Raw
$Tools = "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Skill,TodoWrite"
$ClaudeArgs = @("-p", $Prompt, "--permission-mode", "acceptEdits", "--allowedTools", $Tools)
if ($Model) { $ClaudeArgs += @("--model", $Model) }

Say "Repo: $Repo"
Say "Topic: $Topic | Prompt: $PromptFile | Log: $Log"

if ($DryRun) {
    Say "DRY RUN - lenh se chay: claude -p <prompt $Topic> --permission-mode acceptEdits --allowedTools $Tools $(if ($Model) { "--model $Model" })"
    exit 0
}

Push-Location $Repo
# git/claude ghi tien trinh ra stderr; tren PowerShell 5, muc "Stop" se coi
# do la loi va dung script, nen ha xuong "Continue" cho cac lenh ngoai.
$ErrorActionPreference = "Continue"
try {
    Say "git pull origin master"
    git checkout master 2>&1 | ForEach-Object { Say "  $_" }
    git pull origin master 2>&1 | ForEach-Object { Say "  $_" }

    Say "Bat dau Claude Code..."
    & claude @ClaudeArgs 2>&1 | ForEach-Object { Add-Content -Path $Log -Value $_ -Encoding UTF8; Write-Host $_ }
    $code = $LASTEXITCODE
    Say "Claude Code ket thuc, ma thoat: $code"

    $last = git log -1 --format="%h %s" 2>$null
    Say "Commit moi nhat tren master: $last"
    exit $code
}
finally {
    Pop-Location
}
