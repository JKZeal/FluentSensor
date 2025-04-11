import sys
import sqlite3
import numpy as np
from enum import Enum
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDate, QEvent
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget, QHBoxLayout, QLabel,
                             QGroupBox, QFrame, QButtonGroup, QRadioButton, QTableWidgetItem,
                             QSizePolicy, QFileDialog, QGridLayout)
from qfluentwidgets import (NavigationInterface, NavigationItemPosition, FluentWindow,
                            ComboBox, Slider, PrimaryPushButton, StyleSheetBase,
                            MessageBox, InfoBar, InfoBarPosition, PushButton,
                            RoundMenu, Action, FluentIcon, setTheme, Theme, isDarkTheme, qconfig,
                            ZhDatePicker, TableWidget, SmoothMode, SingleDirectionScrollArea,
                            CardWidget, ElevatedCardWidget, HeaderCardWidget, BodyLabel,
                            CaptionLabel, IconWidget, TransparentToolButton, InfoBarIcon)
from qfluentwidgets.components.widgets.acrylic_label import AcrylicBrush
import pyqtgraph as pg

DB_PATH = "sensor_data.db"


class StyleSheet(StyleSheetBase, Enum):
    """样式表"""
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 初始化数据
        self.data = {'time': [], 'value': []}

        # 保留鼠标滚轮缩放功能
        self.plotItem.setMouseEnabled(x=True, y=True)

        # 初始化曲线
        self.curve = self.plot(pen=pg.mkPen(color='white', width=2))

        # 设置底部轴为时间轴
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.plotItem.setAxisItems({'bottom': date_axis})

        # 根据主题设置外观
        self.update_theme(dark_mode)

    def update_theme(self, dark_mode):
        self.dark_mode = dark_mode

        # 设置颜色
        if dark_mode:
            bg_color = (30, 30, 30, 255)
            curve_color = '#4ec9b0'
            text_color = 'white'
            title_color = 'white'
            grid_alpha = 0.2
        else:
            bg_color = (245, 245, 245, 255)
            curve_color = '#007acc'
            text_color = '#303030'
            title_color = '#101010'
            grid_alpha = 0.15

        # 设置背景色和网格
        self.setBackground(bg_color)
        self.plotItem.showGrid(x=True, y=True, alpha=grid_alpha)

        # 设置标题
        self.plotItem.setTitle(self.plot_title, color=title_color, size="14pt", bold=True)

        # 设置坐标轴标签和样式
        self.plotItem.setLabel('left', self.y_axis_label, color=text_color)
        self.plotItem.setLabel('bottom', 'Time', color=text_color)
        self.getAxis('left').setPen(text_color)
        self.getAxis('bottom').setPen(text_color)
        self.getAxis('left').setTextPen(text_color)

        # 更新曲线颜色
        self.curve.setPen(pg.mkPen(color=curve_color, width=2))

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
            # Y轴自适应
            y_min, y_max = min(new_values), max(new_values)
            padding = max((y_max - y_min) * 0.1, 0.1) if y_max > y_min else 1.0
            self.plotItem.setYRange(y_min - padding, y_max + padding)

            # X轴自适应
            x_min, x_max = min(new_times), max(new_times)
            padding_x = (x_max - x_min) * 0.05 if x_max > x_min else 60
            self.plotItem.setXRange(x_min - padding_x, x_max + padding_x)


