# Joint une image au composeur Facebook déjà ouvert, par le presse-papiers Windows.
#
#   powershell -sta -ExecutionPolicy Bypass -File attach_image.ps1 `
#       -TitleFragment "Vétérinaire Emploi" -ImagePath "C:\...\image.png"
#
# Le composeur doit être ouvert ET le curseur déjà placé dans la zone de texte.
# -sta est obligatoire : Clipboard::SetImage refuse de tourner en MTA.
#
# Limite connue vs macOS : sous Windows on ne peut pas sélectionner un onglet
# Chrome depuis le shell. Le titre de la fenêtre Chrome est celui de l'onglet
# ACTIF ; si l'onglet cible n'est pas au premier plan, le script s'arrête au
# lieu de coller au mauvais endroit.

param(
    [Parameter(Mandatory = $true)][string]$TitleFragment,
    [Parameter(Mandatory = $true)][string]$ImagePath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ImagePath)) {
    Write-Error "Image introuvable : $ImagePath"
    exit 1
}

if ([Threading.Thread]::CurrentThread.GetApartmentState() -ne 'STA') {
    Write-Error "Relance avec powershell -sta : SetImage exige un thread STA."
    exit 1
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# SetImage passe par un bitmap DIB : la transparence PNG est perdue (sans
# incidence sur des visuels pleins), les pixels eux-mêmes ne sont pas recompressés.
$img = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $ImagePath))
try {
    [System.Windows.Forms.Clipboard]::SetImage($img)
} finally {
    $img.Dispose()
}

$chrome = Get-Process -Name chrome -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -like "*$TitleFragment*" } |
    Select-Object -First 1

if (-not $chrome) {
    Write-Error "Aucune fenêtre Chrome dont l'onglet actif contient : $TitleFragment. Mets l'onglet au premier plan puis relance."
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
# Deux tentatives : Windows refuse parfois le premier passage au premier plan.
if (-not $shell.AppActivate($chrome.Id)) {
    Start-Sleep -Milliseconds 300
    if (-not $shell.AppActivate($chrome.Id)) {
        Write-Error "Impossible de mettre la fenêtre Chrome au premier plan."
        exit 1
    }
}

Start-Sleep -Seconds 1
$shell.SendKeys('^v')

# Facebook met quelques secondes à téléverser et afficher la vignette.
Start-Sleep -Seconds 4
Write-Output "Collé dans la fenêtre Chrome : $TitleFragment"
