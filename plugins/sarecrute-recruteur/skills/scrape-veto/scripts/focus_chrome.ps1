# Ramène la fenêtre Chrome au premier plan (Windows).
#
#   powershell -ExecutionPolicy Bypass -File focus_chrome.ps1 [-TitleFragment "Vétérinaire"]
#
# Pourquoi : fenêtre Chrome masquée ou minimisée = requestAnimationFrame suspendu
# et timers bridés, donc le fil Facebook cesse de charger sans message d'erreur.
#
# Limite connue vs macOS : sous Windows on ne peut pas sélectionner un onglet
# Chrome depuis le shell. Le titre de la fenêtre est celui de l'onglet ACTIF ;
# ce script ne peut donc que dé-minimiser et activer la fenêtre. Si l'onglet du
# scrape n'est pas l'onglet actif, il reste occulté : le script le dit, et c'est
# à l'utilisateur de cliquer sur le bon onglet.

param(
    [string]$TitleFragment = ''
)

$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Win {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
'@

$procs = Get-Process chrome -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowHandle -ne 0 }

if (-not $procs) {
    Write-Error "Aucune fenêtre Chrome ouverte."
    exit 1
}

$target = $procs | Select-Object -First 1
if ($TitleFragment) {
    $match = $procs | Where-Object { $_.MainWindowTitle -like "*$TitleFragment*" } | Select-Object -First 1
    if ($match) {
        $target = $match
    } else {
        Write-Output "Aucune fenêtre Chrome dont l'onglet actif contient « $TitleFragment » : l'onglet du scrape n'est probablement pas au premier plan de sa fenêtre. Activation de la fenêtre quand même — demande à l'utilisateur de cliquer sur l'onglet du groupe."
    }
}

$h = $target.MainWindowHandle
if ([Win]::IsIconic($h)) { [Win]::ShowWindow($h, 9) | Out-Null }  # 9 = SW_RESTORE
[Win]::SetForegroundWindow($h) | Out-Null

Start-Sleep -Seconds 1
Write-Output "Fenêtre Chrome au premier plan (onglet actif : $($target.MainWindowTitle))"
