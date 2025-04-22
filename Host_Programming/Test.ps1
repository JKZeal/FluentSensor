# 隐藏终端窗口
if ($host.Name -eq 'ConsoleHost') {
    Add-Type -Name Window -Namespace Console -MemberDefinition '
        [DllImport("Kernel32.dll")]
        public static extern IntPtr GetConsoleWindow();
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    '
    $consolePtr = [Console.Window]::GetConsoleWindow()
    [void][Console.Window]::ShowWindow($consolePtr, 0)
}

Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase

# 定义XAML界面
[xml]$xaml = @"
<Window
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    Title="数据发送工具" Height="360" Width="500"
    FontFamily="Microsoft YaHei UI"
    WindowStartupLocation="CenterScreen">
    <Grid Margin="10">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
        </Grid.RowDefinitions>
        
        <!-- 顶部区域 - 网络设置和数据模式 -->
        <Grid Grid.Row="0" Margin="0,0,0,10">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>
            
            <GroupBox Grid.Column="0" Header="网络设置" Margin="0,0,5,0">
                <Grid Margin="5">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="Auto"/>
                        <ColumnDefinition Width="*"/>
                        <ColumnDefinition Width="Auto"/>
                    </Grid.ColumnDefinitions>
                    <Grid.RowDefinitions>
                        <RowDefinition Height="Auto"/>
                        <RowDefinition Height="Auto"/>
                    </Grid.RowDefinitions>
                    
                    <Label Grid.Row="0" Grid.Column="0" Content="IP地址:" Margin="0,5" />
                    <TextBox Name="ipTextBox" Grid.Row="0" Grid.Column="1" Margin="5" Text="127.0.0.1" />
                    
                    <Label Grid.Row="1" Grid.Column="0" Content="端口:" Margin="0,5" />
                    <TextBox Name="portTextBox" Grid.Row="1" Grid.Column="1" Margin="5" Text="5000" />
                    
                    <Button Name="connectButton" Grid.Row="0" Grid.Column="2" Grid.RowSpan="2"
                            Content="连接" Width="70" Margin="5" />
                </Grid>
            </GroupBox>
            
            <GroupBox Grid.Column="1" Header="数据模式" Margin="5,0,0,0">
                <StackPanel Margin="10">
                    <RadioButton Name="randomDataRadio" Content="随机数据" IsChecked="True" Margin="0,5" />
                    <RadioButton Name="fixedDataRadio" Content="固定数据" Margin="0,5" />
                </StackPanel>
            </GroupBox>
        </Grid>
        
        <!-- 中部区域 - 数据设置和发送模式 -->
        <Grid Grid.Row="1" Margin="0,0,0,10">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="2*"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>
            
            <GroupBox Grid.Column="0" Header="数据设置" Margin="0,0,5,0">
                <Grid Margin="5">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="Auto"/>
                        <ColumnDefinition Width="*"/>
                        <ColumnDefinition Width="Auto"/>
                        <ColumnDefinition Width="*"/>
                    </Grid.ColumnDefinitions>
                    <Grid.RowDefinitions>
                        <RowDefinition Height="Auto"/>
                        <RowDefinition Height="Auto"/>
                    </Grid.RowDefinitions>
                    
                    <Label Grid.Row="0" Grid.Column="0" Content="温度(int16):" Margin="0,5" />
                    <TextBox Name="tempTextBox" Grid.Row="0" Grid.Column="1" Margin="5" IsEnabled="False" Text="25.0" />
                    
                    <Label Grid.Row="0" Grid.Column="2" Content="PM2.5(uint16):" Margin="0,5" />
                    <TextBox Name="pm25TextBox" Grid.Row="0" Grid.Column="3" Margin="5" IsEnabled="False" Text="50" />
                    
                    <Label Grid.Row="1" Grid.Column="0" Content="湿度(uint16):" Margin="0,5" />
                    <TextBox Name="humidityTextBox" Grid.Row="1" Grid.Column="1" Margin="5" IsEnabled="False" Text="50.0" />
                    
                    <Label Grid.Row="1" Grid.Column="2" Content="噪声(uint8):" Margin="0,5" />
                    <TextBox Name="noiseTextBox" Grid.Row="1" Grid.Column="3" Margin="5" IsEnabled="False" Text="50" />
                </Grid>
            </GroupBox>
            
            <GroupBox Grid.Column="1" Header="发送模式" Margin="5,0,0,0">
                <Grid Margin="5">
                    <Grid.RowDefinitions>
                        <RowDefinition Height="Auto"/>
                        <RowDefinition Height="Auto"/>
                    </Grid.RowDefinitions>
                    
                    <Button Name="sendOnceButton" Grid.Row="0" Content="单次发送" Margin="5,5,5,10" Padding="5" />
                    
                    <Grid Grid.Row="1">
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition Width="Auto"/>
                            <ColumnDefinition Width="*"/>
                        </Grid.ColumnDefinitions>
                        
                        <Button Name="autoSendButton" Grid.Column="0" Content="自动发送" Margin="5" />
                        
                        <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center" HorizontalAlignment="Right">
                            <TextBlock Text="间隔:" Margin="2,0" />
                            <TextBox Name="intervalTextBox" Width="30" Text="2" Margin="2,0" />
                            <TextBlock Text="秒" Margin="2,0" />
                        </StackPanel>
                    </Grid>
                </Grid>
            </GroupBox>
        </Grid>
        
        <!-- 底部区域 - 状态信息 -->
        <GroupBox Grid.Row="2" Header="状态信息">
            <TextBlock Name="statusLabel" Text="未连接" VerticalAlignment="Center" 
                      HorizontalAlignment="Center" TextWrapping="Wrap" Margin="10" />
        </GroupBox>
    </Grid>
