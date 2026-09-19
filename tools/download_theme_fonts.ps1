$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$fontDir = Join-Path $root 'assets\fonts'
New-Item -ItemType Directory -Force -Path $fontDir | Out-Null

$files = [ordered]@{
    'NotoSansCJKsc-Regular.otf' = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
    'NotoSansCJKsc-Bold.otf' = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf'
    'NotoSansMonoCJKsc-Regular.otf' = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Mono/NotoSansMonoCJKsc-Regular.otf'
    'NotoSansMonoCJKsc-Bold.otf' = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Mono/NotoSansMonoCJKsc-Bold.otf'
    'OFL.txt' = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE'
}

foreach ($item in $files.GetEnumerator()) {
    $target = Join-Path $fontDir $item.Key
    $isFont = [System.IO.Path]::GetExtension($item.Key) -ieq '.otf'
    $minimumBytes = if ($isFont) { 5MB } else { 1KB }

    if (Test-Path $target) {
        $existing = Get-Item $target
        if ($existing.Length -ge $minimumBytes) {
            Write-Host "Already present: $($item.Key)"
            continue
        }
    }

    $temp = "$target.download"
    Remove-Item -Force -ErrorAction SilentlyContinue $temp
    Write-Host "Downloading $($item.Key)..."
    Invoke-WebRequest -Uri $item.Value -OutFile $temp -UseBasicParsing
    $downloaded = Get-Item $temp
    if ($downloaded.Length -lt $minimumBytes) {
        Remove-Item -Force -ErrorAction SilentlyContinue $temp
        throw "Downloaded file looks invalid or incomplete: $($item.Key)"
    }
    Move-Item -Force $temp $target
}

Write-Host ''
Write-Host 'Theme fonts ready in assets\fonts.'
