<#
.SYNOPSIS
    Publishes the calculator on a public HTTPS address straight from this machine.

.DESCRIPTION
    Starts the production WSGI server, opens a Cloudflare quick tunnel to it and
    prints the public trycloudflare.com address. No account, DNS record or
    firewall change is needed. The address stays live while this script runs;
    closing the window or pressing Ctrl+C stops both the tunnel and the server.

    The tunnel writes its log to .tools\tunnel.log, which is where the public
    address is read from.

.EXAMPLE
    .\share.ps1
    .\share.ps1 -Port 8080
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location -Path $PSScriptRoot

if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    throw "share.ps1 downloads the Windows tunnel client. Elsewhere install cloudflared and run: cloudflared tunnel --url http://127.0.0.1:$Port"
}

$ToolsDirectory = Join-Path $PSScriptRoot ".tools"
$CloudflaredPath = Join-Path $ToolsDirectory "cloudflared.exe"
$TunnelLogPath = Join-Path $ToolsDirectory "tunnel.log"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$Origin = "http://127.0.0.1:$Port"
$HealthUrl = "$Origin/healthz"
$PublicUrlPattern = "https://[a-z0-9-]+\.trycloudflare\.com"
$StartupTimeoutSeconds = 45

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
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $CloudflaredPath -UseBasicParsing
}

function Start-CalculatorServer {
    $interpreter = (Get-Command python -ErrorAction Stop).Source
    return Start-Process -FilePath $interpreter `
        -ArgumentList "-m", "waitress", "--listen=127.0.0.1:$Port", "wsgi:app" `
        -PassThru -WindowStyle Hidden
}

function Start-Tunnel {
    if (Test-Path $TunnelLogPath) {
        Remove-Item $TunnelLogPath -Force
    }

    # Built as one string: Start-Process does not quote array elements, and this
    # project can live in a path containing spaces.
    $arguments = 'tunnel --url ' + $Origin +
        ' --no-autoupdate --loglevel info' +
        ' --logfile "' + $TunnelLogPath + '"'

    return Start-Process -FilePath $CloudflaredPath -ArgumentList $arguments -PassThru -WindowStyle Hidden
}

function Wait-ForPublicUrl {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$TunnelProcess,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($TunnelProcess.HasExited) {
            return $null
        }
        if (Test-Path $TunnelLogPath) {
            $found = Select-String -Path $TunnelLogPath -Pattern $PublicUrlPattern -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($found) {
                return $found.Matches[0].Value
            }
        }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

function Write-HostedAddress {
    param([string]$PublicUrl)

    Write-Host ""
    Write-Host "  Your calculator is live on the internet:" -ForegroundColor Green
    Write-Host "  $PublicUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Try it:      $PublicUrl/healthz"
    Write-Host "  Local copy:  $Origin"
    Write-Host "  Press Ctrl+C (or close this window) to take it offline."
    Write-Host ""
}

$serverProcess = $null
$tunnelProcess = $null

try {
    if (Test-ServerReady -TimeoutSeconds 3) {
        Write-Host "Reusing the server already listening on $Origin"
    }
    else {
        Write-Host "Starting the production server on $Origin ..."
        $serverProcess = Start-CalculatorServer
        if (-not (Test-ServerReady -TimeoutSeconds 30)) {
            throw "The server never became healthy at $HealthUrl. Run 'python -m pip install -r requirements.txt' first."
        }
    }

    Get-CloudflaredClient

    Write-Host "Opening a public tunnel to $Origin ..."
    $tunnelProcess = Start-Tunnel
    $publicUrl = Wait-ForPublicUrl -TunnelProcess $tunnelProcess -TimeoutSeconds $StartupTimeoutSeconds

    if (-not $publicUrl) {
        if ($tunnelProcess.HasExited) {
            Write-Host "cloudflared exited with code $($tunnelProcess.ExitCode)."
        }
        if (Test-Path $TunnelLogPath) {
            Write-Host "--- tunnel log (last 15 lines) ---"
            Get-Content -Path $TunnelLogPath -Tail 15
        }
        throw "The tunnel did not issue a public address within $StartupTimeoutSeconds seconds."
    }

    Write-HostedAddress -PublicUrl $publicUrl

    Wait-Process -Id $tunnelProcess.Id -ErrorAction SilentlyContinue
    Write-Host "Tunnel closed."
}
finally {
    if ($tunnelProcess -and -not $tunnelProcess.HasExited) {
        Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Local server stopped."
    }
}
