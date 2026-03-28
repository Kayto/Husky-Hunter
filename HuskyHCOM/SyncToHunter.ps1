# =============================================
#  Husky Hunter Dev Sync (Automated)
# =============================================
#  Syncs HSYNC\ with a Husky Hunter using
#  CMDHCOM.EXE commands via DOSBox.
#
#  First run:  Downloads all files from Hunter
#  Normal run: Pushes changes (new/modified/deleted)
#
#  By Kayto 28/03/2026
#  Licensed under the MIT License.
#  See LICENSE file for details.
# =============================================

$ErrorActionPreference = 'Stop'

try {

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$SyncFolder   = Join-Path $ScriptDir 'HSYNC'
$HcomDosDir   = Join-Path $ScriptDir 'hcomw\HCOM.DOS'
$ManifestFile = Join-Path $ScriptDir 'hunter-sync.manifest'
$SettingsFile = Join-Path $ScriptDir 'hcom-settings.ini'
$ConfFile     = Join-Path $ScriptDir 'dosbox-hcom.conf'
$BatchFile    = Join-Path $HcomDosDir '_SYNC.BAT'

# HCOM program files that should never be touched by sync
$ProtectedFiles = @(
    'HCOM.EXE', 'HCOM.CFG', 'HCOM.HLP', 'HCS.COM',
    'CMDHCOM.EXE', 'CMDHCOM.CFG', 'BATHCOM.BAT', 'INSTALL.BAT', 'TEST.BAT',
    '_SYNC.BAT',
    'HUNTER.BIN', 'HAWK.BIN', 'H16FS2.BIN',
    'MDROPHHT.EXE', 'MDROPHHT.INI', 'MDROPPC.EXE', 'MDROPPC.INI',
    'MDROPRPT.EXE', 'MDROPRPT.INI'
)

# =============================================
#  Helper Functions
# =============================================

function Write-Header {
    Clear-Host
    Write-Host ''
    Write-Host '  =============================================' -ForegroundColor Cyan
    Write-Host '   Husky Hunter Dev Sync' -ForegroundColor White
    Write-Host '  =============================================' -ForegroundColor Cyan
    Write-Host ''
}

function Load-Manifest {
    $manifest = @{}
    if (Test-Path $ManifestFile) {
        Get-Content $ManifestFile | ForEach-Object {
            $parts = $_ -split '\|'
            if ($parts.Count -eq 3) {
                $manifest[$parts[0]] = @{
                    Size     = [long]$parts[1]
                    Modified = [datetime]$parts[2]
                }
            }
        }
    }
    return $manifest
}

function Save-Manifest {
    param([hashtable]$Manifest)
    $lines = @()
    foreach ($key in ($Manifest.Keys | Sort-Object)) {
        $entry = $Manifest[$key]
        $lines += "$key|$($entry.Size)|$($entry.Modified.ToString('o'))"
    }
    [System.IO.File]::WriteAllLines($ManifestFile, $lines)
}

function Test-Dos83Name {
    param([string]$Name)
    if ($Name -match '^[A-Za-z0-9!#$%&''()\-@^_`{}~]{1,8}(\.[A-Za-z0-9!#$%&''()\-@^_`{}~]{1,3})?$') {
        return $true
    }
    return $false
}

function Run-CmdHcom {
    # Builds a DOS batch file with CMDHCOM commands, runs it in DOSBox
    param([string[]]$Commands)

    # Write the DOS batch file
    $batchLines = @('@echo off')
    foreach ($cmd in $Commands) {
        $batchLines += "CMDHCOM.EXE $cmd"
        $batchLines += 'if errorlevel 1 echo ERROR: %ERRORLEVEL%'
    }
    $batchLines += 'exit'
    # Join with CR+LF for DOS compatibility
    $batchContent = ($batchLines -join "`r`n") + "`r`n"
    [System.IO.File]::WriteAllText($BatchFile, $batchContent, [System.Text.Encoding]::ASCII)

    # Create a temp DOSBox autoexec that runs our batch
    $tempConf = Join-Path $ScriptDir '_sync_autoexec.conf'
    $autoexec = @"
[autoexec]
mount c "."
c:
cd \hcomw\HCOM.DOS
_SYNC.BAT
exit
"@
    [System.IO.File]::WriteAllText($tempConf, $autoexec)

    # Run DOSBox
    $proc = Start-Process -FilePath $DosBoxPath -ArgumentList "-conf `"$ConfFile`" -conf `"$tempConf`"" -PassThru -Wait

    # Cleanup temp files
    Remove-Item $tempConf -Force -ErrorAction SilentlyContinue
    Remove-Item $BatchFile -Force -ErrorAction SilentlyContinue

    return $proc.ExitCode
}

# =============================================
#  Main
# =============================================

Write-Header

Write-Host '  WARNING: This tool modifies files on your Husky' -ForegroundColor Red
Write-Host '  device. Back up important data before syncing.' -ForegroundColor Red
Write-Host '  Use at your own risk — no warranty provided.' -ForegroundColor Red
Write-Host ''

# --- Check prerequisites ---
if (-not (Test-Path $HcomDosDir)) {
    Write-Host '  ERROR: hcomw\HCOM.DOS folder not found.' -ForegroundColor Red
    Write-Host '  Please extract hcomw.zip into this folder.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}

if (-not (Test-Path $SettingsFile)) {
    Write-Host '  ERROR: No settings found.' -ForegroundColor Red
    Write-Host '  Run LaunchHCOM.bat first to configure.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}

if (-not (Test-Path $ConfFile)) {
    Write-Host '  ERROR: dosbox-hcom.conf not found.' -ForegroundColor Red
    Write-Host '  Run LaunchHCOM.bat first to configure.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}

# --- Create sync folder if needed ---
if (-not (Test-Path $SyncFolder)) {
    New-Item -ItemType Directory -Path $SyncFolder | Out-Null
}

# --- Read DOSBox path from settings ---
$DosBoxPath = ''
Get-Content $SettingsFile | ForEach-Object {
    if ($_ -match '^DosBoxPath=(.+)$') { $DosBoxPath = $Matches[1] }
}

if (-not $DosBoxPath -or -not (Test-Path $DosBoxPath)) {
    Write-Host '  ERROR: DOSBox path not found in settings.' -ForegroundColor Red
    Write-Host '  Run LaunchHCOM.bat --setup to reconfigure.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}

# --- Snapshot HCOM.DOS before any operations ---
$hcomFilesBefore = @{}
Get-ChildItem -Path $HcomDosDir -File | ForEach-Object {
    $hcomFilesBefore[$_.Name.ToUpper()] = $_.Length
}

# =============================================
#  First-Run: Download from Hunter via CMDHCOM
# =============================================

$isFirstRun = (-not (Test-Path $ManifestFile)) -and
              ((Get-ChildItem -Path $SyncFolder -File -ErrorAction SilentlyContinue).Count -eq 0)

if ($isFirstRun) {
    Write-Host '  FIRST-TIME SYNC' -ForegroundColor Green
    Write-Host '  =============================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  HSYNC\ is empty and no sync history exists.' -ForegroundColor Gray
    Write-Host '  This will download all files from the Hunter' -ForegroundColor Gray
    Write-Host '  to establish a baseline for change tracking.' -ForegroundColor Gray
    Write-Host ''
    Write-Host '  Make sure the Hunter is connected, powered on,' -ForegroundColor White
    Write-Host '  and running HCOM.' -ForegroundColor White
    Write-Host ''
    Write-Host '  =============================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  Download all files from Hunter? (Y/N) ' -ForegroundColor Yellow -NoNewline
    $answer = Read-Host
    if ($answer -notmatch '^[Yy]') {
        Write-Host ''
        Write-Host '  Cancelled.' -ForegroundColor Gray
        exit 0
    }

    Write-Host ''
    Write-Host '  Downloading from Hunter via CMDHCOM /RX=*.*' -ForegroundColor Cyan
    Write-Host '  (DOSBox will open briefly)...' -ForegroundColor Gray
    Write-Host ''

    # --- Run CMDHCOM /RX=*.* ---
    Run-CmdHcom @('/RX=*.*')

    Write-Header

    # --- Scan HCOM.DOS for newly downloaded files ---
    $downloaded = @()
    Get-ChildItem -Path $HcomDosDir -File | ForEach-Object {
        $name = $_.Name.ToUpper()
        if ($ProtectedFiles -notcontains $name) {
            if (-not $hcomFilesBefore.ContainsKey($name)) {
                $downloaded += $_
            }
            elseif ($_.Length -ne $hcomFilesBefore[$name]) {
                $downloaded += $_
            }
        }
    }

    if ($downloaded.Count -eq 0) {
        Write-Host '  No files were received from the Hunter.' -ForegroundColor Yellow
        Write-Host ''
        Write-Host '  Check that:' -ForegroundColor Gray
        Write-Host '    - The Hunter is connected and running HCOM' -ForegroundColor Gray
        Write-Host '    - The serial cable is plugged in' -ForegroundColor Gray
        Write-Host '    - The COM port is correct (run LaunchHCOM.bat --setup)' -ForegroundColor Gray
        Write-Host ''
        Read-Host '  Press Enter to exit'
        exit 0
    }

    Write-Host "  Received $($downloaded.Count) file(s) from Hunter:" -ForegroundColor Green
    Write-Host ''
    foreach ($file in $downloaded) {
        Write-Host "    $($file.Name)  ($($file.Length) bytes)" -ForegroundColor Green
    }
    Write-Host ''

    # --- Move to HSYNC and create manifest ---
    $newManifest = @{}
    foreach ($file in $downloaded) {
        $dst = Join-Path $SyncFolder $file.Name
        Move-Item -Path $file.FullName -Destination $dst -Force
        $movedFile = Get-Item $dst
        $newManifest[$file.Name.ToUpper()] = @{
            Size     = $movedFile.Length
            Modified = $movedFile.LastWriteTime
        }
    }
    Save-Manifest $newManifest

    Write-Host "  $($downloaded.Count) file(s) saved to HSYNC\" -ForegroundColor Green
    Write-Host '  Sync manifest created. Baseline established.' -ForegroundColor Green
    Write-Host ''
    Write-Host '  You can now edit files in HSYNC\ and run' -ForegroundColor Gray
    Write-Host '  SyncToHunter.bat again to push changes.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 0
}

# =============================================
#  Normal Sync: Push changes to Hunter
# =============================================

# --- Scan sync folder ---
$devFiles = @{}
Get-ChildItem -Path $SyncFolder -File | ForEach-Object {
    $devFiles[$_.Name.ToUpper()] = @{
        FullPath = $_.FullName
        Size     = $_.Length
        Modified = $_.LastWriteTime
    }
}

if ($devFiles.Count -eq 0) {
    Write-Host '  HSYNC\ folder is empty.' -ForegroundColor Yellow
    Write-Host '  Place your files in it, then run again.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 0
}

# --- Check for non-8.3 filenames ---
$badNames = @()
foreach ($name in $devFiles.Keys) {
    if (-not (Test-Dos83Name $name)) {
        $badNames += $name
    }
}
if ($badNames.Count -gt 0) {
    Write-Host '  WARNING: These filenames are not DOS 8.3 compatible:' -ForegroundColor Red
    foreach ($name in $badNames) {
        Write-Host "    $name" -ForegroundColor Yellow
    }
    Write-Host ''
    Write-Host '  The Hunter uses DOS filenames (max 8 chars + 3 char extension).' -ForegroundColor Gray
    Write-Host '  Rename these files before syncing.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}

# --- Check for protected filename conflicts ---
$conflicts = @()
foreach ($name in $devFiles.Keys) {
    if ($ProtectedFiles -contains $name) {
        $conflicts += $name
    }
}
if ($conflicts.Count -gt 0) {
    Write-Host '  ERROR: These files conflict with HCOM program files:' -ForegroundColor Red
    foreach ($name in $conflicts) {
        Write-Host "    $name" -ForegroundColor Yellow
    }
    Write-Host ''
    Write-Host '  Rename them to avoid overwriting HCOM.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}

# --- Load last-sync manifest ---
$manifest = Load-Manifest

# --- Compare ---
$newFiles       = @()
$modifiedFiles  = @()
$deletedFiles   = @()
$unchangedFiles = @()

foreach ($name in ($devFiles.Keys | Sort-Object)) {
    $dev = $devFiles[$name]
    if (-not $manifest.ContainsKey($name)) {
        $newFiles += $name
    }
    elseif ($dev.Size -ne $manifest[$name].Size -or $dev.Modified -gt $manifest[$name].Modified) {
        $modifiedFiles += $name
    }
    else {
        $unchangedFiles += $name
    }
}

foreach ($name in ($manifest.Keys | Sort-Object)) {
    if (-not $devFiles.ContainsKey($name)) {
        $deletedFiles += $name
    }
}

$totalChanges = $newFiles.Count + $modifiedFiles.Count + $deletedFiles.Count

# --- Display summary ---
Write-Host "  Sync folder: HSYNC\ ($($devFiles.Count) files)" -ForegroundColor Gray
Write-Host "  Last synced: $($manifest.Count) files" -ForegroundColor Gray
Write-Host ''

if ($totalChanges -eq 0) {
    Write-Host '  No changes detected. Everything is up to date.' -ForegroundColor Green
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 0
}

if ($newFiles.Count -gt 0) {
    Write-Host "  NEW - will upload ($($newFiles.Count)):" -ForegroundColor Green
    foreach ($name in $newFiles) {
        $size = $devFiles[$name].Size
        Write-Host "    + $name  ($size bytes)" -ForegroundColor Green
    }
    Write-Host ''
}

if ($modifiedFiles.Count -gt 0) {
    Write-Host "  MODIFIED - will delete old + upload new ($($modifiedFiles.Count)):" -ForegroundColor Yellow
    foreach ($name in $modifiedFiles) {
        $size = $devFiles[$name].Size
        Write-Host "    ~ $name  ($size bytes)" -ForegroundColor Yellow
    }
    Write-Host ''
}

if ($deletedFiles.Count -gt 0) {
    Write-Host "  REMOVED from HSYNC\ ($($deletedFiles.Count)):" -ForegroundColor Red
    Write-Host '  Choose per file: D=Delete from Hunter, R=Re-download, S=Skip' -ForegroundColor Gray
    Write-Host ''
    $deleteFromHunter = @()
    $redownloadFiles  = @()
    $skipFiles        = @()
    foreach ($name in $deletedFiles) {
        Write-Host "    - $name  " -ForegroundColor Red -NoNewline
        Write-Host '(D/R/S) ' -ForegroundColor Yellow -NoNewline
        $choice = Read-Host
        switch -Regex ($choice) {
            '^[Dd]' { $deleteFromHunter += $name; Write-Host "      -> Delete from Hunter" -ForegroundColor Red }
            '^[Rr]' { $redownloadFiles  += $name; Write-Host "      -> Re-download to HSYNC\" -ForegroundColor Cyan }
            default { $skipFiles        += $name; Write-Host "      -> Skip (removed from manifest)" -ForegroundColor DarkGray }
        }
    }
    Write-Host ''
}

if ($unchangedFiles.Count -gt 0) {
    Write-Host "  Unchanged: $($unchangedFiles.Count) file(s)" -ForegroundColor DarkGray
    Write-Host ''
}

Write-Host '  =============================================' -ForegroundColor Cyan
$delCount = if ($deletedFiles.Count -gt 0) { $deleteFromHunter.Count } else { 0 }
$dlCount  = if ($deletedFiles.Count -gt 0) { $redownloadFiles.Count } else { 0 }
Write-Host "  $($newFiles.Count) new, $($modifiedFiles.Count) modified, $delCount delete, $dlCount re-download" -ForegroundColor White
Write-Host '  =============================================' -ForegroundColor Cyan
Write-Host ''

# --- Confirm ---
Write-Host '  Sync these changes to Hunter? (Y/N) ' -ForegroundColor Yellow -NoNewline
$answer = Read-Host
if ($answer -notmatch '^[Yy]') {
    Write-Host ''
    Write-Host '  Cancelled.' -ForegroundColor Gray
    exit 0
}

# --- Build CMDHCOM command list ---
Write-Host ''
$commands = @()

# Delete files the user chose to remove from Hunter
if ($deleteFromHunter.Count -gt 0) {
    foreach ($name in $deleteFromHunter) {
        $commands += "/DEL=$name"
        Write-Host "  Queued: DEL $name" -ForegroundColor Red
    }
}

# Delete then re-upload modified files
foreach ($name in $modifiedFiles) {
    $commands += "/DEL=$name"
    Write-Host "  Queued: DEL $name (old version)" -ForegroundColor Yellow
}
foreach ($name in $modifiedFiles) {
    $commands += "/TX=$name"
    Write-Host "  Queued: TX  $name (new version)" -ForegroundColor Yellow
}

# Upload new files
foreach ($name in $newFiles) {
    $commands += "/TX=$name"
    Write-Host "  Queued: TX  $name" -ForegroundColor Green
}

# Re-download files from Hunter
if ($redownloadFiles.Count -gt 0) {
    foreach ($name in $redownloadFiles) {
        $commands += "/RX=$name"
        Write-Host "  Queued: RX  $name" -ForegroundColor Cyan
    }
}

# --- Stage files that need uploading into HCOM.DOS ---
$filesToUpload = $newFiles + $modifiedFiles
foreach ($name in $filesToUpload) {
    $src = $devFiles[$name].FullPath
    $dst = Join-Path $HcomDosDir $name
    Copy-Item -Path $src -Destination $dst -Force
}

if ($commands.Count -eq 0) {
    Write-Host '  No commands to run.' -ForegroundColor Gray
}
else {
    Write-Host ''
    Write-Host "  Running $($commands.Count) CMDHCOM command(s)..." -ForegroundColor Cyan
    Write-Host '  (DOSBox will open briefly)' -ForegroundColor Gray
    Write-Host ''

    # --- Execute ---
    Run-CmdHcom $commands
}

Write-Header

Write-Host '  Sync complete.' -ForegroundColor Green
Write-Host ''

# --- Move re-downloaded files from HCOM.DOS to HSYNC ---
if ($redownloadFiles.Count -gt 0) {
    foreach ($name in $redownloadFiles) {
        $src = Join-Path $HcomDosDir $name
        if (Test-Path $src) {
            $dst = Join-Path $SyncFolder $name
            Move-Item -Path $src -Destination $dst -Force
            $movedFile = Get-Item $dst
            $devFiles[$name] = @{
                FullPath = $movedFile.FullName
                Size     = $movedFile.Length
                Modified = $movedFile.LastWriteTime
            }
            Write-Host "  Re-downloaded: $name ($($movedFile.Length) bytes)" -ForegroundColor Cyan
        }
        else {
            Write-Host "  WARNING: $name not received from Hunter" -ForegroundColor Yellow
        }
    }
    Write-Host ''
}

# --- Update manifest ---
$newManifest = @{}
foreach ($name in $devFiles.Keys) {
    $dev = $devFiles[$name]
    $newManifest[$name] = @{
        Size     = $dev.Size
        Modified = $dev.Modified
    }
}
Save-Manifest $newManifest
Write-Host '  Manifest updated.' -ForegroundColor Gray

# --- Clean staged files from HCOM.DOS ---
$cleaned = 0
foreach ($name in $filesToUpload) {
    $staged = Join-Path $HcomDosDir $name
    if (Test-Path $staged) {
        Remove-Item $staged -Force
        $cleaned++
    }
}
if ($cleaned -gt 0) {
    Write-Host "  Cleaned $cleaned staged file(s) from hcomw\HCOM.DOS\" -ForegroundColor Gray
}

Write-Host ''
Write-Host '  Done.' -ForegroundColor Cyan
Write-Host ''
Read-Host '  Press Enter to exit'

} catch {
    Write-Host ''
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host ''
    Read-Host '  Press Enter to exit'
    exit 1
}
