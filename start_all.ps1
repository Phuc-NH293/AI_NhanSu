param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $Root "frontend"
$LogDir = Join-Path ([System.IO.Path]::GetTempPath()) "day08-rag-pipeline"
$BackendPort = 8001
$FrontendPort = 5173
$FrontendFallbackPorts = 5174..5178

function Test-PythonInterpreter {
    param([string]$Executable)

    if ([string]::IsNullOrWhiteSpace($Executable)) {
        return $false
    }

    if (($Executable -ne "python") -and !(Test-Path -LiteralPath $Executable)) {
        return $false
    }

    $oldErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Executable -c "import sys; print(sys.executable)" *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
    finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
}

function Find-PythonInterpreter {
    $candidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $Root "venv\Scripts\python.exe"),
        "python"
    )

    foreach ($candidate in $candidates) {
        if (Test-PythonInterpreter -Executable $candidate) {
            return $candidate
        }
    }

    return $null
}

$Python = Find-PythonInterpreter
if ($null -eq $Python) {
    Write-Host ""
    Write-Host "No working Python interpreter was found." -ForegroundColor Red
    Write-Host "The existing .\venv is broken because its base Python was removed."
    Write-Host "Install Python 3.12, then recreate the environment:"
    Write-Host "  py -3.12 -m venv .venv"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\start_all.ps1 -Install"
    exit 1
}

function Stop-AppJobs {
    Get-Job -Name "rag-backend", "rag-frontend" -ErrorAction SilentlyContinue | Stop-Job
    Get-Job -Name "rag-backend", "rag-frontend" -ErrorAction SilentlyContinue | Remove-Job -Force
}

function Stop-AppProcess {
    param($Process)
    if ($null -ne $Process) {
        try {
            $Process.Refresh()
            if (-not $Process.HasExited) {
                Stop-Process -Id $Process.Id -Force
            }
        }
        catch {
            # Process is already gone.
        }
    }
}

function Stop-PortListeners {
    param([int[]]$Ports)

    $processIds = @()
    foreach ($port in $Ports) {
        $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($listener in $listeners) {
            if ($listener.OwningProcess -gt 0) {
                $processIds += $listener.OwningProcess
            }
        }
    }

    $processIds = $processIds | Sort-Object -Unique
    foreach ($processId in $processIds) {
        try {
            $process = Get-Process -Id $processId -ErrorAction Stop
            Write-Host "Stopping existing server process PID $processId ($($process.ProcessName))..."
            Stop-Process -Id $processId -Force
        }
        catch {
            # Process is already gone or no longer accessible.
        }
    }

    Start-Sleep -Milliseconds 500
}

Set-Location $Root
Stop-AppJobs
$PortsToClean = @($BackendPort, $FrontendPort) + $FrontendFallbackPorts
Stop-PortListeners -Ports $PortsToClean
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if ($Install) {
    Write-Host "Installing backend dependencies..."
    & $Python -m pip install --timeout 300 --retries 10 fastapi uvicorn python-multipart python-dotenv requests beautifulsoup4 rank-bm25 openai pydantic pypdf pdfplumber PyMuPDF langgraph "markitdown[pdf]"

    Write-Host "Installing frontend dependencies..."
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

Write-Host "Checking backend dependencies..."
$DependencyCheck = @'
import importlib

modules = ['fastapi', 'uvicorn', 'dotenv', 'rank_bm25', 'openai', 'pypdf', 'pdfplumber', 'langgraph']
failures = []
for module in modules:
    try:
        importlib.import_module(module)
    except Exception as exc:
        failures.append(f'{module}: {type(exc).__name__}: {exc}')

if failures:
    print('\n'.join(failures))
    raise SystemExit(1)
'@

$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$dependencyErrors = & $Python -c $DependencyCheck 2>&1
$dependencyExitCode = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference

if ($dependencyExitCode -ne 0) {
    Write-Host ""
    Write-Host "Backend dependency check failed:" -ForegroundColor Red
    $dependencyErrors | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\start_all.ps1 -Install"
    exit 1
}

if (!(Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host ""
    Write-Host "Missing frontend dependencies."
    Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\start_all.ps1 -Install"
    exit 1
}

Write-Host "Starting backend on http://127.0.0.1:$BackendPort ..."
$backendOut = Join-Path $LogDir "backend.out.log"
$backendErr = Join-Path $LogDir "backend.err.log"
$backendProcess = Start-Process `
    -FilePath $Python `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "$BackendPort", "--reload") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Starting frontend on http://127.0.0.1:$FrontendPort ..."
$frontendOut = Join-Path $LogDir "frontend.out.log"
$frontendErr = Join-Path $LogDir "frontend.err.log"
$frontendProcess = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort") `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -WindowStyle Hidden `
    -PassThru

Write-Host ""
Write-Host "App is starting:"
Write-Host "  Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "  Backend:  http://127.0.0.1:$BackendPort/docs"
Write-Host "  Logs:     $LogDir"
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers."

try {
    while ($true) {
        Start-Sleep -Seconds 2

        $backendProcess.Refresh()
        $frontendProcess.Refresh()

        if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
            Write-Host ""
            Write-Host "One server stopped."
            Write-Host "Backend logs:  $backendOut"
            Write-Host "Backend err:   $backendErr"
            Write-Host "Frontend logs: $frontendOut"
            Write-Host "Frontend err:  $frontendErr"
            exit 1
        }
    }
}
finally {
    Stop-AppProcess $backendProcess
    Stop-AppProcess $frontendProcess
    Write-Host "Stopped backend and frontend."
}
