# weekly_refresh.ps1 — wrapper voor de geplande Windows-taak "uitjes-agenda-refresh"
#
# Draait run_weekly_refresh.py (scrapers + export + gen_uitjes.py) en pusht
# het resultaat naar GitHub, als er iets veranderd is. Geen AI/Claude bij
# betrokken — puur script, bedoeld om via Taakplanner te draaien (dagelijks 04:00,
# was ma/wo/za tot 2026-09-02, zie decisions.md).
#
# Logt naar refresh_log.txt in dezelfde map (append), zodat een gemiste of
# mislukte run achteraf te checken is.

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$logFile = Join-Path $PSScriptRoot 'refresh_log.txt'
function Log($msg) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Add-Content -Path $logFile -Value $line
    Write-Output $line
}

Log "=== Start weekly refresh ==="

try {
    python run_weekly_refresh.py 2>&1 | Tee-Object -Variable refreshOutput | Out-Null
    $refreshOutput | ForEach-Object { Log $_ }
} catch {
    Log "FOUT tijdens run_weekly_refresh.py: $_"
    Log "=== Einde (met fout) ==="
    exit 1
}

# Alleen committen/pushen als er daadwerkelijk iets veranderd is
$changes = git status --porcelain
if ([string]::IsNullOrWhiteSpace($changes)) {
    Log "Geen wijzigingen — niets te committen."
} else {
    git add -A
    git commit -m "auto refresh $(Get-Date -Format 'yyyy-MM-dd')" | ForEach-Object { Log $_ }
    try {
        git push 2>&1 | ForEach-Object { Log $_ }
        Log "Gepusht naar origin/main."
    } catch {
        Log "FOUT tijdens git push: $_"
        Log "=== Einde (met fout) ==="
        exit 1
    }
}

Log "=== Einde weekly refresh ==="
