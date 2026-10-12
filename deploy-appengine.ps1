<#
.SYNOPSIS
    Deploys the calculator to Google App Engine (standard environment).

.DESCRIPTION
    Runs the whole App Engine deployment in order:

1. locates the gcloud CLI and the signed-in account
2. picks the project (parameter, or the gcloud default)
3. checks that the project has billing enabled, and links a billing
    account automatically when the signed-in user has exactly one
4. creates the App Engine application the first time only
    5. deploys app.yaml
    6. with -Verify, runs _verify_endpoints.py against the live URL

    App Engine requires a billing account attached to the project, so a payment
    method must be added once at <https://console.cloud.google.com/billing/create>.
    That step cannot be scripted; when it is missing the script stops and says so.

.PARAMETER Project
    Google Cloud project id. Defaults to the project configured in gcloud.

.PARAMETER Region
    App Engine region. Used only when the application is created, because the
    region is permanent for the project. Default: us-central1.

.PARAMETER Verify
    Run the endpoint suite against the deployed URL when the deploy finishes.

.EXAMPLE
    .\deploy-appengine.ps1 -Verify

.EXAMPLE
    .\deploy-appengine.ps1 -Project calc-hemahemapriya -Region asia-south1
#>
[CmdletBinding()]
param(
    [string]$Project,
    [string]$Region = "us-central1",
    [switch]$Verify
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location -Path $PSScriptRoot

$BillingConsoleUrl = "https://console.cloud.google.com/billing/create"
$VerifyScript = Join-Path $PSScriptRoot "_verify_endpoints.py"
$FallbackPython = "C:\Program Files\Python313\python.exe"

function Get-GcloudPath {
    $onPath = Get-Command gcloud -ErrorAction SilentlyContinue
    if ($onPath) {
        return $onPath.Source
    }

    $localSdk = Join-Path $env:USERPROFILE "google-cloud-sdk\bin\gcloud.cmd"
    if (Test-Path $localSdk) {
        return $localSdk
    }

    throw "gcloud was not found. Install the Google Cloud CLI first: https://cloud.google.com/sdk/docs/install"
}

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [switch]$IgnoreFailure
    )

    $output = & $Gcloud @Arguments 2>&1 | Out-String
    $script:GcloudExitCode = $LASTEXITCODE

    if ($GcloudExitCode -ne 0 -and -not $IgnoreFailure) {
        throw "gcloud $($Arguments -join ' ') failed:`n$output"
    }
    return $output
}

function Resolve-Project {
    if ($Project) {
        return $Project
    }

    $configured = (Invoke-Gcloud -Arguments @("config", "get-value", "project")).Trim()
    if (-not $configured -or $configured -eq "(unset)") {
        throw "No project selected. Pass -Project <id> or run: gcloud config set project <id>"
    }
    return $configured
}

function Test-BillingEnabled {
    param([string]$ProjectId)

    $status = Invoke-Gcloud -Arguments @("billing", "projects", "describe", $ProjectId) -IgnoreFailure
    return $status -match "billingEnabled:\s*true"
}

function Connect-BillingAccount {
    param([string]$ProjectId)

    $accounts = Invoke-Gcloud -Arguments @("billing", "accounts", "list", "--format=value(name)") -IgnoreFailure
    $accountIds = @($accounts -split "`r?`n" | Where-Object { $_.Trim() -ne "" })

    if ($accountIds.Count -eq 1) {
        Write-Host "Linking billing account $($accountIds[0]) to $ProjectId ..."
        Invoke-Gcloud -Arguments @("billing", "projects", "link", $ProjectId, "--billing-account=$($accountIds[0])") | Out-Null
        return (Test-BillingEnabled -ProjectId $ProjectId)
    }

    return $false
}

function Ensure-AppEngineApplication {
    param([string]$ProjectId)

    Invoke-Gcloud -Arguments @("app", "describe", "--project=$ProjectId") -IgnoreFailure | Out-Null
    if ($GcloudExitCode -eq 0) {
        Write-Host "App Engine application already exists in $ProjectId."
        return
    }

    Write-Host "Creating the App Engine application in $ProjectId (region $Region, permanent) ..."
    Invoke-Gcloud -Arguments @("app", "create", "--project=$ProjectId", "--region=$Region") | Out-Null
}

$Gcloud = Get-GcloudPath

# The bundled SDK has no Python of its own; pin a supported interpreter when the
# default python on PATH is newer than gcloud supports.
if (-not $env:CLOUDSDK_PYTHON -and (Test-Path $FallbackPython)) {
    $env:CLOUDSDK_PYTHON = $FallbackPython
}
$env:CLOUDSDK_CORE_DISABLE_PROMPTS = "1"

$projectId = Resolve-Project
Write-Host "Project:  $projectId"
Write-Host "Region:   $Region (used only if the App Engine app does not exist yet)"

$account = (Invoke-Gcloud -Arguments @("config", "get-value", "account")).Trim()
if (-not $account -or $account -eq "(unset)") {
    throw "No signed-in Google account. Run: gcloud auth login"
}
Write-Host "Account:  $account"

if (-not (Test-BillingEnabled -ProjectId $projectId)) {
    if (-not (Connect-BillingAccount -ProjectId $projectId)) {
        throw @"
App Engine needs a billing account attached to $projectId and none could be linked.

Add a payment method once at:
  $BillingConsoleUrl

Then run this script again. App Engine requires a billing account even for the
free tier; an F1 instance that scales to zero sits inside the free daily quota.
"@
    }
    Write-Host "Billing is now enabled on $projectId."
}

Ensure-AppEngineApplication -ProjectId $projectId

Write-Host "Deploying app.yaml ..."
Invoke-Gcloud -Arguments @("app", "deploy", "app.yaml", "--project=$projectId", "--quiet") -IgnoreFailure | Write-Host

$hostname = (Invoke-Gcloud -Arguments @("app", "describe", "--project=$projectId", "--format=value(defaultHostname)")).Trim()
$url = "https://$hostname"

Write-Host ""
Write-Host "  Deployed to: $url" -ForegroundColor Green
Write-Host "  Health:      $url/healthz"
Write-Host ""

if ($Verify -and (Test-Path $VerifyScript)) {
    Write-Host "Running the endpoint suite against $url ..."
    $env:CALC_BASE_URL = $url
    $env:CALC_TIMEOUT_SECONDS = "30"
    & python $VerifyScript
    if ($LASTEXITCODE -ne 0) {
        throw "The endpoint suite reported failures against $url"
    }
}
