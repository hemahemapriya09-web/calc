<#
.SYNOPSIS
    Publishes the calculator on a public HTTPS address straight from this machine.

.DESCRIPTION
    Starts the production WSGI server and opens a Cloudflare quick tunnel to it,
    then waits for the public trycloudflare.com address to appear. No account or
    DNS setup is required. The address is live while this window stays open.

.EXAMPLE
    .\share.ps1
    .\share.ps1 -Port 8080
#>
[CmdletBinding()]
param(
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$ToolsDirectory = Join-Path $PSScriptRoot ".tools"
$CloudflaredPath = Join-Path $ToolsDirectory "cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$Origin = "http://127.0.0.1:$Port"
$HealthUrl = "$Origin/healthz"
$PublicUrlPattern = "https://[a-z0-9-]+\.trycloudflare\.com"

function Test-ServerReady {
    param([int]$TimeoutSeconds = 30)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Get-CloudflaredClient {
    if (Test-Path $CloudflaredPath) {
        return
    }

    New-Item -ItemType Directory -Force -Path $ToolsDirectory | Out-Null
    Write-Host "Downloading the Cloudflare tunnel client (one time)..."
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $CloudflaredPath -UseBasicParsing
}

function Start-CalculatorServer {
    $interpreter = (Get-Command python -ErrorAction Stop).Source
    return Start-Process -FilePath $interpreter `
        -ArgumentList "-m", "waitress", "--listen=127.0.0.1:$Port", "wsgi:app" `
        -PassThru -WindowStyle Hidden
}

$serverProcess = $null

try {
    if (Test-ServerReady -TimeoutSeconds 3) {
        Write-Host "Reusing the server already listening on $Origin"
    }
    else {
        Write-Host "Starting the production server on $Origin ..."
        $serverProcess = Start-CalculatorServer
        if (-not (Test-ServerReady -TimeoutSeconds 30)) {
            throw "The server did not become healthy at $HealthUrl. Install dependencies with 'pip install -r requirements.txt' and try again."
        }
    }

    Get-CloudflaredClient

    Write-Host "Opening a public tunnel to $Origin ..."
    $publicUrl = $null
    & $CloudflaredPath tunnel --url $Origin --no-autoupdate 2>&1 | ForEach-Object {
        $line = $_.ToString()
        if (-not $publicUrl -and $line -match $PublicUrlPattern) {
            $publicUrl = $Matches[0]
            Write-Host ""
            Write-Host "  Public address: $publicUrl" -ForegroundColor Green
            Write-Host ""
        }
        elseif ($line -notmatch "trycloudflare\.com" -and $line -notmatch "^2026-") {
            Write-Host $line
        }
    }

    if (-not $publicUrl) {
        Write-Warning "The tunnel closed before a public address was issued."
    }
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
        Write-Host "Local server stopped."
    }
}