class PlotCard(HeaderCardWidget):
    def __init__(self, title, y_label, dark_mode=False, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setBorderRadius(10)

        # 创建图表
        self.plot_widget = PlotWidget(title, y_label, dark_mode)
        self.plot_widget.setMinimumHeight(300)

        # 添加到卡片主视图
        self.viewLayout.addWidget(self.plot_widget)

    def update_data(self, times, values):
        self.plot_widget.update_data(times, values)

    def update_theme(self, dark_mode):
        self.plot_widget.update_theme(dark_mode)


class RealtimeDataCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("实时环境数据")
        self.setBorderRadius(10)

        # # 右上角显示时间的标签
        # self.time_label = CaptionLabel(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self)
        # self.time_label.setStyleSheet("font-size: 14px;")
        #
        # # 在标题后添加时间标签
        # header_layout = QHBoxLayout()
        # header_layout.addWidget(CaptionLabel("最后更新时间:", self))
        # header_layout.addWidget(self.time_label)
        # header_layout.addStretch(1)
        #
        # self.viewLayout.addLayout(header_layout)
        #
        # # 调整间距
        # self.viewLayout.addSpacing(10)

        # 指标容器 - 使用网格布局代替水平布局，以便更好地分布四个指标
        indicator_layout = QGridLayout()
        indicator_layout.setHorizontalSpacing(20)
        indicator_layout.setVerticalSpacing(15)

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
        card = ElevatedCardWidget(self)
        card.setBorderRadius(8)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)  # 增加间距

        # 添加图标和名称到一行
        header_layout = QHBoxLayout()
        icon_widget = IconWidget(icon, card)
        name_label = CaptionLabel(name, card)
        name_label.setStyleSheet("font-size: 14px; color: #888;")  # 增大字体

        header_layout.addWidget(icon_widget)
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        # 添加值标签
        value_label = BodyLabel(value, card)
        value_label.setObjectName(f"{name.lower()}_value")

        # 为时间卡片设置不同的样式
        if time_card:
            value_label.setStyleSheet("font-size: 18px; font-weight: bold;")  # 时间卡片字体稍小
            card.setMinimumHeight(90)  # 时间卡片高度稍小
        else:
            value_label.setStyleSheet("font-size: 24px; font-weight: bold;")  # 其他指标保持大字体
            card.setMinimumHeight(120)  # 保持其他卡片高度

        value_label.setAlignment(Qt.AlignCenter)  # 居中对齐

        layout.addLayout(header_layout)
        layout.addWidget(value_label)

        # 设置卡片大小策略
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        return card

    def update_data(self, temperature=None, humidity=None, pm25=None, noise=None):
        """更新显示的数据"""
        # 更新时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_indicator.findChild(BodyLabel, "更新时间_value").setText(current_time)

        # 更新指标值
        if temperature is not None:
            self.temp_indicator.findChild(BodyLabel, "温度_value").setText(f"{temperature:.1f}°C")

        if humidity is not None:
            self.humidity_indicator.findChild(BodyLabel, "湿度_value").setText(f"{humidity:.1f}%")

        if pm25 is not None:
            self.pm25_indicator.findChild(BodyLabel, "pm2.5_value").setText(f"{pm25:.0f} μg/m³")

        if noise is not None:
            self.noise_indicator.findChild(BodyLabel, "噪声_value").setText(f"{noise:.0f} dB")

