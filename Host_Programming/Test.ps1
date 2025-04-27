# 添加必要的命名空间
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 创建主窗体
$form = New-Object System.Windows.Forms.Form
$form.Text = "数据发送工具"
$form.Size = New-Object System.Drawing.Size(500, 600)
$form.StartPosition = "CenterScreen"
$form.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 9)

# 函数：在控制台输出日志
function WriteLog($message) {
    Write-Host $message
}

# 创建网络设置组
$networkGroupBox = New-Object System.Windows.Forms.GroupBox
$networkGroupBox.Text = "网络设置"
$networkGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$networkGroupBox.Size = New-Object System.Drawing.Size(440, 100)

$ipLabel = New-Object System.Windows.Forms.Label
$ipLabel.Text = "IP地址:"
$ipLabel.Location = New-Object System.Drawing.Point(20, 30)
$ipLabel.Size = New-Object System.Drawing.Size(70, 20)

$ipTextBox = New-Object System.Windows.Forms.TextBox
$ipTextBox.Text = "127.0.0.1"
$ipTextBox.Location = New-Object System.Drawing.Point(100, 30)
$ipTextBox.Size = New-Object System.Drawing.Size(150, 20)

$portLabel = New-Object System.Windows.Forms.Label
$portLabel.Text = "端口:"
$portLabel.Location = New-Object System.Drawing.Point(270, 30)
$portLabel.Size = New-Object System.Drawing.Size(50, 20)

$portTextBox = New-Object System.Windows.Forms.TextBox
$portTextBox.Text = "5000"
$portTextBox.Location = New-Object System.Drawing.Point(330, 30)
$portTextBox.Size = New-Object System.Drawing.Size(80, 20)

$connectButton = New-Object System.Windows.Forms.Button
$connectButton.Text = "连接"
$connectButton.Location = New-Object System.Drawing.Point(170, 60)
$connectButton.Size = New-Object System.Drawing.Size(100, 30)

# 数据模式组
$dataGroupBox = New-Object System.Windows.Forms.GroupBox
$dataGroupBox.Text = "数据模式"
$dataGroupBox.Location = New-Object System.Drawing.Point(20, 130)
$dataGroupBox.Size = New-Object System.Drawing.Size(440, 70)

$randomDataRadio = New-Object System.Windows.Forms.RadioButton
$randomDataRadio.Text = "随机数据"
$randomDataRadio.Checked = $true
$randomDataRadio.Location = New-Object System.Drawing.Point(100, 30)
$randomDataRadio.Size = New-Object System.Drawing.Size(100, 20)

$fixedDataRadio = New-Object System.Windows.Forms.RadioButton
$fixedDataRadio.Text = "固定数据"
$fixedDataRadio.Location = New-Object System.Drawing.Point(250, 30)
$fixedDataRadio.Size = New-Object System.Drawing.Size(100, 20)

# 数据设置组
$dataSettingsGroupBox = New-Object System.Windows.Forms.GroupBox
$dataSettingsGroupBox.Text = "数据设置"
$dataSettingsGroupBox.Location = New-Object System.Drawing.Point(20, 210)
$dataSettingsGroupBox.Size = New-Object System.Drawing.Size(440, 160)

$tempLabel = New-Object System.Windows.Forms.Label
$tempLabel.Text = "温度:"
$tempLabel.Location = New-Object System.Drawing.Point(20, 30)
$tempLabel.Size = New-Object System.Drawing.Size(90, 20)

$tempTextBox = New-Object System.Windows.Forms.TextBox
$tempTextBox.Text = "20.0"
$tempTextBox.Enabled = $false
$tempTextBox.Location = New-Object System.Drawing.Point(120, 30)
$tempTextBox.Size = New-Object System.Drawing.Size(80, 20)

$humidityLabel = New-Object System.Windows.Forms.Label
$humidityLabel.Text = "湿度:"
$humidityLabel.Location = New-Object System.Drawing.Point(20, 70)
$humidityLabel.Size = New-Object System.Drawing.Size(90, 20)

$humidityTextBox = New-Object System.Windows.Forms.TextBox
$humidityTextBox.Text = "40.0"
$humidityTextBox.Enabled = $false
$humidityTextBox.Location = New-Object System.Drawing.Point(120, 70)
$humidityTextBox.Size = New-Object System.Drawing.Size(80, 20)

