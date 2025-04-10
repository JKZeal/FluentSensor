import sys
import sqlite3
import numpy as np
from enum import Enum
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
                             QGroupBox, QFrame, QButtonGroup, QRadioButton)
from qfluentwidgets import (NavigationInterface, NavigationItemPosition, FluentWindow,
                            ComboBox, Slider, PrimaryPushButton, StyleSheetBase,
                            MessageBox, InfoBar, InfoBarPosition, PushButton,
                            RoundMenu, Action, FluentIcon, setTheme, Theme, isDarkTheme, qconfig)
from qfluentwidgets.components.widgets.acrylic_label import AcrylicBrush
import pyqtgraph as pg

DB_PATH = "sensor_data.db"


class StyleSheet(StyleSheetBase, Enum):
    """ 样式表 """
    MAIN_WINDOW = "main_window"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f"qss/{theme.value.lower()}/{self.value}.qss"


class PlotWidget(pg.PlotWidget):
    def __init__(self, title="", y_label="", dark_mode=False):
        super().__init__()

        # 保存标题和标签
        self.plot_title = title
        self.y_axis_label = y_label
        self.dark_mode = dark_mode

        # 设置基本属性
        self.setMinimumHeight(250)

        # 初始化数据
        self.data = {'time': [], 'value': []}

        # 初始化曲线 - 先创建再更新主题
        self.curve = self.plot(pen=pg.mkPen(color='white', width=2))

        # 设置底部轴为时间轴
        self.plotItem.axes['bottom']['item'].setLogMode(False)
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.plotItem.setAxisItems({'bottom': date_axis})

        # 根据主题设置外观
        self.update_theme(dark_mode)

    def set_title_and_labels(self):
        # 根据主题设置标题和标签颜色
        if self.dark_mode:
            title_color = 'white'
            text_color = 'white'
            grid_alpha = 0.2
        else:
            title_color = '#101010'  # 深黑色，在浅色背景上更清晰
            text_color = '#303030'  # 深灰色
            grid_alpha = 0.15

        # 设置网格
        self.plotItem.showGrid(x=True, y=True, alpha=grid_alpha)

        # 设置标题，在浅色主题下使用黑色文字
        self.plotItem.setTitle(
            self.plot_title,
            color=title_color,
            size="14pt",
            bold=True
        )

        # 设置坐标轴标签
        self.plotItem.setLabel('left', self.y_axis_label, color=text_color)
        self.plotItem.setLabel('bottom', 'Time', color=text_color)

        # 设置坐标轴颜色
        self.getAxis('left').setPen(text_color)
        self.getAxis('bottom').setPen(text_color)

        # 设置刻度标签颜色
        self.getAxis('left').setTextPen(text_color)

        # 设置时间轴颜色
        bottom_axis = self.getPlotItem().getAxis('bottom')
        if isinstance(bottom_axis, pg.DateAxisItem):
            bottom_axis.setPen(text_color)
            # 尝试设置文本颜色，兼容不同版本
            try:
                bottom_axis.setTextPen(text_color)
            except (AttributeError, TypeError):
                pass

    def update_theme(self, dark_mode):
        self.dark_mode = dark_mode

        # 设置颜色
        if dark_mode:
            background_color = (30, 30, 30, 255)
            curve_color = '#4ec9b0'  # 青绿色，在深色主题下更显眼
        else:
            background_color = (245, 245, 245, 255)
            curve_color = '#007acc'  # 蓝色，在浅色主题下更显眼

        # 设置背景色
        self.setBackground(background_color)

        # 更新标题和标签
        self.set_title_and_labels()

        # 更新曲线颜色
        self.curve.setPen(pg.mkPen(color=curve_color, width=2))

    def update_data(self, new_times, new_values):
        # 确保传入的是列表，而不是单个值
        if not isinstance(new_times, list):
            new_times = [new_times]
        if not isinstance(new_values, list):
            new_values = [new_values]

        # 重置数据而不是追加
        self.data['time'] = new_times
        self.data['value'] = new_values

        # 确保数据是数值类型
        x = np.array(self.data['time'], dtype=np.float64)
        y = np.array(self.data['value'], dtype=np.float64)

        # 设置数据
        self.curve.setData(x, y)

        # 如果有数据，自动缩放Y轴以适应所有点
        if len(x) > 0:
            y_min, y_max = min(y), max(y)
            padding = (y_max - y_min) * 0.1 if y_max > y_min else 1.0
            self.plotItem.setYRange(y_min - padding, y_max + padding)

            # 设置X轴的范围，确保显示完整时间范围
            x_min, x_max = min(x), max(x)
            padding_x = (x_max - x_min) * 0.05
            self.plotItem.setXRange(x_min - padding_x, x_max + padding_x)


