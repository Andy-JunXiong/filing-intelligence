param(
    [string[]]$Tickers = @("MSFT", "NVDA", "AMZN", "GOOGL", "META"),
    [string]$FilingType = "10-K",
    [string]$FilingYear = "2025"
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Test-Path "C:\Program Files\Amazon\AWSSAMCLI\runtime\python.exe") {
    $pythonCmd = "C:\Program Files\Amazon\AWSSAMCLI\runtime\python.exe"
} else {
    throw "Python executable not found. Please install Python or update the script path."
}

& $pythonCmd -m app.main --compare-many @Tickers --filing-type $FilingType --filing-year $FilingYear --mode real