$pm25Label = New-Object System.Windows.Forms.Label
$pm25Label.Text = "PM2.5:"
$pm25Label.Location = New-Object System.Drawing.Point(230, 30)
$pm25Label.Size = New-Object System.Drawing.Size(90, 20)

$pm25TextBox = New-Object System.Windows.Forms.TextBox
$pm25TextBox.Text = "40"
$pm25TextBox.Enabled = $false
$pm25TextBox.Location = New-Object System.Drawing.Point(330, 30)
$pm25TextBox.Size = New-Object System.Drawing.Size(80, 20)

$noiseLabel = New-Object System.Windows.Forms.Label
$noiseLabel.Text = "噪声:"
$noiseLabel.Location = New-Object System.Drawing.Point(230, 70)
$noiseLabel.Size = New-Object System.Drawing.Size(90, 20)

$noiseTextBox = New-Object System.Windows.Forms.TextBox
$noiseTextBox.Text = "40"
$noiseTextBox.Enabled = $false
$noiseTextBox.Location = New-Object System.Drawing.Point(330, 70)
$noiseTextBox.Size = New-Object System.Drawing.Size(80, 20)

# 范围显示的标签
$rangeLabel = New-Object System.Windows.Forms.Label
$rangeLabel.Text = "-20~+60°C|0~100%|PM2.5:0~999ug|0~120dB"
$rangeLabel.Location = New-Object System.Drawing.Point(20, 120)
$rangeLabel.Size = New-Object System.Drawing.Size(400, 20)
$rangeLabel.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 8)

# 发送设置组
$sendSettingsGroupBox = New-Object System.Windows.Forms.GroupBox
$sendSettingsGroupBox.Text = "发送设置"
$sendSettingsGroupBox.Location = New-Object System.Drawing.Point(20, 380)
$sendSettingsGroupBox.Size = New-Object System.Drawing.Size(440, 120)

$sendCountLabel = New-Object System.Windows.Forms.Label
$sendCountLabel.Text = "次数:"
$sendCountLabel.Location = New-Object System.Drawing.Point(20, 30)
$sendCountLabel.Size = New-Object System.Drawing.Size(70, 20)

$sendCountTextBox = New-Object System.Windows.Forms.TextBox
$sendCountTextBox.Text = "1"
$sendCountTextBox.Location = New-Object System.Drawing.Point(100, 30)
$sendCountTextBox.Size = New-Object System.Drawing.Size(80, 20)

$intervalLabel = New-Object System.Windows.Forms.Label
$intervalLabel.Text = "间隔ms:"
$intervalLabel.Location = New-Object System.Drawing.Point(200, 30)
$intervalLabel.Size = New-Object System.Drawing.Size(70, 20)

$intervalTextBox = New-Object System.Windows.Forms.TextBox
$intervalTextBox.Text = "1000"
$intervalTextBox.Location = New-Object System.Drawing.Point(280, 30)
$intervalTextBox.Size = New-Object System.Drawing.Size(80, 20)

# 发送按钮和停止按钮
$sendButton = New-Object System.Windows.Forms.Button
$sendButton.Text = "发送"
$sendButton.Location = New-Object System.Drawing.Point(120, 70)
$sendButton.Size = New-Object System.Drawing.Size(90, 35)

$stopButton = New-Object System.Windows.Forms.Button
$stopButton.Text = "终止"
$stopButton.Location = New-Object System.Drawing.Point(240, 70)
$stopButton.Size = New-Object System.Drawing.Size(90, 35)
$stopButton.Enabled = $false

# 添加控件到窗体
$networkGroupBox.Controls.AddRange(@($ipLabel, $ipTextBox, $portLabel, $portTextBox, $connectButton))
$dataGroupBox.Controls.AddRange(@($randomDataRadio, $fixedDataRadio))
$dataSettingsGroupBox.Controls.AddRange(@($tempLabel, $tempTextBox, $humidityLabel, $humidityTextBox, $pm25Label, $pm25TextBox, $noiseLabel, $noiseTextBox, $rangeLabel))
$sendSettingsGroupBox.Controls.AddRange(@($sendCountLabel, $sendCountTextBox, $intervalLabel, $intervalTextBox, $sendButton, $stopButton))

$form.Controls.AddRange(@($networkGroupBox, $dataGroupBox, $dataSettingsGroupBox, $sendSettingsGroupBox))

