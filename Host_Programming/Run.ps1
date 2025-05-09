$ScriptDirectory = $PSScriptRoot
$VenvActivateScript = Join-Path -Path $ScriptDirectory -ChildPath ".venv\Scripts\Activate.ps1"
$SplashScript = Join-Path -Path $ScriptDirectory -ChildPath "splash.py"

# 检查虚拟环境激活脚本是否存在
if (-not (Test-Path $VenvActivateScript)) {
    Write-Error "错误：找不到虚拟环境激活脚本 '$VenvActivateScript'。请确保虚拟环境已在 '.venv' 目录中创建。"
    Read-Host "按 Enter 键退出"
    exit 1
}

# 检查 splash.py 是否存在
if (-not (Test-Path $SplashScript)) {
    Write-Error "错误：找不到启动脚本 '$SplashScript'。"
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host "正在激活虚拟环境..."
try {
    . $VenvActivateScript
    Write-Host "虚拟环境已激活。"
    Write-Host "正在运行 splash.py..."
    python $SplashScript

} catch {
    Write-Error "执行过程中发生错误: $($_.Exception.Message)"
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
    }
    Read-Host "按 Enter 键退出"
    exit 1
}

# 脚本正常结束
exit 0