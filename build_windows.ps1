param(
  [string]$StockfishPath = "",
  [switch]$NoZip
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows) {
  throw "build_windows.ps1 must be run on Windows"
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  py -3 -m venv .venv
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt -r requirements-build.txt

function Get-LatestStockfishExe {
  $downloadDir = Join-Path $Root ".cache\stockfish"
  if (Test-Path $downloadDir) {
    Remove-Item -Path $downloadDir -Recurse -Force
  }
  New-Item -ItemType Directory -Path $downloadDir | Out-Null

  $apiUrl = "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest"
  $headers = @{ "User-Agent" = "ChessHelper-Windows-Build" }
  $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers

  $patterns = @(
    "windows.*x86-64.*avx2.*\.zip$",
    "windows.*x86-64.*bmi2.*\.zip$",
    "windows.*x86-64.*\.zip$",
    "windows.*\.zip$"
  )

  $asset = $null
  foreach ($pattern in $patterns) {
    $asset = $release.assets | Where-Object { $_.name -match $pattern } | Select-Object -First 1
    if ($asset) { break }
  }

  if (-not $asset) {
    throw "Windows Stockfish asset was not found in latest release"
  }

  Write-Host "Downloading $($asset.name)..."
  $zipPath = Join-Path $downloadDir "stockfish.zip"
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath

  $extractPath = Join-Path $downloadDir "extract"
  Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

  $engine = Get-ChildItem -Path $extractPath -Recurse -File -Filter "*.exe" |
    Where-Object { $_.Name -match "^stockfish.*\.exe$" } |
    Sort-Object Length -Descending |
    Select-Object -First 1

  if (-not $engine) {
    throw "stockfish.exe not found after archive extraction"
  }

  return $engine.FullName
}

function Resolve-StockfishPath {
  param([string]$Requested)

  if ($Requested -and (Test-Path $Requested)) {
    return (Resolve-Path $Requested).Path
  }

  if ($env:STOCKFISH_PATH -and (Test-Path $env:STOCKFISH_PATH)) {
    return (Resolve-Path $env:STOCKFISH_PATH).Path
  }

  $whereMatches = @()
  try {
    $whereMatches = (& where.exe stockfish 2>$null)
  } catch {
    $whereMatches = @()
  }

  foreach ($candidate in $whereMatches) {
    if (-not (Test-Path $candidate)) {
      continue
    }
    if ($candidate -match "\\chocolatey\\bin\\") {
      continue
    }
    return (Resolve-Path $candidate).Path
  }

  $searchRoots = @("C:\tools", "C:\ProgramData\chocolatey\lib")
  foreach ($rootPath in $searchRoots) {
    if (-not (Test-Path $rootPath)) {
      continue
    }
    $engine = Get-ChildItem -Path $rootPath -Recurse -File -Filter "stockfish*.exe" -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -notmatch "\\chocolatey\\bin\\" } |
      Sort-Object Length -Descending |
      Select-Object -First 1

    if ($engine) {
      return $engine.FullName
    }
  }

  return Get-LatestStockfishExe
}

$resolvedStockfish = Resolve-StockfishPath -Requested $StockfishPath
if (-not $resolvedStockfish) {
  throw "Unable to resolve Stockfish path"
}

Write-Host "Stockfish: $resolvedStockfish"

$buildArgs = @("build_app.py", "--stockfish", $resolvedStockfish)
if ($NoZip) {
  $buildArgs += "--no-zip"
}

& $VenvPython @buildArgs

Write-Host "Done. Check dist and release folders."
