# Compatibility entry point. Use ./scripts/setup.cmd for installation.
& (Join-Path $PSScriptRoot 'setup.ps1') @args
exit $LASTEXITCODE
