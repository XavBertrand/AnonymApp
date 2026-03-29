param(
    [string]$PythonExe = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-PythonCommand {
    param(
        [string]$Executable,
        [string[]]$Arguments = @()
    )

    return [pscustomobject]@{
        Executable = $Executable
        Arguments  = $Arguments
    }
}

function Resolve-PythonCommand {
    param(
        [string]$RootPath,
        [string]$ExplicitPythonExe = ""
    )

    if ($ExplicitPythonExe) {
        if (-not (Test-Path $ExplicitPythonExe)) {
            throw "The provided Python executable was not found: $ExplicitPythonExe"
        }
        return New-PythonCommand -Executable (Resolve-Path $ExplicitPythonExe).Path
    }

    $venvPython = Join-Path $RootPath ".venv-windows-build\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return New-PythonCommand -Executable $venvPython
    }

    if ($env:CONDA_PREFIX) {
        $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
        if (Test-Path $condaPython) {
            return New-PythonCommand -Executable $condaPython
        }
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return New-PythonCommand -Executable $python.Source
    }

    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        return New-PythonCommand -Executable $py.Source -Arguments @("-3.11")
    }

    throw "Python 3.11 was not found. Activate your Windows env first, pass -PythonExe, or create .venv-windows-build."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        $Command,
        [string[]]$ExtraArgs = @()
    )

    & $Command.Executable @($Command.Arguments + $ExtraArgs)
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptRoot "..\..")
Set-Location $RepoRoot

$PythonCommand = Resolve-PythonCommand -RootPath $RepoRoot -ExplicitPythonExe $PythonExe

Write-Host "Using Python: $($PythonCommand.Executable)"
if ($PythonCommand.Arguments.Count -gt 0) {
    Write-Host "Python arguments: $($PythonCommand.Arguments -join ' ')"
}

Write-Host "Verifying staged release layout..."
Invoke-Python -Command $PythonCommand -ExtraArgs @("scripts/packaging/verify_staged_release.py", ".")

if (-not (Test-Path ".venv-windows-build\Scripts\python.exe")) {
    Write-Host "Creating .venv-windows-build..."
    Invoke-Python -Command $PythonCommand -ExtraArgs @("-m", "venv", ".venv-windows-build")
}

$BuildPython = New-PythonCommand -Executable (Join-Path $RepoRoot ".venv-windows-build\Scripts\python.exe")
if (-not (Test-Path $BuildPython.Executable)) {
    throw "Build venv python not found: $($BuildPython.Executable)"
}

Invoke-Python -Command $BuildPython -ExtraArgs @("-m", "pip", "install", "--upgrade", "pip")
if (Test-Path "requirements-windows.txt") {
    Write-Host "Installing Windows build requirements from requirements-windows.txt..."
    Invoke-Python -Command $BuildPython -ExtraArgs @("-m", "pip", "install", "-r", "requirements-windows.txt")
}
else {
    Write-Host "requirements-windows.txt not found, falling back to editable install + PyInstaller..."
    Invoke-Python -Command $BuildPython -ExtraArgs @("-m", "pip", "install", "-e", ".")
    Invoke-Python -Command $BuildPython -ExtraArgs @("-m", "pip", "install", "PyInstaller")
}

Write-Host "Building portable desktop bundle..."
Invoke-Python -Command $BuildPython -ExtraArgs @(
    "-m",
    "PyInstaller",
    "scripts/packaging/a4_desktop.spec",
    "--noconfirm"
)

$OutputPath = Resolve-Path "dist\a4_desktop_portable"
$ExecutablePath = Join-Path $OutputPath "A4Desktop.exe"
if (-not (Test-Path $ExecutablePath)) {
    throw "Portable executable not found after build: $ExecutablePath"
}

Write-Host "Bundled runtime DLLs:"
Invoke-Python -Command $BuildPython -ExtraArgs @(
    "-c",
    "from pathlib import Path; from scripts.packaging.build_windows_portable import portable_runtime_binaries_report; [print(item) for item in portable_runtime_binaries_report(Path.cwd())]"
)

Write-Host "Portable bundle ready at: $OutputPath"
Write-Host "Executable ready at: $ExecutablePath"
