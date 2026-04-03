# =============================================
#  Husky Hunter Dev Sync (From Hunter)
# =============================================
#  Pulls changes from the Hunter into HSYNC\.
#  Only new or modified files are updated —
#  existing matching files are left untouched.
#
#  By Kayto 02/04/2026
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
    Write-Host '   Husky Hunter Dev Sync (From Hunter)' -ForegroundColor White
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

function Run-CmdHcom {
    param([string[]]$Commands)

    $batchLines = @('@echo off')
    foreach ($cmd in $Commands) {
        $batchLines += "CMDHCOM.EXE $cmd"
        $batchLines += 'if errorlevel 1 echo ERROR: %ERRORLEVEL%'
    }
    $batchLines += 'exit'
    $batchContent = ($batchLines -join "`r`n") + "`r`n"
    [System.IO.File]::WriteAllText($BatchFile, $batchContent, [System.Text.Encoding]::ASCII)

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

    $proc = Start-Process -FilePath $DosBoxPath -ArgumentList "-conf `"$ConfFile`" -conf `"$tempConf`"" -PassThru -Wait

    Remove-Item $tempConf -Force -ErrorAction SilentlyContinue
    Remove-Item $BatchFile -Force -ErrorAction SilentlyContinue

    return $proc.ExitCode
}

# =============================================
#  Main
# =============================================

Write-Header

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

# --- Create sync folder if needed ---
if (-not (Test-Path $SyncFolder)) {
    New-Item -ItemType Directory -Path $SyncFolder | Out-Null
}

$existingCount = @(Get-ChildItem -Path $SyncFolder -File -ErrorAction SilentlyContinue).Count
if ($existingCount -gt 0) {
    Write-Host "  HSYNC\ has $existingCount file(s). Only new or" -ForegroundColor Gray
    Write-Host '  changed files from the Hunter will be updated.' -ForegroundColor Gray
    Write-Host ''
}

# --- Snapshot HCOM.DOS before download ---
$hcomFilesBefore = @{}
Get-ChildItem -Path $HcomDosDir -File | ForEach-Object {
    $hcomFilesBefore[$_.Name.ToUpper()] = @{
        Size     = $_.Length
        Modified = $_.LastWriteTime
    }
}

# --- Confirm download ---
Write-Host '  Make sure the Hunter is connected, powered on,' -ForegroundColor White
Write-Host '  and running HCOM.' -ForegroundColor White
Write-Host ''
Write-Host '  Check Hunter for changes? (Y/N) ' -ForegroundColor Yellow -NoNewline
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
        elseif ($_.Length -ne $hcomFilesBefore[$name].Size -or $_.LastWriteTime -ne $hcomFilesBefore[$name].Modified) {
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

# --- Compare with existing HSYNC files ---
$newFiles     = @()
$updatedFiles = @()
$sameFiles    = @()

foreach ($file in $downloaded) {
    $name = $file.Name.ToUpper()
    $existingPath = Join-Path $SyncFolder $file.Name
    if (-not (Test-Path $existingPath)) {
        $newFiles += $file
    }
    else {
        $existing = Get-Item $existingPath
        if ($file.Length -ne $existing.Length) {
            $updatedFiles += $file
        }
        else {
            # Same size — compare content
            $srcHash = (Get-FileHash -Path $file.FullName -Algorithm MD5).Hash
            $dstHash = (Get-FileHash -Path $existingPath -Algorithm MD5).Hash
            if ($srcHash -ne $dstHash) {
                $updatedFiles += $file
            }
            else {
                $sameFiles += $file
            }
        }
    }
}

# --- Display summary ---
Write-Host "  Received $($downloaded.Count) file(s) from Hunter:" -ForegroundColor Green
Write-Host ''

if ($newFiles.Count -gt 0) {
    Write-Host "  NEW ($($newFiles.Count)):" -ForegroundColor Green
    foreach ($file in $newFiles) {
        Write-Host "    + $($file.Name)  ($($file.Length) bytes)" -ForegroundColor Green
    }
    Write-Host ''
}

if ($updatedFiles.Count -gt 0) {
    Write-Host "  UPDATED ($($updatedFiles.Count)):" -ForegroundColor Yellow
    foreach ($file in $updatedFiles) {
        $existingPath = Join-Path $SyncFolder $file.Name
        $oldSize = (Get-Item $existingPath).Length
        Write-Host "    ~ $($file.Name)  ($oldSize -> $($file.Length) bytes)" -ForegroundColor Yellow
    }
    Write-Host ''
}

if ($sameFiles.Count -gt 0) {
    Write-Host "  Unchanged: $($sameFiles.Count) file(s)" -ForegroundColor DarkGray
    Write-Host ''
}

$changeCount = $newFiles.Count + $updatedFiles.Count

if ($changeCount -eq 0) {
    Write-Host '  No changes from Hunter. Everything is up to date.' -ForegroundColor Green
    Write-Host ''
    # Clean downloaded files from HCOM.DOS
    foreach ($file in $downloaded) {
        $name = $file.Name.ToUpper()
        if (-not $hcomFilesBefore.ContainsKey($name)) {
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    Read-Host '  Press Enter to exit'
    exit 0
}

# --- Move new/updated files to HSYNC ---
Write-Host '  =============================================' -ForegroundColor Cyan
Write-Host "  $($newFiles.Count) new, $($updatedFiles.Count) updated" -ForegroundColor White
Write-Host '  =============================================' -ForegroundColor Cyan
Write-Host ''

foreach ($file in ($newFiles + $updatedFiles)) {
    $dst = Join-Path $SyncFolder $file.Name
    Move-Item -Path $file.FullName -Destination $dst -Force
    Write-Host "  -> $($file.Name)" -ForegroundColor Green
}
Write-Host ''

# Clean unchanged downloaded files from HCOM.DOS
foreach ($file in $sameFiles) {
    $name = $file.Name.ToUpper()
    if (-not $hcomFilesBefore.ContainsKey($name)) {
        Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
    }
}

# --- Update manifest from current HSYNC state ---
$newManifest = @{}
Get-ChildItem -Path $SyncFolder -File | ForEach-Object {
    $newManifest[$_.Name.ToUpper()] = @{
        Size     = $_.Length
        Modified = $_.LastWriteTime
    }
}
Save-Manifest $newManifest

Write-Host '  Manifest updated.' -ForegroundColor Gray
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