class StyledGroupBox(QGroupBox):
    """自定义分组框，添加了Fluent UI风格"""

    def __init__(self, title, parent=None, dark_mode=False):
        super().__init__(title, parent)
        self.update_style(dark_mode)

    def update_style(self, dark_mode):
        if dark_mode:
            self.setStyleSheet("""
                QGroupBox {
                    font-size: 14px;
                    font-weight: bold;
                    border: 1px solid #555555;
                    border-radius: 6px;
                    margin-top: 12px;
                    padding-top: 10px;
                    color: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 10px;
                    padding: 0 5px;
                    color: #4cc2ff;
                }
            """)
        else:
            self.setStyleSheet("""
                QGroupBox {
                    font-size: 14px;
                    font-weight: bold;
                    border: 1px solid #d0d0d0;
                    border-radius: 6px;
                    margin-top: 12px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 10px;
                    padding: 0 5px;
                    color: #0078d4;
                }
            """)


class TimeRangeSettings(QWidget):
    # 定义信号
    timeRangeChanged = pyqtSignal(int)
    refreshRateChanged = pyqtSignal(int)
    themeChanged = pyqtSignal(bool)  # 传递是否为暗色主题

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = isDarkTheme()
        self.groups = []  # 存储所有GroupBox以便主题切换时更新
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 创建标题
        self.title_label = QLabel("数据显示设置")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(self.title_label)

        # 时间范围设置区域
        time_group = StyledGroupBox("时间范围设置", self, self.dark_mode)
        self.groups.append(time_group)
        time_layout = QVBoxLayout(time_group)

        # 添加说明
        time_label = QLabel("选择要显示的历史数据时间范围")
        time_label.setStyleSheet("font-weight: normal;")
        if not self.dark_mode:
            time_label.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-weight: normal;")
        time_layout.addWidget(time_label)

        # 创建下拉框
        combo_layout = QHBoxLayout()
        combo_label = QLabel("时间范围:")
        self.timeComboBox = ComboBox(self)
        self.timeComboBox.addItems([
            "1 分钟", "5 分钟", "15 分钟", "30 分钟",
            "1 小时", "3 小时", "12 小时", "24 小时"
        ])
        self.timeComboBox.setCurrentIndex(1)  # 默认选择5分钟
        combo_layout.addWidget(combo_label)
        combo_layout.addWidget(self.timeComboBox)
        time_layout.addLayout(combo_layout)

        # 添加时间范围组到主布局
        layout.addWidget(time_group)

        # 刷新频率设置区域
        refresh_group = StyledGroupBox("刷新频率设置", self, self.dark_mode)
        self.groups.append(refresh_group)
        refresh_layout = QVBoxLayout(refresh_group)

        # 添加说明
        refresh_label = QLabel("设置数据刷新频率")
        refresh_label.setStyleSheet("font-weight: normal;")
        if not self.dark_mode:
            refresh_label.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-weight: normal;")
        refresh_layout.addWidget(refresh_label)

        # 滑动条布局
        slider_layout = QVBoxLayout()
        self.refresh_value_label = QLabel("刷新频率: 2 秒")
        slider_layout.addWidget(self.refresh_value_label)

        self.refreshSlider = Slider(Qt.Horizontal, self)
        self.refreshSlider.setRange(1, 10)
        self.refreshSlider.setValue(2)
        self.refreshSlider.valueChanged.connect(self.on_refresh_slider_changed)
        slider_layout.addWidget(self.refreshSlider)

        refresh_layout.addLayout(slider_layout)

        # 添加刷新率组到主布局
        layout.addWidget(refresh_group)

        # 主题设置区域
        theme_group = StyledGroupBox("主题设置", self, self.dark_mode)
        self.groups.append(theme_group)
        theme_layout = QVBoxLayout(theme_group)

        theme_desc = QLabel("选择应用主题")
        theme_desc.setStyleSheet("font-weight: normal;")
        if not self.dark_mode:
            theme_desc.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-weight: normal;")
        theme_layout.addWidget(theme_desc)

        # 创建单选按钮
        radio_layout = QHBoxLayout()
        self.theme_button_group = QButtonGroup(self)

        self.light_radio = QRadioButton("浅色主题", self)
        self.dark_radio = QRadioButton("深色主题", self)

        # 根据当前主题设置默认选中状态
        self.light_radio.setChecked(not self.dark_mode)
        self.dark_radio.setChecked(self.dark_mode)

        self.theme_button_group.addButton(self.light_radio, 0)
        self.theme_button_group.addButton(self.dark_radio, 1)

        radio_layout.addWidget(self.light_radio)
        radio_layout.addWidget(self.dark_radio)
        radio_layout.addStretch()

        theme_layout.addLayout(radio_layout)
        layout.addWidget(theme_group)

        # 添加一个分隔线
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        if self.dark_mode:
            self.separator.setStyleSheet("background-color: #555555; height: 1px;")
        else:
            self.separator.setStyleSheet("background-color: #e0e0e0; height: 1px;")
        layout.addWidget(self.separator)

        # 应用按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.applyButton = PrimaryPushButton("应用设置")
        self.applyButton.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.applyButton)
        layout.addLayout(button_layout)

        # 填充空白
        layout.addStretch()

    def update_theme(self, dark_mode):
        """更新所有组件的主题"""
        self.dark_mode = dark_mode

        # 更新所有分组框样式
        for group in self.groups:
            group.update_style(dark_mode)

        # 更新分隔线颜色
        if dark_mode:
            self.separator.setStyleSheet("background-color: #555555; height: 1px;")
            # 更新说明文本颜色
            for child in self.findChildren(QLabel):
                if "font-weight: normal" in child.styleSheet():
                    child.setStyleSheet("color: #cccccc; font-weight: normal;")
        else:
            self.separator.setStyleSheet("background-color: #e0e0e0; height: 1px;")
            # 更新说明文本颜色
            for child in self.findChildren(QLabel):
                if "font-weight: normal" in child.styleSheet():
                    child.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-weight: normal;")

        # 更新标题颜色
        if dark_mode:
            self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px; color: white;")
        else:
            self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px; color: #333333;")

    def on_refresh_slider_changed(self, value):
        self.refresh_value_label.setText(f"刷新频率: {value} 秒")

    def apply_settings(self):
        # 1. 发出时间范围改变信号
        time_ranges = [1, 5, 15, 30, 60, 180, 720, 1440]  # 分钟
        index = self.timeComboBox.currentIndex()
        self.timeRangeChanged.emit(time_ranges[index])

        # 2. 发出刷新频率改变信号
        refresh_rate = self.refreshSlider.value()
        self.refreshRateChanged.emit(refresh_rate)

        # 3. 发出主题改变信号
        dark_mode = self.dark_radio.isChecked()
        if dark_mode != self.dark_mode:
            self.themeChanged.emit(dark_mode)
            self.update_theme(dark_mode)

        # 显示一个提示，告诉用户设置已经应用
        InfoBar.success(
            title='设置已应用',
            content=f"已更新时间范围为 {self.timeComboBox.currentText()}，刷新频率为 {refresh_rate} 秒",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # 创建qss目录
        self.create_qss_folders()

        # 初始化界面
        self.setWindowTitle("Sensor Data Monitor")
        self.resize(1200, 800)

        # 创建亚克力效果
        self.acrylic = AcrylicBrush(self, 30)
        self.setStyleSheet("background: transparent")

        # 设置查询时间范围
        self.time_range_minutes = 5  # 默认改为5分钟

        # 默认使用当前主题设置
        self.dark_mode = isDarkTheme()

        # 先创建主界面容器并设置objectName
        self.main_widget = QWidget()
        self.main_widget.setObjectName("mainWidget")  # 必须设置objectName
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 创建4个图表
        self.init_plots()

        # 创建导航栏
        self.init_navigation()

        # 定时更新数据
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_all_plots)
        self.timer.start(2000)  # 每2秒更新一次

    def create_qss_folders(self):
        """创建样式表文件夹结构"""
        import os

        # 创建目录
        os.makedirs("qss/light", exist_ok=True)
        os.makedirs("qss/dark", exist_ok=True)

        # 创建浅色主题样式文件
        with open("qss/light/main_window.qss", "w") as f:
            f.write("""
            QWidget {
                background-color: transparent;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
            QRadioButton {
                color: #333333;
            }
            """)

        # 创建深色主题样式文件
        with open("qss/dark/main_window.qss", "w") as f:
            f.write("""
            QWidget {
                background-color: transparent;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QRadioButton {
                color: #ffffff;
            }
            """)

    # 在 init_navigation 方法中做以下调整
    def init_navigation(self):
        # 添加导航项 - 改用正确的 fluent icon 常量
        self.addSubInterface(self.main_widget, FluentIcon.SPEED_HIGH, "环境监测")

        # 创建分析界面（改用 CHART）
        self.analytics_widget = QWidget()
        self.analytics_widget.setObjectName("alarmWidget")
        self.addSubInterface(self.analytics_widget,
                             FluentIcon.RINGER,
                             "报警规则",
                             NavigationItemPosition.SCROLL)

        # 创建历史界面（改用 HISTORY）
        self.history_widget = QWidget()
        self.history_widget.setObjectName("historyWidget")
        self.addSubInterface(self.history_widget,
                             FluentIcon.HISTORY,
                             "历史数据",
                             NavigationItemPosition.SCROLL)

        # 添加底部导航项
        self.navigationInterface.addSeparator()

        # 创建设置界面
        self.settings_widget = TimeRangeSettings()
        self.settings_widget.setObjectName("settingsWidget")
        self.settings_widget.timeRangeChanged.connect(self.on_time_range_changed)
        self.settings_widget.refreshRateChanged.connect(self.set_refresh_rate)
        self.settings_widget.themeChanged.connect(self.on_theme_changed)
        self.addSubInterface(self.settings_widget,
                             FluentIcon.SETTING,
                             "设置",
                             NavigationItemPosition.BOTTOM)

        self.about_widget = QWidget()
        self.about_widget.setObjectName("aboutWidget")
        self.addSubInterface(self.about_widget,
                             FluentIcon.INFO,
                             "关于",
                             NavigationItemPosition.BOTTOM)

    def init_plots(self):
        # 温度图表
        self.temp_plot = PlotWidget("温度", "°C", self.dark_mode)
        self.main_layout.addWidget(self.temp_plot)

        # 湿度图表
        self.humidity_plot = PlotWidget("湿度", "%", self.dark_mode)
        self.main_layout.addWidget(self.humidity_plot)

        # PM2.5图表
        self.pm25_plot = PlotWidget("PM2.5", "μg/m³", self.dark_mode)
        self.main_layout.addWidget(self.pm25_plot)

        # 噪声图表
        self.noise_plot = PlotWidget("噪声", "dB", self.dark_mode)
        self.main_layout.addWidget(self.noise_plot)

        # 设置图表样式
        for plot in [self.temp_plot, self.humidity_plot, self.pm25_plot, self.noise_plot]:
            plot.setFixedHeight(190)  # 减小高度以适应4个图表

    def on_time_range_changed(self, minutes):
        self.time_range_minutes = minutes
        self.update_all_plots()  # 立即更新图表以反映新的时间范围

    def set_refresh_rate(self, seconds):
        """设置数据刷新频率"""
        self.timer.stop()
        self.timer.start(seconds * 1000)  # 转换为毫秒

    def on_theme_changed(self, dark_mode):
        """切换主题"""
        self.dark_mode = dark_mode
        theme = Theme.DARK if dark_mode else Theme.LIGHT
        setTheme(theme)

        # 更新所有图表的主题
        for plot in [self.temp_plot, self.humidity_plot, self.pm25_plot, self.noise_plot]:
            plot.update_theme(dark_mode)

        # 应用主题样式表
        StyleSheet.MAIN_WINDOW.apply(self)

    def fetch_recent_data(self, minutes=5):
        """获取最近X分钟的数据"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes)

            cursor.execute(
                "SELECT timestamp, temperature, humidity, pm25, noise "
                "FROM sensor_data "
                "WHERE timestamp BETWEEN ? AND ? "
                "ORDER BY timestamp",
                (start_time.strftime("%Y-%m-%d %H:%M:%S"),
                 end_time.strftime("%Y-%m-%d %H:%M:%S"))
            )

            data = cursor.fetchall()
            conn.close()
            return data
        except Exception as e:
            print(f"数据库查询错误: {e}")
            return []

    def update_all_plots(self):
        # 使用当前设置的时间范围获取数据
        data = self.fetch_recent_data(self.time_range_minutes)

        if not data:
            return

        # 转换时间戳为浮点数
        times = []
        temps = []
        humids = []
        pm25s = []
        noises = []

        for row in data:
            try:
                t = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                timestamp = t.timestamp()
                times.append(timestamp)
                temps.append(float(row[1]))
                humids.append(float(row[2]))
                pm25s.append(float(row[3]))
                noises.append(float(row[4]))
            except (ValueError, TypeError) as e:
                print(f"跳过错误数据行: {row}, 错误: {e}")
                continue

        # 更新各图表
        if times:  # 确保有数据再更新
            self.temp_plot.update_data(times, temps)
            self.humidity_plot.update_data(times, humids)
            self.pm25_plot.update_data(times, pm25s)
            self.noise_plot.update_data(times, noises)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 设置初始主题
    setTheme(Theme.LIGHT)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())