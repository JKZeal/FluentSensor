import sqlite3
import sys
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDate, QSize
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (QApplication, QFileDialog,
                             QGridLayout, QTableWidgetItem, QVBoxLayout,
                             QHBoxLayout, QWidget, QButtonGroup, QDialog)

from qfluentwidgets import (
    NavigationItemPosition, FluentWindow, FluentIcon,
    ComboBox, Slider, PrimaryPushButton, StyleSheetBase, PushButton,
    InfoBar, InfoBarPosition, TransparentToolButton,
    setTheme, Theme, isDarkTheme, qconfig, CheckBox,
    ZhDatePicker, TableWidget, SingleDirectionScrollArea,
    CardWidget, ElevatedCardWidget, HeaderCardWidget, BodyLabel,
    CaptionLabel, IconWidget, RadioButton, StrongBodyLabel
)

DB_PATH = "db/sensor_data.db"


class StyleSheet(StyleSheetBase, Enum):
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
        self.setMinimumHeight(240)
        self.setBackground(None)

        # 初始化数据
        self.data = {'time': [], 'value': []}

        # 初始化曲线
        self.curve = self.plot(pen=pg.mkPen(color='#0078d4', width=2.5))

        # 设置底部轴为时间轴
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.plotItem.setAxisItems({'bottom': date_axis})

        # 设置字体
        font = QFont()
        font.setFamily("Microsoft YaHei UI")
        font.setPointSize(9)
        self.getAxis('bottom').tickFont = font
        self.getAxis('left').tickFont = font

        # 根据主题设置外观
        self.update_theme(dark_mode)

    def update_theme(self, dark_mode):
        self.dark_mode = dark_mode

        # 设置颜色
        if dark_mode:
            bg_color = QColor(30, 30, 30, 0)  # 完全透明背景
            curve_color = '#60cdff'
            text_color = '#ffffff'
            title_color = '#ffffff'
            grid_alpha = 0.2
        else:
            bg_color = QColor(250, 250, 250, 0)  # 完全透明背景
            curve_color = '#0078d4'
            text_color = '#202020'
            title_color = '#000000'
            grid_alpha = 0.15

        # 设置背景色和网格
        self.setBackground(bg_color)
        self.plotItem.showGrid(x=True, y=True, alpha=grid_alpha)

        # 设置标题
        if self.plot_title:
            self.plotItem.setTitle(self.plot_title, color=title_color, size="13pt", bold=True)

        # 设置坐标轴标签和样式
        self.plotItem.setLabel('left', self.y_axis_label, color=text_color)
        self.plotItem.setLabel('bottom', 'Time', color=text_color)

        # 设置坐标轴颜色与主题匹配
        self.getAxis('left').setPen(pg.mkPen(color=text_color, width=1))
        self.getAxis('bottom').setPen(pg.mkPen(color=text_color, width=1))
        self.getAxis('left').setTextPen(text_color)
        self.getAxis('bottom').setTextPen(text_color)

        # 修改底部和左侧轴的背景，使其与卡片融合
        for axis in ['left', 'bottom']:
            ax = self.getAxis(axis)
            # 尝试适用于不同版本的pyqtgraph
            try:
                # 新版本可能直接支持设置背景透明
                ax.setStyle(brush=QColor(0, 0, 0, 0))
            except:
                # 对于旧版本，我们尝试不同的方法或简单忽略
                pass

        # 更新曲线颜色
        self.curve.setPen(pg.mkPen(color=curve_color, width=2.5))

    def update_data(self, new_times, new_values):
        # 确保传入的是列表
        if not isinstance(new_times, list):
            new_times = [new_times]
        if not isinstance(new_values, list):
            new_values = [new_values]

        # 更新数据
        self.data['time'] = new_times
        self.data['value'] = new_values

        # 设置数据
        self.curve.setData(np.array(new_times, dtype=np.float64), np.array(new_values, dtype=np.float64))

        # 自动缩放以适应所有点
        if new_times:
            # 计算适当的范围
            x_min = min(new_times)
            x_max = max(new_times)
            y_min = min(new_values)
            y_max = max(new_values)

            # 添加一些边距
            padding_x = (x_max - x_min) * 0.05 if x_min != x_max else 86400
            padding_y = (y_max - y_min) * 0.1 if y_min != y_max else 1

            # 设置范围
            self.plotItem.setXRange(x_min - padding_x, x_max + padding_x)
            self.plotItem.setYRange(y_min - padding_y, y_max + padding_y)