# 全局变量
$script:clientSocket = $null
$script:timer = New-Object System.Windows.Forms.Timer
$script:timer.Interval = 2000
$script:remainingSends = 0

# 用于生成连续变化的随机数据
$script:lastTemp = 20.0
$script:lastHumidity = 40.0
$script:lastPM25 = 40
$script:lastNoise = 40

# 数据处理函数
function ValidateNumber($value, $min, $max, $default, $decimals = 0) {
    try {
        $num = [double]::Parse($value)
        $num = [Math]::Max($min, [Math]::Min($max, $num))
        if ($decimals -gt 0) {
            return [Math]::Round($num, $decimals)
        }
        return [int]$num
    } catch {
        return $default
    }
}

# 生成平滑变化的随机数
function SmoothRandomValue($lastValue, $min, $max, $maxChange, $decimals = 0) {
    $rnd = Get-Random -Minimum -1.0 -Maximum 1.0
    $change = $rnd * $maxChange
    $newValue = $lastValue + $change
    $newValue = [Math]::Max($min, [Math]::Min($max, $newValue))
    if ($decimals -gt 0) {
        return [Math]::Round($newValue, $decimals)
    }
    return [int]$newValue
}

# 发送数据
function SendData {
    try {
        # 获取要发送的数据
        if ($randomDataRadio.Checked) {
            # 生成平滑变化的随机数据
            $script:lastTemp = SmoothRandomValue $script:lastTemp -10 40 1.5 1
            $script:lastHumidity = SmoothRandomValue $script:lastHumidity 20 80 2.5 1
            $script:lastPM25 = SmoothRandomValue $script:lastPM25 10 300 15
            $script:lastNoise = SmoothRandomValue $script:lastNoise 30 90 5

            $data = @{
                temperature = $script:lastTemp
                humidity = $script:lastHumidity
                pm25 = $script:lastPM25
                noise = $script:lastNoise
            }
        } else {
            $data = @{
                temperature = ValidateNumber $tempTextBox.Text -20 60 20 1
                humidity = ValidateNumber $humidityTextBox.Text 0 100 40 1
                pm25 = ValidateNumber $pm25TextBox.Text 0 999 40
                noise = ValidateNumber $noiseTextBox.Text 0 120 40
            }
        }

        # 打包数据
        $ms = New-Object IO.MemoryStream
        $bw = New-Object IO.BinaryWriter($ms)

        # 添加头部
        $bw.Write([byte]0xAA)
        $bw.Write([byte]0xBB)
        $bw.Write([byte]0xCC)
        $bw.Write([byte]0xDD)

        # 以网络字节序(大端)写入数据
        $tempBytes = [BitConverter]::GetBytes([int16]($data.temperature * 10))
        if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($tempBytes) }
        $bw.Write($tempBytes)

        $humidityBytes = [BitConverter]::GetBytes([uint16]($data.humidity * 10))
        if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($humidityBytes) }
        $bw.Write($humidityBytes)

        $pm25Bytes = [BitConverter]::GetBytes([uint16]$data.pm25)
        if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($pm25Bytes) }
        $bw.Write($pm25Bytes)

        $bw.Write([byte]$data.noise)

        # 发送数据
        $packet = $ms.ToArray()
        $script:clientSocket.GetStream().Write($packet, 0, $packet.Length)
        $bw.Close()
        $ms.Close()

        # 更新计数
        $script:remainingSends = $script:remainingSends - 1
        if ($script:remainingSends -le 0) {
            StopSending
        }

        WriteLog "已发送: 温度=$($data.temperature)°C, 湿度=$($data.humidity)%, PM2.5=$($data.pm25)μg/m³, 噪声=$($data.noise)dB"
    }
    catch {
        WriteLog "发送数据失败: $($_.Exception.Message)"
        StopSending
        DisconnectSocket
    }
}

# 停止发送
function StopSending {
    $script:timer.Stop()
    $sendButton.Enabled = $true
    $stopButton.Enabled = $false
    $script:remainingSends = 0

    if ($null -ne $script:clientSocket) {
        WriteLog "已停止发送数据"
    }
}

# 断开连接
function DisconnectSocket {
    if ($null -ne $script:clientSocket) {
        try {
            $script:clientSocket.Close()
            $script:clientSocket.Dispose()
        } catch {
            # 忽略关闭时的错误
        }
        $script:clientSocket = $null

        $connectButton.Text = "连接"
        $ipTextBox.Enabled = $true
        $portTextBox.Enabled = $true
        $sendButton.Enabled = $false

        WriteLog "已断开连接"
    }
}

