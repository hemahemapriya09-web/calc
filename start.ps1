<#
.SYNOPSIS
    Runs the calculator on a production WSGI server, exactly as a host would.

.DESCRIPTION
    Linux hosts run `gunicorn wsgi:app`. On Windows gunicorn is not available,
    so this script uses waitress, the equivalent production WSGI server.
    Binds 0.0.0.0 so other devices on your network can reach it too.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Port 8080
#>
[CmdletBinding()]
param(
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if ($IsWindows -or $env:OS -eq "Windows_NT") {
    Write-Host "Serving with waitress on http://0.0.0.0:$Port (Ctrl+C to stop)"
    python -m waitress --listen=0.0.0.0:$Port wsgi:app
}
else {
    Write-Host "Serving with gunicorn on http://0.0.0.0:$Port (Ctrl+C to stop)"
    gunicorn wsgi:app --bind 0.0.0.0:$Port --workers 2 --threads 4 --timeout 60
}
