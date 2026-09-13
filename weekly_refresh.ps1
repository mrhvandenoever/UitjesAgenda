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
    Add-Content -Path $logFile -Value $line -Encoding utf8
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

    # BUG (gevonden 2026-09-13, decisions.md): git push/commit schrijven hun
    # normale voortgangsregels ("To https://...", branch-tracking-info) naar
    # STDERR -- standaardgedrag, geen fout. Onder $ErrorActionPreference =
    # 'Stop' laat een 2>&1-merge zo'n normale regel PowerShell alsnog een
    # terminating exception gooien, ook al slaagt de push zelf gewoon (5
    # nachten lang kwam de commit wél op GitHub aan, maar meldde het
    # script steeds "FOUT tijdens git push"). Fix: ErrorActionPreference
    # lokaal op 'Continue' zetten zodat de stderr-regels als gewone
    # dataregels door de pipeline stromen, en de ECHTE success/fail-status
    # aflezen via $LASTEXITCODE (git's eigen exitcode) i.p.v. op een
    # exception te vertrouwen.
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    git push 2>&1 | ForEach-Object { Log $_ }
    $pushExitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP

    if ($pushExitCode -ne 0) {
        Log "FOUT tijdens git push (exitcode $pushExitCode)"
        Log "=== Einde (met fout) ==="
        exit 1
    }
    Log "Gepusht naar origin/main."
}

Log "=== Einde weekly refresh ==="