</Window>
"@

# 加载XAML
$reader = [System.Xml.XmlNodeReader]::new($xaml)
$window = [System.Windows.Markup.XamlReader]::Load($reader)

# 获取控件引用
$controls = @{}
$xaml.SelectNodes("//*[@Name]") | ForEach-Object {
    $controls[$_.Name] = $window.FindName($_.Name)
}

# 全局变量
$script:clientSocket = $null
$script:timer = New-Object System.Windows.Threading.DispatcherTimer
$script:timer.Interval = [TimeSpan]::FromSeconds(2)

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

# 发送数据
function SendData {
    try {
        # 获取要发送的数据
        if ($controls.randomDataRadio.IsChecked) {
            $rnd = New-Object Random
            $data = @{
                temperature = [Math]::Round($rnd.NextDouble() * 50 - 10, 1) # -10.0 到 40.0
                humidity = [Math]::Round($rnd.NextDouble() * 60 + 20, 1)    # 20.0 到 80.0
                pm25 = $rnd.Next(10, 301)                                   # 10 到 300
                noise = $rnd.Next(30, 91)                                   # 30 到 90
            }
        } else {
            $data = @{
                temperature = ValidateNumber $controls.tempTextBox.Text -20 60 25 1
                humidity = ValidateNumber $controls.humidityTextBox.Text 0 100 50 1
                pm25 = ValidateNumber $controls.pm25TextBox.Text 0 999 50
                noise = ValidateNumber $controls.noiseTextBox.Text 0 120 50
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
        
        # 更新状态
        $controls.statusLabel.Text = "已发送: 温度=$($data.temperature)°C, " + 
                               "湿度=$($data.humidity)%, " +
                               "PM2.5=$($data.pm25)μg/m³, " +
                               "噪声=$($data.noise)dB"
    }
    catch {
        [System.Windows.MessageBox]::Show("发送数据失败: $($_.Exception.Message)", 
            "发送错误", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Error)
        StopAutoSend
        DisconnectSocket
    }
}

# 停止自动发送
function StopAutoSend {
    if ($script:timer.IsEnabled) {
        $script:timer.Stop()
        $controls.autoSendButton.Content = "自动发送"
        if ($null -ne $script:clientSocket) {
            $controls.statusLabel.Text = "已连接"
        }
    }
}

# 断开连接
function DisconnectSocket {
    if ($null -ne $script:clientSocket) {
        $script:clientSocket.Close()
        $script:clientSocket.Dispose()
        $script:clientSocket = $null
        
        $controls.connectButton.Content = "连接"
        $controls.statusLabel.Text = "未连接"
        $controls.ipTextBox.IsEnabled = $true
        $controls.portTextBox.IsEnabled = $true
    }
}

# 设置事件处理
$controls.randomDataRadio.Add_Checked({
    $controls.tempTextBox.IsEnabled = $false
    $controls.humidityTextBox.IsEnabled = $false
    $controls.pm25TextBox.IsEnabled = $false
    $controls.noiseTextBox.IsEnabled = $false
})

$controls.fixedDataRadio.Add_Checked({
    $controls.tempTextBox.IsEnabled = $true
    $controls.humidityTextBox.IsEnabled = $true
    $controls.pm25TextBox.IsEnabled = $true
    $controls.noiseTextBox.IsEnabled = $true
})

$controls.connectButton.Add_Click({
    if ($null -eq $script:clientSocket) {
        try {
            $host = $controls.ipTextBox.Text
            $port = [int]::Parse($controls.portTextBox.Text)
            
            $script:clientSocket = New-Object System.Net.Sockets.TcpClient
            $script:clientSocket.Connect($host, $port)
            
            $controls.connectButton.Content = "断开"
            $controls.statusLabel.Text = "已连接到 $host`:$port"
            $controls.ipTextBox.IsEnabled = $false
            $controls.portTextBox.IsEnabled = $false
        }
        catch {
            [System.Windows.MessageBox]::Show("无法连接到服务器: $($_.Exception.Message)", 
                "连接错误", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Error)
            $script:clientSocket = $null
        }
    }
    else {
        StopAutoSend
        DisconnectSocket
    }
})

$controls.sendOnceButton.Add_Click({
    if ($null -eq $script:clientSocket) {
        [System.Windows.MessageBox]::Show("请先连接到服务器", 
            "未连接", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Warning)
        return
    }
    SendData
})

$controls.autoSendButton.Add_Click({
    if ($script:timer.IsEnabled) {
        StopAutoSend
    }
    else {
        if ($null -eq $script:clientSocket) {
            [System.Windows.MessageBox]::Show("请先连接到服务器", 
                "未连接", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Warning)
            return
        }
        
        $interval = ValidateNumber $controls.intervalTextBox.Text 1 60 2
        $controls.intervalTextBox.Text = $interval
        
        $script:timer.Interval = [TimeSpan]::FromSeconds($interval)
        $script:timer.Start()
        $controls.autoSendButton.Content = "停止自动发送"
        $controls.statusLabel.Text = "自动发送中 (每${interval}秒)"
    }
})

# 数值验证处理器
$numberValidationFields = @(
    @{Control = $controls.tempTextBox; Min = -20; Max = 60; Default = 25; Decimals = 1},
    @{Control = $controls.humidityTextBox; Min = 0; Max = 100; Default = 50; Decimals = 1},
    @{Control = $controls.pm25TextBox; Min = 0; Max = 999; Default = 50},
    @{Control = $controls.noiseTextBox; Min = 0; Max = 120; Default = 50},
    @{Control = $controls.intervalTextBox; Min = 1; Max = 60; Default = 2}
)

foreach ($field in $numberValidationFields) {
    $field.Control.Add_LostFocus({
        param($sender, $e)
        
        $fieldInfo = $numberValidationFields | Where-Object { $_.Control -eq $sender }
        $value = ValidateNumber $sender.Text $fieldInfo.Min $fieldInfo.Max $fieldInfo.Default $fieldInfo.Decimals
        
        if ($fieldInfo.Decimals) {
            $format = "F$($fieldInfo.Decimals)"
            $sender.Text = $value.ToString($format)
        } else {
            $sender.Text = $value.ToString()
        }
    })
}

# 定时器事件
$script:timer.Add_Tick({ SendData })

# 关闭窗口事件
$window.Add_Closing({
    StopAutoSend
    DisconnectSocket
})

# 显示窗口
[void]$window.ShowDialog()