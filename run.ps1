param(
    [string]$Workbook = "outputs\01a05ca8-e128-7ef2-9f03-59f0cd18a688\anonymized_schedule_example.xlsx",
    [string]$PythonExe = "",
    [string]$Subject = "PHYSIQUE-CHIMIE"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$WorkbookPath = Join-Path $ProjectRoot $Workbook
$Output = Join-Path $ProjectRoot "output"

if (!(Test-Path -LiteralPath $WorkbookPath)) {
    throw "Fichier Excel introuvable : $WorkbookPath"
}
if (!(Test-Path -LiteralPath $Python)) {
    if ($PythonExe) {
        & $PythonExe -m venv (Join-Path $ProjectRoot ".venv")
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.11 -m venv (Join-Path $ProjectRoot ".venv")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m venv (Join-Path $ProjectRoot ".venv")
    } else {
        throw "Python 3.11+ n'est pas installé ou visible dans Windows."
    }
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $Python)) {
        throw "Impossible de créer l'environnement Python. Réinstaller Python en cochant 'Add Python to PATH'."
    }
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& $Python -m schedule_repair.cli $WorkbookPath --output (Join-Path $Output "import.json")
if ($LASTEXITCODE -ne 0) { throw "Corriger les erreurs d'import dans output/import.json" }

& $Python -m schedule_repair.analyze_cli $WorkbookPath --output (Join-Path $Output "deduced_constraints.md")
& $Python -m schedule_repair.optimize_cli $WorkbookPath `
    --subject $Subject `
    --constraints (Join-Path $ProjectRoot "config\constraints.example.json") `
    --output (Join-Path $Output "suggested_iterations.md") `
    --exceptions (Join-Path $Output "constraint_exceptions.md") `
    --teacher-changes (Join-Path $Output "teacher_schedule_changes.md") `
    --json (Join-Path $Output "suggested_iterations.json")

if ($LASTEXITCODE -eq 3) {
    Write-Host "Analyse terminée : optimisation bloquée, voir output/suggested_iterations.md"
    exit 0
}
if ($LASTEXITCODE -ne 0) { throw "Échec de l'optimisation" }
Write-Host "Terminé : voir le dossier output"