class TimeRangeSettings(QWidget):
    # 定义信号
    timeRangeChanged = pyqtSignal(int)
    refreshRateChanged = pyqtSignal(int)
    themeChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = isDarkTheme()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 创建标题
        self.title_label = BodyLabel("数据显示设置", self)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(self.title_label)

        # 时间范围设置区域
        self.time_card = HeaderCardWidget(self)
        self.time_card.setTitle("时间范围设置")
        self.time_card.setBorderRadius(10)

        # 添加说明
        time_label = CaptionLabel("选择要显示的历史数据时间范围", self.time_card)

        # 创建下拉框
        combo_layout = QHBoxLayout()
        combo_label = BodyLabel("时间范围:", self.time_card)
        self.timeComboBox = ComboBox(self.time_card)
        self.timeComboBox.addItems(["1 分钟", "5 分钟", "15 分钟", "30 分钟",
                                    "1 小时", "3 小时", "12 小时", "24 小时"])
        self.timeComboBox.setCurrentIndex(1)  # 默认选择5分钟
        combo_layout.addWidget(combo_label)
        combo_layout.addWidget(self.timeComboBox)
        combo_layout.addStretch()

        self.time_card.viewLayout.addWidget(time_label)
        self.time_card.viewLayout.addLayout(combo_layout)

        layout.addWidget(self.time_card)

        # 刷新频率设置区域
        self.refresh_card = HeaderCardWidget(self)
        self.refresh_card.setTitle("刷新频率设置")
        self.refresh_card.setBorderRadius(10)

        # 添加说明
        refresh_label = CaptionLabel("设置数据刷新频率", self.refresh_card)

        # 滑动条布局
        slider_layout = QVBoxLayout()
        self.refresh_value_label = BodyLabel("刷新频率: 2 秒", self.refresh_card)
        slider_layout.addWidget(self.refresh_value_label)

        self.refreshSlider = Slider(Qt.Horizontal, self.refresh_card)
        self.refreshSlider.setRange(1, 10)
        self.refreshSlider.setValue(2)
        self.refreshSlider.valueChanged.connect(self.on_refresh_slider_changed)
        slider_layout.addWidget(self.refreshSlider)

        self.refresh_card.viewLayout.addWidget(refresh_label)
        self.refresh_card.viewLayout.addLayout(slider_layout)

        layout.addWidget(self.refresh_card)

        # 主题设置区域
        self.theme_card = HeaderCardWidget(self)
        self.theme_card.setTitle("主题设置")
        self.theme_card.setBorderRadius(10)

        theme_desc = CaptionLabel("选择应用主题", self.theme_card)

        # 创建单选按钮
        radio_layout = QHBoxLayout()
        self.theme_button_group = QButtonGroup(self)

        self.light_radio = QRadioButton("浅色主题", self.theme_card)
        self.dark_radio = QRadioButton("深色主题", self.theme_card)

        self.light_radio.setChecked(not self.dark_mode)
        self.dark_radio.setChecked(self.dark_mode)

        self.theme_button_group.addButton(self.light_radio, 0)
        self.theme_button_group.addButton(self.dark_radio, 1)

        radio_layout.addWidget(self.light_radio)
        radio_layout.addWidget(self.dark_radio)
        radio_layout.addStretch()

        self.theme_card.viewLayout.addWidget(theme_desc)
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
            self.dark_mode = dark_mode

        # 显示提示
        InfoBar.success(
            title='设置已应用',
            content=f"已更新时间范围为 {self.timeComboBox.currentText()}，刷新频率为 {refresh_rate} 秒",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )


class HistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = isDarkTheme()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 创建标题
        self.title_label = BodyLabel("历史数据查询", self)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(self.title_label)

        # 日期选择区域使用 HeaderCardWidget
        self.date_card = HeaderCardWidget(self)
        self.date_card.setTitle("选择日期")
        self.date_card.setBorderRadius(10)

        date_desc = CaptionLabel("选择要查询的日期", self.date_card)

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

        # 添加导出按钮 - 移到查询按钮旁边
        self.export_button = PushButton("导出为CSV", self.date_card)
        self.export_button.clicked.connect(self.export_data)
        picker_layout.addWidget(self.export_button)

        picker_layout.addStretch()

        self.date_card.viewLayout.addWidget(date_desc)
        self.date_card.viewLayout.addLayout(picker_layout)

        layout.addWidget(self.date_card)

        # 数据展示区域
        self.results_card = HeaderCardWidget(self)
        self.results_card.setTitle("查询结果")
        self.results_card.setBorderRadius(10)

        # 添加表格
        self.table = TableWidget(self.results_card)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setColumnCount(6)

        # 设置表头
        self.table.setHorizontalHeaderLabels(['时间', '温度(°C)', '湿度(%)', 'PM2.5(μg/m³)', '噪声(dB)', '状态'])
        self.table.verticalHeader().hide()
        self.table.setSelectRightClickedRow(True)

        # 禁用平滑滚动以提高性能
        try:
            self.table.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)
        except:
            pass

        # 设置表格大小策略，使其能够填充可用空间
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 添加表格到结果卡片
        self.results_card.viewLayout.addWidget(self.table)

        # 将结果卡片添加到主布局，并设置它可以拉伸
        layout.addWidget(self.results_card, 1)  # 添加拉伸因子1，使其能够填充剩余空间

    def query_data(self):
        """根据选择的日期查询数据"""
        selected_date = self.date_picker.getDate()
        date_str = selected_date.toString("yyyy-MM-dd")

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT timestamp, temperature, humidity, pm25, noise "
                "FROM sensor_data "
                "WHERE timestamp LIKE ? "
                "ORDER BY timestamp",
                (f"{date_str}%",)  # 使用通配符匹配当天所有时间
            )

            data = cursor.fetchall()
            conn.close()

            # 更新表格
            self.update_table(data)

            # 显示查询结果消息
            if data:
                InfoBar.success(
                    title='查询成功',
                    content=f"找到 {len(data)} 条 {date_str} 的记录",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self.window()
                )
            else:
                InfoBar.warning(
                    title='无数据',
                    content=f"未找到 {date_str} 的记录",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self.window()
                )

        except Exception as e:
            InfoBar.error(
                title='查询失败',
                content=f"错误信息: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self.window()
            )

    def update_table(self, data):
        """更新表格数据"""
        self.table.setRowCount(0)

        if not data:
            return

        # 定义环境评估阈值
        thresholds = {
            'temp': {'良好': (18, 26), '注意': (10, 32), '警告': (0, 40)},
            'humidity': {'良好': (40, 60), '注意': (30, 70), '警告': (0, 100)},
            'pm25': {'良好': (0, 50), '注意': (50, 100), '警告': (100, 999)},
            'noise': {'良好': (0, 50), '注意': (50, 70), '警告': (70, 999)}
        }

        for row_idx, row_data in enumerate(data):
            self.table.insertRow(row_idx)

            # 解析时间仅显示时间部分
            timestamp = row_data[0]
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp

            temp = float(row_data[1])
            humidity = float(row_data[2])
            pm25 = float(row_data[3])
            noise = float(row_data[4])

            # 评估环境状态
            status = self._evaluate_status(temp, humidity, pm25, noise, thresholds)

            # 设置单元格内容
            self.table.setItem(row_idx, 0, QTableWidgetItem(time_str))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{temp:.1f}"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{humidity:.1f}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{pm25:.0f}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{noise:.0f}"))

            # 设置状态单元格
            status_item = QTableWidgetItem(status)
            status_colors = {'良好': QColor(0, 170, 0), '注意': QColor(255, 140, 0), '警告': QColor(255, 0, 0)}
            status_item.setForeground(QBrush(status_colors.get(status, QColor(0, 0, 0))))
            self.table.setItem(row_idx, 5, status_item)

        # 调整列宽
        self.table.resizeColumnsToContents()

    def _evaluate_status(self, temp, humidity, pm25, noise, thresholds):
        """评估环境状态"""
        status = "良好"

        # 温度检查
        if temp < thresholds['temp']['良好'][0] or temp > thresholds['temp']['良好'][1]:
            if temp < thresholds['temp']['注意'][0] or temp > thresholds['temp']['注意'][1]:
                return "警告"
            status = "注意"

        # 湿度检查
        if humidity < thresholds['humidity']['良好'][0] or humidity > thresholds['humidity']['良好'][1]:
            if humidity < thresholds['humidity']['注意'][0] or humidity > thresholds['humidity']['注意'][1]:
                return "警告"
            elif status == "良好":
                status = "注意"

        # PM2.5检查
        if pm25 > thresholds['pm25']['良好'][1]:
            if pm25 > thresholds['pm25']['注意'][1]:
                return "警告"
            elif status == "良好":
                status = "注意"

        # 噪声检查
        if noise > thresholds['noise']['良好'][1]:
            if noise > thresholds['noise']['注意'][1]:
                return "警告"
            elif status == "良好":
                status = "注意"

        return status

    def export_data(self):
        """导出表格数据为CSV文件"""
        if self.table.rowCount() == 0:
            InfoBar.warning(
                title='导出失败',
                content="没有数据可导出",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
            return

        # 获取选定的日期作为文件名
        selected_date = self.date_picker.getDate().toString("yyyy-MM-dd")
        default_name = f"环境数据_{selected_date}.csv"

        # 使用系统对话框获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为CSV",
            default_name,
            "CSV 文件 (*.csv)"
        )

        if not file_path:  # 用户取消了保存
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                import csv
                writer = csv.writer(f)

                # 写入表头
                headers = []
                for col in range(self.table.columnCount()):
                    headers.append(self.table.horizontalHeaderItem(col).text())
                writer.writerow(headers)

                # 写入数据
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            InfoBar.success(
                title='导出成功',
                content=f"数据已保存到: {file_path}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
        except Exception as e:
            InfoBar.error(
                title='导出失败',
                content=f"错误信息: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self.window()
            )

    def update_theme(self, dark_mode):
        """更新所有组件的主题"""
        self.dark_mode = dark_mode

        # 更新标题和标签颜色
        title_color = "white" if dark_mode else "#333333"
        self.title_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; margin-bottom: 15px; color: {title_color};")


class AboutWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 创建卡片
        about_card = HeaderCardWidget(self)
        about_card.setTitle("关于应用")
        about_card.setBorderRadius(10)

        # 添加图标
        icon_layout = QHBoxLayout()
        app_icon = IconWidget(FluentIcon.IOT, self)
        app_icon.setFixedSize(64, 64)
        icon_layout.addWidget(app_icon, 0, Qt.AlignCenter)

        # 添加应用名称
        app_name = BodyLabel("环境监测系统", self)
        app_name.setStyleSheet("font-size: 24px; font-weight: bold;")
        name_layout = QHBoxLayout()
        name_layout.addWidget(app_name, 0, Qt.AlignCenter)

        # 添加版本信息
        version_label = CaptionLabel("版本 1.0", self)
        version_layout = QHBoxLayout()
        version_layout.addWidget(version_label, 0, Qt.AlignCenter)

        # 添加说明文本
        desc_label = BodyLabel(
            "这是一个环境数据监测与可视化系统，用于实时采集和显示环境参数。\n\n"
            "支持以下功能：\n"
            "• 实时显示温度、湿度、PM2.5和噪声数据\n"
            "• 超出所设阈值报警\n"
            "• 历史数据查询与导出\n"
            "• 数据趋势图表分析\n"
            "• 自定义显示设置",
            self
        )
        desc_label.setWordWrap(True)

        # 添加著作权信息
        copyright_label = CaptionLabel("© 2025春 综合工程设计 第5组。", self)
        copyright_layout = QHBoxLayout()
        copyright_layout.addWidget(copyright_label, 0, Qt.AlignCenter)

        # 将所有内容添加到卡片
        about_card.viewLayout.addLayout(icon_layout)
        about_card.viewLayout.addLayout(name_layout)
        about_card.viewLayout.addLayout(version_layout)
        about_card.viewLayout.addSpacing(20)
        about_card.viewLayout.addWidget(desc_label)
        about_card.viewLayout.addSpacing(20)
        about_card.viewLayout.addLayout(copyright_layout)

        layout.addWidget(about_card)
        layout.addStretch()


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # 创建qss目录
        self.create_qss_folders()

        # 初始化界面
        self.setWindowTitle("环境监测系统")
        self.resize(1200, 800)

        # 创建亚克力效果
        self.acrylic = AcrylicBrush(self, 30)
        self.setStyleSheet("background: transparent")

        # 设置查询时间范围
        self.time_range_minutes = 5

        # 默认使用当前主题设置
        self.dark_mode = isDarkTheme()

        # 创建主界面容器
        self.main_widget = QWidget()
        self.main_widget.setObjectName("mainWidget")
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 创建图表
        self.init_plots()

        # 创建导航栏
        self.init_navigation()

        # 定时更新数据
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_all_plots)
        self.timer.start(2000)  # 每2秒更新一次

        # 应用主题样式表
        StyleSheet.MAIN_WINDOW.apply(self)

    def create_qss_folders(self):
        """创建样式表文件夹结构"""
        import os

        # 创建目录
        os.makedirs("qss/light", exist_ok=True)
        os.makedirs("qss/dark", exist_ok=True)

        # 创建样式文件
        light_style = """
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
        """

        dark_style = """
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
        """

        with open("qss/light/main_window.qss", "w") as f:
            f.write(light_style)

        with open("qss/dark/main_window.qss", "w") as f:
            f.write(dark_style)

    def init_navigation(self):
        # 添加导航项
        self.addSubInterface(self.main_widget, FluentIcon.IOT, "环境监测")

        # 创建报警规则界面
        self.analytics_widget = QWidget()
        self.analytics_widget.setObjectName("alarmWidget")
        self.addSubInterface(self.analytics_widget,
                             FluentIcon.RINGER,
                             "报警规则",
                             NavigationItemPosition.SCROLL)

        # 创建历史界面
        self.history_widget = HistoryWidget()
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

        # 创建关于界面
        self.about_widget = AboutWidget()
        self.about_widget.setObjectName("aboutWidget")
        self.addSubInterface(self.about_widget,
                             FluentIcon.INFO,
                             "关于",
                             NavigationItemPosition.BOTTOM)

    def init_plots(self):
        # 修改为垂直布局，使内容自适应填充整个宽度
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建容器小部件并使用垂直布局
        self.plots_container = QWidget()
        # 给 plots_container 添加右侧边距，确保卡片与滚动条之间有间距
        plots_layout = QVBoxLayout(self.plots_container)
        plots_layout.setContentsMargins(0, 0, 20, 0)  # 左、上、右、下 - 右侧添加20px边距
        plots_layout.setSpacing(20)

        # 添加实时数据卡片
        self.realtime_card = RealtimeDataCard(self.plots_container)
        plots_layout.addWidget(self.realtime_card)

        # 创建四个图表卡片
        self.temp_plot = PlotCard("温度", "°C", self.dark_mode)
        self.humidity_plot = PlotCard("湿度", "%", self.dark_mode)
        self.pm25_plot = PlotCard("PM2.5", "μg/m³", self.dark_mode)
        self.noise_plot = PlotCard("噪声", "dB", self.dark_mode)

        # 添加图表到布局
        plots_layout.addWidget(self.temp_plot)
        plots_layout.addWidget(self.humidity_plot)
        plots_layout.addWidget(self.pm25_plot)
        plots_layout.addWidget(self.noise_plot)

        # 设置容器的大小策略，使其能够填充可用空间
        self.plots_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 添加图表区域到主区域
        main_layout.addWidget(self.plots_container)

        # 底部可以添加一个空白区域用于滚动余量
        scroll_space = QWidget()
        scroll_space.setMinimumHeight(20)  # 底部留出一点空间
        scroll_space.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(scroll_space)

        # 创建自定义滚动区域
        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical)
        self.scroll_area.setWidget(main_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea{background: transparent; border: none}")
        self.plots_container.setStyleSheet("QWidget{background: transparent}")

        # 将滚动区域添加到主布局
        self.main_layout.addWidget(self.scroll_area)

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
        self.temp_plot.update_theme(dark_mode)
        self.humidity_plot.update_theme(dark_mode)
        self.pm25_plot.update_theme(dark_mode)
        self.noise_plot.update_theme(dark_mode)

        # 更新滚动区域样式
        self.plots_container.setStyleSheet("QWidget{background: transparent}")

        # 更新历史数据界面主题
        self.history_widget.update_theme(dark_mode)

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
        """更新所有图表"""
        data = self.fetch_recent_data(self.time_range_minutes)

        if not data:
            return

        # 处理数据
        times, temps, humids, pm25s, noises = [], [], [], [], []

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
        if times:
            self.temp_plot.update_data(times, temps)
            self.humidity_plot.update_data(times, humids)
            self.pm25_plot.update_data(times, pm25s)
            self.noise_plot.update_data(times, noises)

            # 更新实时数据卡片
            self.realtime_card.update_data(
                temperature=temps[-1] if temps else None,
                humidity=humids[-1] if humids else None,
                pm25=pm25s[-1] if pm25s else None,
                noise=noises[-1] if noises else None
            )

    def resizeEvent(self, event):
        """当窗口大小变化时调用"""
        super().resizeEvent(event)
        # 延迟更新布局以提高性能
        QTimer.singleShot(0, self.update_plot_layouts)

    def update_plot_layouts(self):
        """更新所有图表的布局"""
        for plot in [self.temp_plot, self.humidity_plot, self.pm25_plot, self.noise_plot]:
            plot.update()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())