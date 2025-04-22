# 获取脚本所在目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "脚本路径: $scriptPath" -ForegroundColor Cyan

# venv环境中Python解释器的路径
$venvPath = Join-Path -Path $scriptPath -ChildPath "venv"
$pythonPath = Join-Path -Path $venvPath -ChildPath "Scripts\python.exe"

# 输出路径以便调试
Write-Host "查找Python解释器: $pythonPath" -ForegroundColor Cyan

# 确保Python解释器存在
if (-not (Test-Path -LiteralPath $pythonPath)) {
    # 尝试检查venv目录本身是否存在
    if (-not (Test-Path -LiteralPath $venvPath)) {
        Write-Host "venv目录不存在: $venvPath" -ForegroundColor Red
    } else {
        Write-Host "venv目录存在，但未找到Python解释器" -ForegroundColor Yellow
        # 列出venv/Scripts目录内容以帮助调试
        Get-ChildItem -Path (Join-Path -Path $venvPath -ChildPath "Scripts") -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "找到文件: $($_.FullName)" -ForegroundColor Gray
        }
    }

    Write-Error "Python虚拟环境未找到。请确保在同目录下存在venv文件夹。"
    exit 1
}

# fluent.py和router.py的路径
$fluentPath = Join-Path -Path $scriptPath -ChildPath "fluent.py"
$routerPath = Join-Path -Path $scriptPath -ChildPath "router.py"

# 检查两个Python文件是否存在
if (-not (Test-Path -LiteralPath $fluentPath)) {
    Write-Error "fluent.py未找到: $fluentPath"
    exit 1
}

if (-not (Test-Path -LiteralPath $routerPath)) {
    Write-Error "router.py未找到: $routerPath"
    exit 1
}

Write-Host "正在启动fluent.py和router.py..." -ForegroundColor Green

# 使用Start-Process在独立进程中启动两个Python脚本
$fluentProcess = Start-Process -FilePath $pythonPath -ArgumentList "`"$fluentPath`"" -PassThru -NoNewWindow
$routerProcess = Start-Process -FilePath $pythonPath -ArgumentList "`"$routerPath`"" -PassThru -NoNewWindow

Write-Host "fluent.py (PID: $($fluentProcess.Id))和router.py (PID: $($routerProcess.Id))已启动。" -ForegroundColor Green
Write-Host "按Ctrl+C终止程序..." -ForegroundColor Yellow

try {
    # 等待用户输入以保持脚本运行
    while ($true) {
        Start-Sleep -Seconds 1
        # 检查进程是否仍在运行
        if ($fluentProcess.HasExited -and $routerProcess.HasExited) {
            Write-Host "两个进程均已退出。" -ForegroundColor Red
            break
        } elseif ($fluentProcess.HasExited) {
            Write-Host "fluent.py进程已退出。" -ForegroundColor Red
            break
        } elseif ($routerProcess.HasExited) {
            Write-Host "router.py进程已退出。" -ForegroundColor Red
            break
        }
    }
}
finally {
    # 确保在脚本退出时终止子进程
    if (-not $fluentProcess.HasExited) {
        $fluentProcess | Stop-Process -Force
    }
    if (-not $routerProcess.HasExited) {
        $routerProcess | Stop-Process -Force
    }
    Write-Host "所有进程已终止。" -ForegroundColor Green
}