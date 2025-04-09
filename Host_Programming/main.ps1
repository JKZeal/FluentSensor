$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $scriptDir "venv\Scripts\python.exe"
Start-Process -FilePath $pythonExe -ArgumentList (Join-Path $scriptDir "tcp_server.py")
& $pythonExe (Join-Path $scriptDir "plotly_ui.py")