class PlotCard(HeaderCardWidget):
    def __init__(self, title, y_label, dark_mode=False, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setBorderRadius(8)

        # 使用空标题创建图表，避免重复
        self.plot_widget = PlotWidget("", y_label, dark_mode)
        self.plot_widget.setMinimumHeight(240)

        # 添加到卡片主视图
        self.viewLayout.addWidget(self.plot_widget)

    def update_data(self, times, values):
        self.plot_widget.update_data(times, values)

    def update_theme(self, dark_mode):
        self.plot_widget.update_theme(dark_mode)


class PlotsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("plotsWidget")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 创建标题
        self.title_label = BodyLabel("数据图表", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        # 创建图表滚动区域
        self.scroll_area = SingleDirectionScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollArea > QWidget {
                background: transparent;
            }
        """)

        # 创建图表容器
        self.plots_container = QWidget()
        self.plots_container.setObjectName("plotsContainerWidget")
        self.plots_container.setStyleSheet("""
            #plotsContainerWidget {
                background: transparent;
                border: none;
            }
        """)
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.setSpacing(16)

        # 使用当前主题创建图表
        dark_mode = isDarkTheme()
        self.temp_plot = PlotCard("温度趋势", "温度 (°C)", dark_mode)
        self.humidity_plot = PlotCard("湿度趋势", "湿度 (%)", dark_mode)
        self.pm25_plot = PlotCard("PM2.5趋势", "PM2.5 (μg/m³)", dark_mode)
        self.noise_plot = PlotCard("噪声趋势", "噪声 (dB)", dark_mode)

        # 添加图表到容器
        self.plots_layout.addWidget(self.temp_plot)
        self.plots_layout.addWidget(self.humidity_plot)
        self.plots_layout.addWidget(self.pm25_plot)
        self.plots_layout.addWidget(self.noise_plot)

        # 设置滚动区域的部件
        self.scroll_area.setWidget(self.plots_container)

        # 添加滚动区域到主布局
        layout.addWidget(self.scroll_area, 1)

    def update_data(self, times=None, temp_history=None, humidity_history=None, pm25_history=None, noise_history=None):
        """更新显示的数据"""
        if times is not None:
            if temp_history is not None:
                self.temp_plot.update_data(times, temp_history)
            if humidity_history is not None:
                self.humidity_plot.update_data(times, humidity_history)
            if pm25_history is not None:
                self.pm25_plot.update_data(times, pm25_history)
            if noise_history is not None:
                self.noise_plot.update_data(times, noise_history)

    def update_theme(self, dark_mode):
        """更新主题"""
        self.temp_plot.update_theme(dark_mode)
        self.humidity_plot.update_theme(dark_mode)
        self.pm25_plot.update_theme(dark_mode)
        self.noise_plot.update_theme(dark_mode)


class RealtimeDataCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("实时环境数据")
        self.setBorderRadius(8)

        # 指标容器 - 使用网格布局
        indicator_layout = QGridLayout()
        indicator_layout.setHorizontalSpacing(16)
        indicator_layout.setVerticalSpacing(12)

        # 创建时间戳和四个指标卡片
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_indicator = self._create_indicator("更新时间", current_time, FluentIcon.HISTORY, time_card=True)
        self.temp_indicator = self._create_indicator("温度", "0°C", FluentIcon.CALORIES)
        self.humidity_indicator = self._create_indicator("湿度", "0%", FluentIcon.CLOUD)
        self.pm25_indicator = self._create_indicator("PM2.5", "0 μg/m³", FluentIcon.LEAF)
        self.noise_indicator = self._create_indicator("噪声", "0 dB", FluentIcon.SPEAKERS)

        # 添加到网格布局中 - 分三行两列
        # 第一行放时间指标，跨两列
        indicator_layout.addWidget(self.time_indicator, 0, 0, 1, 2)
        # 第二行和第三行放其他指标
        indicator_layout.addWidget(self.temp_indicator, 1, 0)
        indicator_layout.addWidget(self.humidity_indicator, 1, 1)
        indicator_layout.addWidget(self.pm25_indicator, 2, 0)
        indicator_layout.addWidget(self.noise_indicator, 2, 1)

        # 设置列伸展
        indicator_layout.setColumnStretch(0, 1)
        indicator_layout.setColumnStretch(1, 1)

        # 添加指标布局到卡片的主视图
        self.viewLayout.addLayout(indicator_layout)

    def _create_indicator(self, name, value, icon, time_card=False):
        """创建单个指标卡片"""
        card = ElevatedCardWidget()
        card.setBorderRadius(8)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 添加图标和名称到一行
        header_layout = QHBoxLayout()
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(20, 20)
        name_label = CaptionLabel(name)
        name_label.setStyleSheet("font-size: 13px; font-weight: 500; color: var(--text-color-secondary);")

        header_layout.addWidget(icon_widget)
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        # 添加值标签
        value_label = BodyLabel(value)
        value_label.setObjectName(f"{name.lower().replace('.', '_')}_value")

        # 为时间卡片设置不同的样式
        if time_card:
            value_label.setStyleSheet("font-size: 16px; font-weight: 600;")
            card.setMinimumHeight(100)
        else:
            value_label.setStyleSheet("font-size: 22px; font-weight: 600;")
            card.setMinimumHeight(100)

        value_label.setAlignment(Qt.AlignCenter)

        layout.addLayout(header_layout)
        layout.addWidget(value_label)

        return card

    def update_data(self, temperature=None, humidity=None, pm25=None, noise=None, timestamp=None):
        """更新显示的数据"""
        # 更新时间
        if timestamp:
            self.time_indicator.findChild(BodyLabel, "更新时间_value").setText(timestamp)
        else:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_indicator.findChild(BodyLabel, "更新时间_value").setText(current_time)

        # 更新指标值
        if temperature is not None:
            self.temp_indicator.findChild(BodyLabel, "温度_value").setText(f"{temperature:.1f}°C")

        if humidity is not None:
            self.humidity_indicator.findChild(BodyLabel, "湿度_value").setText(f"{humidity:.1f}%")

        if pm25 is not None:
            self.pm25_indicator.findChild(BodyLabel, "pm2_5_value").setText(f"{pm25:.0f} μg/m³")

        if noise is not None:
            self.noise_indicator.findChild(BodyLabel, "噪声_value").setText(f"{noise:.0f} dB")


class TimeRangeSettings(QWidget):
    timeRangeChanged = pyqtSignal(int)
    refreshRateChanged = pyqtSignal(int)
    themeChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timeRangeSettings")
        self.dark_mode = isDarkTheme()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 创建标题
        self.title_label = BodyLabel("系统设置", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        # 时间范围设置区域
        self.time_card = HeaderCardWidget(self)
        self.time_card.setTitle("时间范围")
        self.time_card.setBorderRadius(8)

        # 创建下拉框
        combo_layout = QHBoxLayout()
        combo_label = BodyLabel("显示历史数据时间范围:", self.time_card)
        self.timeComboBox = ComboBox(self.time_card)
        self.timeComboBox.addItems(["1 分钟", "5 分钟", "15 分钟", "30 分钟",
                                    "1 小时", "3 小时", "12 小时", "24 小时"])
        self.timeComboBox.setCurrentIndex(1)  # 默认选择5分钟
        combo_layout.addWidget(combo_label)
        combo_layout.addWidget(self.timeComboBox)
        combo_layout.addStretch()

        self.time_card.viewLayout.addLayout(combo_layout)

        layout.addWidget(self.time_card)

        # 刷新频率设置区域
        self.refresh_card = HeaderCardWidget(self)
        self.refresh_card.setTitle("刷新频率")
        self.refresh_card.setBorderRadius(8)

        # 修改为水平布局，将文本和滑动条左右排列
        slider_layout = QHBoxLayout()
        self.refresh_value_label = BodyLabel("数据更新间隔: 2 秒", self.refresh_card)
        self.refresh_value_label.setMinimumWidth(150)  # 确保文本有足够宽度
        slider_layout.addWidget(self.refresh_value_label)

        self.refreshSlider = Slider(Qt.Horizontal, self.refresh_card)
        self.refreshSlider.setRange(1, 10)
        self.refreshSlider.setValue(2)
        self.refreshSlider.valueChanged.connect(self.on_refresh_slider_changed)
        slider_layout.addWidget(self.refreshSlider)

        self.refresh_card.viewLayout.addLayout(slider_layout)
        layout.addWidget(self.refresh_card)

        # 主题设置区域
        self.theme_card = HeaderCardWidget(self)
        self.theme_card.setTitle("外观主题")
        self.theme_card.setBorderRadius(8)

        # 创建单选按钮
        radio_layout = QHBoxLayout()
        self.theme_button_group = QButtonGroup(self)

        self.light_radio = RadioButton("浅色主题", self.theme_card)
        self.dark_radio = RadioButton("深色主题", self.theme_card)

        self.light_radio.setChecked(not self.dark_mode)
        self.dark_radio.setChecked(self.dark_mode)

        self.theme_button_group.addButton(self.light_radio, 0)
        self.theme_button_group.addButton(self.dark_radio, 1)

        radio_layout.addWidget(self.light_radio)
        radio_layout.addWidget(self.dark_radio)
        radio_layout.addStretch()

        self.theme_card.viewLayout.addLayout(radio_layout)
        layout.addWidget(self.theme_card)

        # 应用按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.applyButton = PrimaryPushButton("应用设置", self)
        self.applyButton.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.applyButton)
        layout.addLayout(button_layout)

        # 填充空白
        layout.addStretch()

    def on_refresh_slider_changed(self, value):
        self.refresh_value_label.setText(f"数据更新间隔: {value} 秒")

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
            self.dark_mode = dark_mode

        # 显示提示
        InfoBar.success(
            title='设置已应用',
            content='您的设置已成功应用',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )


class EnvironmentStatusWidget(QWidget):
    """环境状态指标小部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 创建4个状态标签
        self.temp_status = StrongBodyLabel("适宜")
        self.temp_status.setFixedHeight(28)
        self.temp_status.setAlignment(Qt.AlignCenter)
        self.temp_status.setObjectName("tempLabel")

        self.humidity_status = StrongBodyLabel("适宜")
        self.humidity_status.setFixedHeight(28)
        self.humidity_status.setAlignment(Qt.AlignCenter)
        self.humidity_status.setObjectName("humidityLabel")

        self.pm25_status = StrongBodyLabel("良好")
        self.pm25_status.setFixedHeight(28)
        self.pm25_status.setAlignment(Qt.AlignCenter)
        self.pm25_status.setObjectName("pm25Label")

        self.noise_status = StrongBodyLabel("安静")
        self.noise_status.setFixedHeight(28)
        self.noise_status.setAlignment(Qt.AlignCenter)
        self.noise_status.setObjectName("noiseLabel")

        # 设置标签样式
        self._setup_label_style(self.temp_status)
        self._setup_label_style(self.humidity_status)
        self._setup_label_style(self.pm25_status)
        self._setup_label_style(self.noise_status)

        # 设置初始状态颜色
        self.set_status_colors("适宜", "适宜", "良好", "安静")

        # 添加到布局
        layout.addWidget(self.temp_status)
        layout.addWidget(self.humidity_status)
        layout.addWidget(self.pm25_status)
        layout.addWidget(self.noise_status)

    def _setup_label_style(self, label):
        """设置标签的基础样式"""
        label.setStyleSheet("""
            StrongBodyLabel {
                border-radius: 4px;
                padding: 2px 8px;
                color: white;
                font-weight: bold;
            }
        """)

    def set_status_colors(self, temp_status, humidity_status, pm25_status, noise_status):
        """设置状态颜色"""
        # 设置温度状态
        self.temp_status.setText(temp_status)
        if temp_status == "寒冷":
            self.temp_status.setStyleSheet("""
                StrongBodyLabel#tempLabel {
                    background-color: #007ad9;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        elif temp_status == "适宜":
            self.temp_status.setStyleSheet("""
                StrongBodyLabel#tempLabel {
                    background-color: #16a34a;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        else:  # 炎热
            self.temp_status.setStyleSheet("""
                StrongBodyLabel#tempLabel {
                    background-color: #e11d48;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)

        # 设置湿度状态
        self.humidity_status.setText(humidity_status)
        if humidity_status == "干燥":
            self.humidity_status.setStyleSheet("""
                StrongBodyLabel#humidityLabel {
                    background-color: #eab308;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        elif humidity_status == "适宜":
            self.humidity_status.setStyleSheet("""
                StrongBodyLabel#humidityLabel {
                    background-color: #16a34a;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        else:  # 潮湿
            self.humidity_status.setStyleSheet("""
                StrongBodyLabel#humidityLabel {
                    background-color: #0284c7;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)

        # 设置PM2.5状态
        self.pm25_status.setText(pm25_status)
        if pm25_status == "良好":
            self.pm25_status.setStyleSheet("""
                StrongBodyLabel#pm25Label {
                    background-color: #16a34a;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        elif pm25_status == "轻度污染":
            self.pm25_status.setStyleSheet("""
                StrongBodyLabel#pm25Label {
                    background-color: #eab308;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        else:  # 重度污染
            self.pm25_status.setStyleSheet("""
                StrongBodyLabel#pm25Label {
                    background-color: #e11d48;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)

        # 设置噪声状态
        self.noise_status.setText(noise_status)
        if noise_status == "安静":
            self.noise_status.setStyleSheet("""
                StrongBodyLabel#noiseLabel {
                    background-color: #16a34a;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        elif noise_status == "一般":
            self.noise_status.setStyleSheet("""
                StrongBodyLabel#noiseLabel {
                    background-color: #eab308;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)
        else:  # 嘈杂
            self.noise_status.setStyleSheet("""
                StrongBodyLabel#noiseLabel {
                    background-color: #e11d48;
                    border-radius: 4px;
                    padding: 2px 8px;
                    color: white;
                    font-weight: bold;
                }
            """)


class HistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyWidget")
        self.dark_mode = isDarkTheme()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 创建标题
        self.title_label = BodyLabel("历史记录", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        # 日期选择区域
        self.date_card = HeaderCardWidget(self)
        self.date_card.setTitle("选择日期")
        self.date_card.setBorderRadius(8)

        # 日期选择器和查询按钮的水平布局
        picker_layout = QHBoxLayout()

        # 添加中文日期选择器
        self.date_picker = ZhDatePicker(self.date_card)
        self.date_picker.setDate(QDate.currentDate())
        picker_layout.addWidget(self.date_picker)

        # 添加查询按钮
        self.query_button = PrimaryPushButton("查询", self.date_card)
        self.query_button.clicked.connect(self.query_data)
        picker_layout.addWidget(self.query_button)

        # 添加导出按钮
        self.export_button = PushButton("导出为CSV", self.date_card)
        self.export_button.clicked.connect(self.export_data)
        picker_layout.addWidget(self.export_button)

        picker_layout.addStretch()

        self.date_card.viewLayout.addLayout(picker_layout)
        layout.addWidget(self.date_card)

        # 数据展示区域
        self.results_card = HeaderCardWidget(self)
        self.results_card.setTitle("查询结果")
        self.results_card.setBorderRadius(8)

        # 添加表格
        self.table = TableWidget(self.results_card)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setColumnCount(6)

        # 禁止编辑表格
        self.table.setEditTriggers(TableWidget.NoEditTriggers)

        # 设置表头
        self.table.setHorizontalHeaderLabels(['时间', '温度(°C)', '湿度(%)', 'PM2.5(μg/m³)', '噪声(dB)', '状态'])
        self.table.verticalHeader().hide()
        self.table.setSelectRightClickedRow(True)

        # 设置表格大小策略
        self.table.horizontalHeader().setStretchLastSection(True)

        # 添加表格到结果卡片
        self.results_card.viewLayout.addWidget(self.table)

        # 将结果卡片添加到主布局
        layout.addWidget(self.results_card, 1)

    def query_data(self):
        """根据选择的日期查询数据"""
        selected_date = self.date_picker.getDate()
        date_str = selected_date.toString("yyyy-MM-dd")

        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            cursor = conn.cursor()

            # 构建日期范围查询
            start_date = f"{date_str} 00:00:00"
            end_date = f"{date_str} 23:59:59"

            # 执行查询
            cursor.execute("""
                SELECT timestamp, temperature, humidity, pm25, noise
                FROM sensor_data
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """, (start_date, end_date))

            # 获取结果
            results = cursor.fetchall()
            conn.close()

            # 更新表格
            self.update_table(results)

            # 显示成功消息
            if results:
                InfoBar.success(
                    title='查询成功',
                    content=f'找到 {len(results)} 条记录',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self.window()
                )
            else:
                InfoBar.info(
                    title='无数据',
                    content=f'所选日期 {date_str} 没有记录',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self.window()
                )

        except Exception as e:
            InfoBar.error(
                title='查询错误',
                content=f'发生错误: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )

    def update_table(self, data):
        """更新表格数据"""
        self.table.setRowCount(0)

        if not data:
            return

        # 定义环境评估阈值
        thresholds = {
            'temp': {'寒冷': (-20, 10), '适宜': (10, 26), '炎热': (26, 50)},
            'humidity': {'干燥': (0, 40), '适宜': (40, 70), '潮湿': (70, 100)},
            'pm25': {'良好': (0, 35), '轻度污染': (35, 75), '重度污染': (75, 1000)},
            'noise': {'安静': (0, 45), '一般': (45, 65), '嘈杂': (65, 120)}
        }

        for row_idx, row_data in enumerate(data):
            self.table.insertRow(row_idx)

            # 时间戳
            timestamp_item = QTableWidgetItem(row_data[0])
            self.table.setItem(row_idx, 0, timestamp_item)

            # 温度
            temp = row_data[1]
            temp_item = QTableWidgetItem(f"{temp:.1f}")
            self.table.setItem(row_idx, 1, temp_item)

            # 湿度
            humidity = row_data[2]
            humidity_item = QTableWidgetItem(f"{humidity:.1f}")
            self.table.setItem(row_idx, 2, humidity_item)

            # PM2.5
            pm25 = row_data[3]
            pm25_item = QTableWidgetItem(f"{pm25}")
            self.table.setItem(row_idx, 3, pm25_item)

            # 噪声
            noise = row_data[4]
            noise_item = QTableWidgetItem(f"{noise}")
            self.table.setItem(row_idx, 4, noise_item)

            # 设置指标状态 - 使用新的状态显示方式
            temp_status = self._evaluate_temp(temp, thresholds['temp'])
            humidity_status = self._evaluate_humidity(humidity, thresholds['humidity'])
            pm25_status = self._evaluate_pm25(pm25, thresholds['pm25'])
            noise_status = self._evaluate_noise(noise, thresholds['noise'])

            # 创建状态小部件
            status_widget = EnvironmentStatusWidget()
            status_widget.set_status_colors(temp_status, humidity_status, pm25_status, noise_status)

            # 将小部件添加到表格单元格
            self.table.setCellWidget(row_idx, 5, status_widget)

        # 调整列宽
        self.table.resizeColumnsToContents()

        # 确保状态列有足够的宽度
        self.table.setColumnWidth(5, 300)

    def _evaluate_temp(self, value, thresholds):
        """评估温度状态"""
        if value < thresholds['适宜'][0]:
            return "寒冷"
        elif value > thresholds['适宜'][1]:
            return "炎热"
        return "适宜"

    def _evaluate_humidity(self, value, thresholds):
        """评估湿度状态"""
        if value < thresholds['适宜'][0]:
            return "干燥"
        elif value > thresholds['适宜'][1]:
            return "潮湿"
        return "适宜"

    def _evaluate_pm25(self, value, thresholds):
        """评估PM2.5状态"""
        if value <= thresholds['良好'][1]:
            return "良好"
        elif value <= thresholds['轻度污染'][1]:
            return "轻度污染"
        return "重度污染"

    def _evaluate_noise(self, value, thresholds):
        """评估噪声状态"""
        if value <= thresholds['安静'][1]:
            return "安静"
        elif value <= thresholds['一般'][1]:
            return "一般"
        return "嘈杂"

    def export_data(self):
        """导出表格数据为CSV文件"""
        if self.table.rowCount() == 0:
            InfoBar.warning(
                title='导出失败',
                content='没有数据可导出',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 获取选定的日期作为文件名
        selected_date = self.date_picker.getDate().toString("yyyy-MM-dd")
        default_name = f"环境数据_{selected_date}.csv"

        # 使用系统对话框获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存CSV文件",
            default_name,
            "CSV 文件 (*.csv)"
        )

        if not file_path:  # 用户取消了保存
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                # 写入表头
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                f.write(','.join(headers) + '\n')

                # 写入数据 - 需要特殊处理状态列，因为它是一个组件
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        if col == 5:  # 状态列
                            status_widget = self.table.cellWidget(row, col)
                            temp_status = status_widget.temp_status.text()
                            humidity_status = status_widget.humidity_status.text()
                            pm25_status = status_widget.pm25_status.text()
                            noise_status = status_widget.noise_status.text()
                            row_data.append(f"{temp_status},{humidity_status},{pm25_status},{noise_status}")
                        else:
                            item = self.table.item(row, col)
                            row_data.append(item.text() if item else '')
                    f.write(','.join(row_data) + '\n')

            InfoBar.success(
                title='导出成功',
                content=f'数据已保存至 {file_path}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        except Exception as e:
            InfoBar.error(
                title='导出失败',
                content=f'发生错误: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )

    def update_theme(self, dark_mode):
        """更新所有组件的主题"""
        self.dark_mode = dark_mode
        # 更新标题和标签颜色会由全局主题处理


class AlarmRule:
    """警报规则数据类"""

    def __init__(self, sensor_type, condition_type, threshold, notification_type):
        self.id = id(self)  # 使用对象ID作为唯一标识
        self.sensor_type = sensor_type  # 'temperature', 'humidity', 'pm25', 'noise'
        self.condition_type = condition_type  # '>=', '<', 'and', 'or'
        self.threshold = threshold  # 阈值
        self.notification_type = notification_type  # ['message', 'sound']
        self.is_active = True  # 规则是否处于活动状态

    def check_condition(self, value):
        """检查条件是否满足"""
        if self.condition_type == ">=":
            return value >= self.threshold
        elif self.condition_type == "<":
            return value < self.threshold
        return False

    def get_description(self):
        """获取规则描述"""
        sensor_names = {
            'temperature': '温度',
            'humidity': '湿度',
            'pm25': 'PM2.5',
            'noise': '噪声'
        }
        condition_symbols = {
            '>=': '≥',
            '<': '<'
        }
        units = {
            'temperature': '°C',
            'humidity': '%',
            'pm25': 'μg/m³',
            'noise': 'dB'
        }
        notification_names = {
            'message': '消息提醒',
            'sound': '音频提醒',
            'message,sound': '消息+音频'
        }

        return f"{sensor_names[self.sensor_type]} {condition_symbols[self.condition_type]} {self.threshold}{units[self.sensor_type]} → {notification_names[self.notification_type]}"


class AlarmRuleDialog(QDialog):  # 修改为继承QDialog而不是QWidget
    """添加警报规则对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)  # 使用QDialog初始化
        self.setWindowTitle("添加警报规则")
        self.resize(400, 300)
        self.rule = None  # 存储创建的规则
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 传感器类型卡片
        sensor_card = HeaderCardWidget(self)
        sensor_card.setTitle("选择指标")
        sensor_card.setBorderRadius(8)
        sensor_layout = QVBoxLayout()

        self.temperature_radio = RadioButton("温度", sensor_card)
        self.humidity_radio = RadioButton("湿度", sensor_card)
        self.pm25_radio = RadioButton("PM2.5", sensor_card)
        self.noise_radio = RadioButton("噪声", sensor_card)

        self.temperature_radio.setChecked(True)

        self.sensor_group = QButtonGroup(self)
        self.sensor_group.addButton(self.temperature_radio, 0)
        self.sensor_group.addButton(self.humidity_radio, 1)
        self.sensor_group.addButton(self.pm25_radio, 2)
        self.sensor_group.addButton(self.noise_radio, 3)

        sensor_layout.addWidget(self.temperature_radio)
        sensor_layout.addWidget(self.humidity_radio)
        sensor_layout.addWidget(self.pm25_radio)
        sensor_layout.addWidget(self.noise_radio)

        sensor_card.viewLayout.addLayout(sensor_layout)
        layout.addWidget(sensor_card)

        # 条件设置卡片
        condition_card = HeaderCardWidget(self)
        condition_card.setTitle("设置条件")
        condition_card.setBorderRadius(8)
        condition_layout = QVBoxLayout()

        # 条件类型
        condition_type_layout = QHBoxLayout()
        self.greater_equal_radio = RadioButton("大于等于", condition_card)
        self.less_radio = RadioButton("小于", condition_card)

        self.greater_equal_radio.setChecked(True)

        self.condition_group = QButtonGroup(self)
        self.condition_group.addButton(self.greater_equal_radio, 0)
        self.condition_group.addButton(self.less_radio, 1)

        condition_type_layout.addWidget(self.greater_equal_radio)
        condition_type_layout.addWidget(self.less_radio)
        condition_type_layout.addStretch()
        condition_layout.addLayout(condition_type_layout)

        # 阈值设置
        threshold_layout = QHBoxLayout()
        threshold_label = BodyLabel("阈值:", condition_card)
        self.threshold_slider = Slider(Qt.Horizontal, condition_card)
        self.threshold_value_label = BodyLabel("25", condition_card)
        self.threshold_value_label.setMinimumWidth(40)

        # 根据当前选择的传感器类型更新滑动条范围
        self.temperature_radio.clicked.connect(lambda: self.update_slider_range('temperature'))
        self.humidity_radio.clicked.connect(lambda: self.update_slider_range('humidity'))
        self.pm25_radio.clicked.connect(lambda: self.update_slider_range('pm25'))
        self.noise_radio.clicked.connect(lambda: self.update_slider_range('noise'))

        # 初始设置温度滑动条
        self.update_slider_range('temperature')

        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value_label)
        condition_layout.addLayout(threshold_layout)

        condition_card.viewLayout.addLayout(condition_layout)
        layout.addWidget(condition_card)

        # 通知方式卡片
        notification_card = HeaderCardWidget(self)
        notification_card.setTitle("通知方式")
        notification_card.setBorderRadius(8)
        notification_layout = QVBoxLayout()

        self.message_checkbox = CheckBox("消息提醒", notification_card)
        self.sound_checkbox = CheckBox("音频提醒", notification_card)

        self.message_checkbox.setChecked(True)

        notification_layout.addWidget(self.message_checkbox)
        notification_layout.addWidget(self.sound_checkbox)

        notification_card.viewLayout.addLayout(notification_layout)
        layout.addWidget(notification_card)

        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = PushButton("取消", self)
        self.add_button = PrimaryPushButton("添加", self)

        self.cancel_button.clicked.connect(self.close)
        self.add_button.clicked.connect(self.add_rule)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.add_button)
        layout.addLayout(button_layout)

    def update_slider_range(self, sensor_type):
        """根据传感器类型更新滑动条范围"""
        if sensor_type == 'temperature':
            self.threshold_slider.setRange(0, 40)
            self.threshold_slider.setValue(25)
        elif sensor_type == 'humidity':
            self.threshold_slider.setRange(0, 100)
            self.threshold_slider.setValue(60)
        elif sensor_type == 'pm25':
            self.threshold_slider.setRange(0, 300)
            self.threshold_slider.setValue(75)
        elif sensor_type == 'noise':
            self.threshold_slider.setRange(0, 120)
            self.threshold_slider.setValue(60)

        self.threshold_value_label.setText(str(self.threshold_slider.value()))
        self.threshold_slider.valueChanged.connect(
            lambda value: self.threshold_value_label.setText(str(value))
        )

    def add_rule(self):
        """创建并保存警报规则"""
        # 获取传感器类型
        sensor_types = ['temperature', 'humidity', 'pm25', 'noise']
        sensor_type = sensor_types[self.sensor_group.checkedId()]

        # 获取条件类型
        condition_type = ">=" if self.greater_equal_radio.isChecked() else "<"

        # 获取阈值
        threshold = self.threshold_slider.value()

        # 获取通知方式
        notification_types = []
        if self.message_checkbox.isChecked():
            notification_types.append("message")
        if self.sound_checkbox.isChecked():
            notification_types.append("sound")

        notification_type = ",".join(notification_types)

        if not notification_type:
            InfoBar.warning(
                title='错误',
                content='请至少选择一种通知方式',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return False  # 返回False表示未创建规则

        # 创建规则并保存在dialog对象中
        self.rule = AlarmRule(sensor_type, condition_type, threshold, notification_type)
        self.accept()  # 接受对话框
        return True

    def accept(self):
        self.done(1)

    def reject(self):
        self.done(0)

    def done(self, r):
        self.setParent(None)
        self.deleteLater()


class AlarmRuleItem(CardWidget):
    """警报规则列表项"""
    deleteClicked = pyqtSignal(int)

    def __init__(self, rule, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 规则描述
        self.description_label = BodyLabel(self.rule.get_description(), self)
        layout.addWidget(self.description_label, 1)

        # 删除按钮
        self.delete_button = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_button.setFixedSize(32, 32)
        self.delete_button.setIconSize(QSize(16, 16))
        self.delete_button.clicked.connect(lambda: self.deleteClicked.emit(self.rule.id))
        layout.addWidget(self.delete_button)


class AlarmWidget(QWidget):
    """警报规则管理界面"""
    alarm_rules_changed = pyqtSignal(list)  # 当规则列表变更时发出信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alarmWidget")
        self.alarm_rules = []  # 存储所有警报规则
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 创建标题
        self.title_label = BodyLabel("警报规则", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        # 警报规则列表卡片
        self.rules_card = HeaderCardWidget(self)
        self.rules_card.setTitle("当前警报规则")
        self.rules_card.setBorderRadius(8)

        # 提示信息（当没有规则时显示）
        self.empty_hint = BodyLabel("暂无警报规则，点击下方按钮添加", self.rules_card)
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color: var(--text-color-secondary); padding: 20px;")
        self.rules_card.viewLayout.addWidget(self.empty_hint)

        # 规则列表容器
        self.rules_container = QWidget(self.rules_card)
        self.rules_layout = QVBoxLayout(self.rules_container)
        self.rules_layout.setContentsMargins(0, 0, 0, 0)
        self.rules_layout.setSpacing(8)

        # 设置规则列表滚动区域
        self.scroll_area = SingleDirectionScrollArea(self.rules_card)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.rules_container)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollArea > QWidget {
                background: transparent;
            }
        """)

        self.rules_card.viewLayout.addWidget(self.scroll_area)

        # 初始隐藏规则容器
        self.rules_container.hide()

        layout.addWidget(self.rules_card)

        # 添加规则按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.add_rule_button = PrimaryPushButton("添加规则", self)
        self.add_rule_button.setIcon(FluentIcon.ADD)
        self.add_rule_button.clicked.connect(self.show_add_rule_dialog)
        button_layout.addWidget(self.add_rule_button)
        layout.addLayout(button_layout)

        # 填充空白
        layout.addStretch()

    def show_add_rule_dialog(self):
        """显示添加规则对话框"""
        dialog = AlarmRuleDialog(self.window())
        if dialog.exec_():  # 现在这个方法是可用的
            if dialog.rule:  # 检查是否成功创建了规则
                self.add_rule(dialog.rule)

    def add_rule(self, rule):
        """添加规则到列表"""
        self.alarm_rules.append(rule)

        # 创建规则项
        rule_item = AlarmRuleItem(rule)
        rule_item.deleteClicked.connect(self.remove_rule)

        # 添加到布局
        self.rules_layout.addWidget(rule_item)

        # 如果是第一条规则，显示规则容器并隐藏提示
        if len(self.alarm_rules) == 1:
            self.empty_hint.hide()
            self.rules_container.show()

        # 发出规则变更信号
        self.alarm_rules_changed.emit(self.alarm_rules)

        # 显示成功提示
        InfoBar.success(
            title='添加成功',
            content='警报规则已成功添加',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def remove_rule(self, rule_id):
        """根据ID移除规则"""
        # 找到要删除的规则
        for i, rule in enumerate(self.alarm_rules):
            if rule.id == rule_id:
                # 从列表中移除规则
                self.alarm_rules.pop(i)

                # 从布局中移除对应的小部件
                item = self.rules_layout.itemAt(i)
                widget = item.widget()
                self.rules_layout.removeItem(item)
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

                # 如果没有规则了，显示提示并隐藏规则容器
                if not self.alarm_rules:
                    self.empty_hint.show()
                    self.rules_container.hide()

                # 发出规则变更信号
                self.alarm_rules_changed.emit(self.alarm_rules)

                # 显示删除成功提示
                InfoBar.success(
                    title='删除成功',
                    content='警报规则已成功删除',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self.window()
                )

                break


class AlarmNotificationCard(HeaderCardWidget):
    """警报通知卡片，显示在主页上"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("警报通知")
        self.setBorderRadius(8)
        self.setMaximumHeight(250)

        # 创建内容布局
        self.alarm_layout = QVBoxLayout()
        self.viewLayout.addLayout(self.alarm_layout)

        # 初始提示信息
        self.no_alarm_label = BodyLabel("无警报", self)
        self.no_alarm_label.setAlignment(Qt.AlignCenter)
        self.alarm_layout.addWidget(self.no_alarm_label)

        # 警报滚动区域
        self.scroll_area = SingleDirectionScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollArea > QWidget {
                background: transparent;
            }
        """)

        # 警报容器
        self.alarm_container = QWidget()
        self.alarm_container_layout = QVBoxLayout(self.alarm_container)
        self.alarm_container_layout.setContentsMargins(0, 0, 0, 0)
        self.alarm_container_layout.setSpacing(8)

        self.scroll_area.setWidget(self.alarm_container)
        self.alarm_layout.addWidget(self.scroll_area)

        # 初始隐藏滚动区域
        self.scroll_area.hide()

    def show_alarm(self, rule, value):
        """显示警报"""
        # 隐藏无警报提示
        self.no_alarm_label.hide()

        # 显示滚动区域
        self.scroll_area.show()

        # 创建警报项
        alarm_item = ElevatedCardWidget()
        alarm_item.setBorderRadius(6)

        # 获取警报颜色
        alarm_color = "#e11d48"  # 红色警报

        # 设置警报样式
        alarm_item.setStyleSheet(f"""
            ElevatedCardWidget {{
                border-left: 4px solid {alarm_color};
            }}
        """)

        # 警报内容布局
        alarm_layout = QVBoxLayout(alarm_item)
        alarm_layout.setContentsMargins(12, 10, 12, 10)
        alarm_layout.setSpacing(4)

        # 警报标题
        sensor_names = {
            'temperature': '温度警报',
            'humidity': '湿度警报',
            'pm25': 'PM2.5警报',
            'noise': '噪声警报'
        }

        alarm_title = StrongBodyLabel(sensor_names[rule.sensor_type], alarm_item)
        alarm_title.setStyleSheet("font-weight: bold; color: var(--text-color);")
        alarm_layout.addWidget(alarm_title)

        # 警报详情
        units = {
            'temperature': '°C',
            'humidity': '%',
            'pm25': 'μg/m³',
            'noise': 'dB'
        }

        condition_symbols = {
            '>=': '≥',
            '<': '<'
        }

        alarm_detail = BodyLabel(
            f"当前值: {value}{units[rule.sensor_type]} {condition_symbols[rule.condition_type]} {rule.threshold}{units[rule.sensor_type]}",
            alarm_item
        )
        alarm_detail.setStyleSheet("color: var(--text-color-secondary);")
        alarm_layout.addWidget(alarm_detail)

        # 时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = CaptionLabel(f"触发时间: {timestamp}", alarm_item)
        time_label.setStyleSheet("color: var(--text-color-tertiary); font-size: 11px;")
        alarm_layout.addWidget(time_label)

        # 添加警报项到容器
        self.alarm_container_layout.addWidget(alarm_item)

    def clear_alarms(self):
        """清除所有警报"""
        # 移除所有警报项
        while self.alarm_container_layout.count():
            item = self.alarm_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # 显示无警报提示
        self.no_alarm_label.show()

        # 隐藏滚动区域
        self.scroll_area.hide()


class HomeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeWidget")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 删除标题文本，直接显示实时数据卡片
        self.data_card = RealtimeDataCard(self)
        layout.addWidget(self.data_card)

        # 删除系统说明卡片，只保留数据卡片
        layout.addStretch()

    def update_data(self, temperature=None, humidity=None, pm25=None, noise=None, timestamp=None):
        """更新显示的数据"""
        # 更新实时数据卡片
        self.data_card.update_data(temperature, humidity, pm25, noise, timestamp)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # 应用样式表
        StyleSheet.MAIN_WINDOW.apply(self)

        # 窗口设置 - 允许调整大小
        self.setWindowTitle("环境监测系统")
        self.resize(960, 600)
        self.move(100, 100)
        self.setMinimumSize(800, 500)

        # 初始化变量
        self.time_range_minutes = 5
        self.dark_mode = isDarkTheme()
        self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}
        self.last_known_data = None

        # 创建界面 - 设置objectName
        self.homeWidget = HomeWidget(self)
        self.plotsWidget = PlotsWidget(self)
        self.historyWidget = HistoryWidget(self)
        self.alarmWidget = AlarmWidget(self)
        self.settingsWidget = TimeRangeSettings(self)

        # 初始化导航
        self.init_navigation()

        # 连接信号
        self.settingsWidget.timeRangeChanged.connect(self.on_time_range_changed)
        self.settingsWidget.refreshRateChanged.connect(self.set_refresh_rate)
        self.settingsWidget.themeChanged.connect(self.on_theme_changed)

        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_all_data)
        self.set_refresh_rate(2)  # 默认2秒更新一次

        # 第一次更新数据
        QTimer.singleShot(100, self.update_all_data)

    def cleanup(self):
        """程序关闭前的清理工作"""
        self.timer.stop()

    def create_qss_folders(self):
        """创建样式表文件夹结构"""
        import os

        # 创建目录结构
        dirs = [
            'qss',
            'qss/light',
            'qss/dark'
        ]

        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def init_navigation(self):
        # 添加导航项 - 使用修改后的图标
        self.addSubInterface(self.homeWidget, FluentIcon.HOME, "主页")
        self.addSubInterface(self.plotsWidget, FluentIcon.IOT, "数据图表")  # 修改为IOT图标
        self.addSubInterface(self.historyWidget, FluentIcon.HISTORY, "历史记录")
        self.addSubInterface(self.alarmWidget, FluentIcon.RINGER, "警报规则")  # 修改为RINGER图标

        # 添加设置到底部
        self.addSubInterface(self.settingsWidget, FluentIcon.SETTING, "设置", NavigationItemPosition.BOTTOM)

    def on_time_range_changed(self, minutes):
        self.time_range_minutes = minutes
        self.update_all_data()

    def set_refresh_rate(self, seconds):
        # 确保至少1秒更新一次
        seconds = max(1, seconds)
        self.timer.start(seconds * 1000)

    def on_theme_changed(self, dark_mode):
        # 更新主题
        self.dark_mode = dark_mode
        setTheme(Theme.DARK if dark_mode else Theme.LIGHT)

        # 更新各个组件的主题
        self.plotsWidget.update_theme(dark_mode)
        self.historyWidget.update_theme(dark_mode)

        # 应用样式表
        StyleSheet.MAIN_WINDOW.apply(self)

    def get_last_record_from_db(self):
        """从数据库获取最后一条记录"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            cursor = conn.cursor()

            # 查询最后一条记录
            cursor.execute("""
                SELECT timestamp, temperature, humidity, pm25, noise
                FROM sensor_data
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'timestamp': result[0],
                    'temperature': result[1],
                    'humidity': result[2],
                    'pm25': result[3],
                    'noise': result[4]
                }
            return None

        except Exception as e:
            print(f"Error fetching last record: {e}")
            return None

    def fetch_recent_data(self, minutes=5):
        """获取最近X分钟的数据"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            cursor = conn.cursor()

            # 计算起始时间
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes)

            # 格式化时间字符串
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

            # 执行查询
            cursor.execute("""
                SELECT timestamp, temperature, humidity, pm25, noise
                FROM sensor_data
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (start_time_str, end_time_str))

            # 清空缓存
            self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}

            # 处理结果
            results = cursor.fetchall()
            conn.close()

            if not results:
                # 如果没有数据，返回None
                return None

            for row in results:
                timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp()
                self.data_cache['times'].append(timestamp)
                self.data_cache['temp'].append(row[1])
                self.data_cache['humidity'].append(row[2])
                self.data_cache['pm25'].append(row[3])
                self.data_cache['noise'].append(row[4])

            # 保存最后一条数据
            last_record = results[-1]
            self.last_known_data = {
                'timestamp': last_record[0],
                'temperature': last_record[1],
                'humidity': last_record[2],
                'pm25': last_record[3],
                'noise': last_record[4]
            }

            return self.last_known_data

        except Exception as e:
            print(f"Error fetching db: {e}")
            return None

    def update_all_data(self):
        """更新所有数据显示"""
        # 获取数据
        latest = self.fetch_recent_data(self.time_range_minutes)

        # 如果没有获取到最近时间范围内的数据，使用最后一条已知数据
        if not latest:
            if not self.last_known_data:
                # 尝试从数据库获取最后一条记录
                self.last_known_data = self.get_last_record_from_db()

            latest = self.last_known_data

        if latest:
            # 更新主页数据
            self.homeWidget.update_data(
                temperature=latest['temperature'],
                humidity=latest['humidity'],
                pm25=latest['pm25'],
                noise=latest['noise'],
                timestamp=latest['timestamp']  # 传递时间戳
            )

            # 如果有数据缓存，则更新图表数据
            if self.data_cache['times']:
                self.plotsWidget.update_data(
                    times=self.data_cache['times'],
                    temp_history=self.data_cache['temp'],
                    humidity_history=self.data_cache['humidity'],
                    pm25_history=self.data_cache['pm25'],
                    noise_history=self.data_cache['noise']
                )

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        self.cleanup()
        super().closeEvent(event)


if __name__ == '__main__':
    # 捕获Ctrl+C信号
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 启用高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 设置全局字体
    font = app.font()
    font.setFamily("Microsoft YaHei UI")
    font.setPointSize(10)
    app.setFont(font)

    setTheme(Theme.LIGHT)
    window = MainWindow()
    window.show()

    # 确保窗口在合适的位置显示
    desktop = app.desktop().availableGeometry()
    windowRect = window.frameGeometry()
    windowRect.moveCenter(desktop.center())
    windowRect.moveTop(max(windowRect.top() - 30, 50))
    windowRect.moveLeft(max(windowRect.left(), 50))
    window.move(windowRect.topLeft())

    sys.exit(app.exec_())