# 事件处理
$randomDataRadio.Add_Click({
    $tempTextBox.Enabled = $false
    $humidityTextBox.Enabled = $false
    $pm25TextBox.Enabled = $false
    $noiseTextBox.Enabled = $false
    WriteLog "已切换到随机数据模式"
})

$fixedDataRadio.Add_Click({
    $tempTextBox.Enabled = $true
    $humidityTextBox.Enabled = $true
    $pm25TextBox.Enabled = $true
    $noiseTextBox.Enabled = $true
    WriteLog "已切换到固定数据模式"
})

$connectButton.Add_Click({
    if ($null -eq $script:clientSocket) {
        try {
            $hostAddress = $ipTextBox.Text
            $port = [int]::Parse($portTextBox.Text)

            WriteLog "正在连接到 $hostAddress`:$port..."

            $script:clientSocket = New-Object System.Net.Sockets.TcpClient
            # 设置连接超时为5秒
            $result = $script:clientSocket.BeginConnect($hostAddress, $port, $null, $null)
            $success = $result.AsyncWaitHandle.WaitOne(5000, $false)

            if (-not $success) {
                throw "连接超时，请检查服务器是否启动"
            }

            # 完成连接过程
            $script:clientSocket.EndConnect($result)

            $connectButton.Text = "断开"
            $ipTextBox.Enabled = $false
            $portTextBox.Enabled = $false
            $sendButton.Enabled = $true

            WriteLog "成功连接到 $hostAddress`:$port"
        }
        catch {
            if ($null -ne $script:clientSocket) {
                try {
                    $script:clientSocket.Close()
                } catch {}
                $script:clientSocket = $null
            }

            WriteLog "无法连接到服务器: $($_.Exception.Message)"
        }
    }
    else {
        StopSending
        DisconnectSocket
    }
})

$sendButton.Add_Click({
    if ($null -eq $script:clientSocket) {
        WriteLog "请先连接到服务器"
        return
    }

    $count = ValidateNumber $sendCountTextBox.Text 1 1000 1
    $sendCountTextBox.Text = $count.ToString()

    $interval = ValidateNumber $intervalTextBox.Text 100 60000 2000
    $intervalTextBox.Text = $interval.ToString()

    $script:remainingSends = $count
    $script:timer.Interval = $interval

    if ($count -eq 1) {
        # 单次发送
        WriteLog "开始单次发送"
        SendData
    } else {
        # 多次发送
        $sendButton.Enabled = $false
        $stopButton.Enabled = $true
        WriteLog "开始多次发送 (共$count次，间隔$interval毫秒)"
        SendData
        $script:timer.Start()
    }
})

$stopButton.Add_Click({
    WriteLog "用户手动停止发送"
    StopSending
})

# 数值验证
$tempTextBox.Add_Leave({
    $tempTextBox.Text = (ValidateNumber $tempTextBox.Text -20 60 20 1).ToString("F1")
})

$humidityTextBox.Add_Leave({
    $humidityTextBox.Text = (ValidateNumber $humidityTextBox.Text 0 100 40 1).ToString("F1")
})

$pm25TextBox.Add_Leave({
    $pm25TextBox.Text = (ValidateNumber $pm25TextBox.Text 0 999 40).ToString()
})

$noiseTextBox.Add_Leave({
    $noiseTextBox.Text = (ValidateNumber $noiseTextBox.Text 0 120 40).ToString()
})

$sendCountTextBox.Add_Leave({
    $sendCountTextBox.Text = (ValidateNumber $sendCountTextBox.Text 1 1000 1).ToString()
})

$intervalTextBox.Add_Leave({
    $intervalTextBox.Text = (ValidateNumber $intervalTextBox.Text 100 60000 2000).ToString()
})

# 定时器事件
$script:timer.Add_Tick({
    if ($script:remainingSends -gt 0) {
        SendData
    } else {
        StopSending
    }
})

# 启动时的初始状态
$sendButton.Enabled = $false

# 在窗口关闭时清理
$form.Add_FormClosing({
    WriteLog "程序正在关闭..."
    StopSending
    DisconnectSocket
})

# 向控制台输出程序启动信息
WriteLog "数据发送工具已启动"

# 显示窗口
[void]$form.ShowDialog()