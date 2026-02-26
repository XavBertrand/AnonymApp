Param(
    [string]$PythonExe = "python",
    [string]$OutDir = "dist"
)

$ErrorActionPreference = "Stop"

Write-Host "Building Windows executable with PyInstaller..."
& $PythonExe -m pip install pyinstaller
& $PythonExe -m PyInstaller --onefile --name anonymizer --distpath $OutDir -m anonymizer_core.cli

Write-Host "Build done. Executable available in $OutDir"
