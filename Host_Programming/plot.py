import numpy as np
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QFont, QColor, QLinearGradient, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import BodyLabel, SingleDirectionScrollArea, isDarkTheme, CardWidget, FluentStyleSheet
import pyqtgraph as pg
from datetime import datetime


class FluentAxisItem(pg.AxisItem):
    """Fluent Design风格的简化坐标轴"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyle(showValues=True)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """自定义刻度显示格式"""
        if self.orientation == 'bottom':
            # 时间轴，显示时分秒
            strings = []
            for v in values:
                try:
                    dt = datetime.fromtimestamp(v)
                    strings.append(dt.strftime("%H:%M:%S"))
                except (ValueError, OSError):
                    strings.append('')
            return strings
        else:
            # 普通轴，简化数字显示
            return [f"{int(v)}" if v == int(v) else f"{v:.1f}" for v in values]


class FluentChartPlot(pg.PlotWidget):
    """Fluent Design风格的图表组件"""

    # 预定义数据范围
    DATA_RANGES = {
        "温度": (-20, 60),
        "湿度": (0, 100),
        "PM2.5": (0, 1000),
        "噪声": (0, 120)
    }

    def __init__(self, title="", y_label="", dark_mode=False, color_theme="blue"):
        # 创建自定义轴
        axis_items = {
            'left': FluentAxisItem(orientation='left'),
            'bottom': FluentAxisItem(orientation='bottom')
        }

        super().__init__(axisItems=axis_items)

        # 基本属性设置
        self.plot_title = title
        self.y_axis_label = y_label
        self.dark_mode = dark_mode
        self.color_theme = color_theme
        self.data = {'time': [], 'value': []}
        self.current_point = None  # 当前选中的点

        # 禁用鼠标滚轮缩放
        self.plotItem.vb.setMouseEnabled(x=False, y=False)

        # 隐藏自动缩放按钮
        self.plotItem.hideButtons()

        # 设置字体
        self.font = QFont("Microsoft YaHei UI", 9)

        # 移除上和右边框
        self.showAxis('top', show=False)
        self.showAxis('right', show=False)

        # 创建主曲线
        self.curve = self.plot(pen=pg.mkPen(color='#0078d4', width=2, cosmetic=True))

        # 创建底部曲线（用于填充）
        self.bottom_curve = self.plot(pen=pg.mkPen(None))

        # 创建填充区域
        self.fill = pg.FillBetweenItem(curve1=self.curve, curve2=self.bottom_curve,
                                       brush=pg.mkBrush(color=(0, 120, 215, 50)))
        self.addItem(self.fill)

        # 数据点标记
        self.point_marker = pg.ScatterPlotItem()
        self.point_marker.setSize(8)
        self.point_marker.hide()
        self.addItem(self.point_marker)

        # 垂直线指示器
        self.vLine = pg.InfiniteLine(angle=90, movable=False,
                                     pen=pg.mkPen(color='#888888', width=1, style=Qt.DashLine))
        self.vLine.hide()
        self.addItem(self.vLine)

        # 连接鼠标事件
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.onMouseMoved)
        self.leaveProxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.checkMouseLeave)

        # 初始化主题
        self.update_theme(dark_mode, color_theme)

        # 设置固定Y轴范围
        self.setFixedYRange()

    def setFixedYRange(self):
        """设置固定的Y轴范围"""
        y_range = self.DATA_RANGES.get(self.y_axis_label, (0, 100))
        min_y, max_y = y_range

        # 调整Y轴范围，确保最大最小值可见，同时为标签留出空间
        self.setYRange(min_y - 0.05 * (max_y - min_y),
                       max_y + 0.05 * (max_y - min_y),
                       padding=0)

    def get_theme_colors(self, theme_name):
        """获取不同主题的颜色配置"""
        themes = {
            "orange": {  # 温度
                "light": {
                    "curve": "#FF8C00",
                    "gradient_start": "#FF8C00",
                    "gradient_end": "#FFAA33",
                    "hover_text": "#D66F00",  # 深色文本
                    "normal_text": "#FF9E33"  # 浅色文本
                },
                "dark": {
                    "curve": "#FFA500",
                    "gradient_start": "#FF8C00",
                    "gradient_end": "#FFAA33",
                    "hover_text": "#FFB84D",  # 深色文本
                    "normal_text": "#FFAA33"  # 浅色文本
                }
            },
            "blue": {  # 湿度
                "light": {
                    "curve": "#1E90FF",
                    "gradient_start": "#1E90FF",
                    "gradient_end": "#87CEFA",
                    "hover_text": "#0066CC",  # 深色文本
                    "normal_text": "#5CACEE"  # 浅色文本
                },
                "dark": {
                    "curve": "#00BFFF",
                    "gradient_start": "#1E90FF",
                    "gradient_end": "#87CEFA",
                    "hover_text": "#29B9FF",  # 深色文本
                    "normal_text": "#87CEFA"  # 浅色文本
                }
            },
            "green": {  # PM2.5
                "light": {
                    "curve": "#32CD32",
                    "gradient_start": "#32CD32",
                    "gradient_end": "#90EE90",
                    "hover_text": "#228B22",  # 深色文本
                    "normal_text": "#66CD00"  # 浅色文本
                },
                "dark": {
                    "curve": "#3CB371",
                    "gradient_start": "#32CD32",
                    "gradient_end": "#90EE90",
                    "hover_text": "#4EEE94",  # 深色文本
                    "normal_text": "#90EE90"  # 浅色文本
                }
            },
            "purple": {  # 噪声
                "light": {
                    "curve": "#9370DB",
                    "gradient_start": "#9370DB",
                    "gradient_end": "#B19CD9",
                    "hover_text": "#7D26CD",  # 深色文本
                    "normal_text": "#A385FF"  # 浅色文本
                },
                "dark": {
                    "curve": "#9370DB",
                    "gradient_start": "#9370DB",
                    "gradient_end": "#B19CD9",
                    "hover_text": "#AB82FF",  # 深色文本
                    "normal_text": "#B19CD9"  # 浅色文本
                }
            }
        }

        mode = "dark" if self.dark_mode else "light"
        return themes.get(theme_name, themes["blue"])[mode]

    def update_theme(self, dark_mode, color_theme=None):
        """更新图表主题"""
        self.dark_mode = dark_mode
        if color_theme:
            self.color_theme = color_theme

        # 获取主题颜色
        theme_colors = self.get_theme_colors(self.color_theme)

        # 设置背景和文字颜色
        if dark_mode:
            # 深色主题
            bg_color = QColor(30, 30, 30)  # 实心背景
            text_color = '#ffffff'
            axis_color = '#888888'
            grid_color = '#333333'
            grid_alpha = 0.4
            border_color = '#555555'
        else:
            # 浅色主题
            bg_color = QColor(255, 255, 255)  # 纯白色背景
            text_color = '#505050'
            axis_color = '#aaaaaa'
            grid_color = '#e0e0e0'
            grid_alpha = 0.5
            border_color = '#cccccc'

        # 应用背景色
        self.setBackground(bg_color)

        # 配置网格
        self.showGrid(x=True, y=True, alpha=grid_alpha)

        # 移除轴标签文本
        self.getAxis('left').setLabel('')
        self.getAxis('bottom').setLabel('')

        # 更新轴样式 - 保留边框线，使其可见
        axis_pen = pg.mkPen(color=border_color, width=1)
        self.getAxis('left').setPen(axis_pen)
        self.getAxis('bottom').setPen(axis_pen)
        self.getAxis('left').setTextPen(text_color)
        self.getAxis('bottom').setTextPen(text_color)

        # 创建明显的外框
        self.getPlotItem().getViewBox().setBorder(pg.mkPen(color=border_color, width=1))

        # 更新曲线样式
        curve_color = theme_colors["curve"]
        self.curve.setPen(pg.mkPen(color=curve_color, width=2, cosmetic=True))
        self.vLine.setPen(pg.mkPen(color='#888888', width=1, style=Qt.DashLine))

        # 创建填充区域的渐变色
        start_color = QColor(theme_colors["gradient_start"])
        end_color = QColor(theme_colors["gradient_end"])
        start_color.setAlpha(100)  # 更明显的填充
        end_color.setAlpha(30)  # 逐渐淡化

        # 创建渐变
        gradient = QLinearGradient(0, 0, 0, 1)
        gradient.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
        gradient.setColorAt(0, start_color)
        gradient.setColorAt(1, end_color)

        # 应用渐变到填充区域
        self.fill.setBrush(QBrush(gradient))

        # 更新点标记颜色
        self.point_marker.setPen(pg.mkPen(color=curve_color, width=2))
        self.point_marker.setBrush(pg.mkBrush(color=QColor(curve_color).lighter(120)))

    def update_data(self, new_times, new_values):
        """更新图表数据"""
        if not new_times or not new_values or len(new_times) == 0 or len(new_values) == 0:
            return

        if not isinstance(new_times, list):
            new_times = [new_times]
        if not isinstance(new_values, list):
            new_values = [new_values]

        # 更新数据存储
        self.data['time'] = new_times
        self.data['value'] = new_values

        # 转换为numpy数组
        x_data = np.array(new_times, dtype=np.float64)
        y_data = np.array(new_values, dtype=np.float64)

        # 获取Y轴范围
        y_range = self.DATA_RANGES.get(self.y_axis_label, (0, 100))

        # 使用Y轴实际可视范围的底部值作为填充基线，而不是数据范围的最小值
        view_range = self.getViewBox().viewRange()
        base_level = view_range[1][0]  # 使用当前Y轴视图的底部值

        # 绘制主曲线 - 不使用平滑曲线，直接显示数据点
        self.curve.setData(x_data, y_data)

        # 更新底部曲线（用于填充区域）
        self.bottom_curve.setData(x_data, np.full_like(x_data, base_level))

        # 设置X轴范围
        if len(new_times) > 1:
            x_min, x_max = min(x_data), max(x_data)
            self.setXRange(x_min, x_max, padding=0)  # 无内边距

        # 清除当前选中点
        self.current_point = None
        self.hideHoverItems()

    def onMouseMoved(self, event):
        """处理鼠标移动事件，显示悬停信息"""
        # 获取场景位置
        pos = event[0]

        # 防止越界
        if not self.plotItem.sceneBoundingRect().contains(pos):
            self.hideHoverItems()
            return

        # 获取鼠标的数据坐标
        mouse_point = self.plotItem.vb.mapSceneToView(pos)
        x = mouse_point.x()

        # 检查数据是否存在
        if not self.data['time'] or len(self.data['time']) == 0:
            return

        # 找到最近的数据点
        times = np.array(self.data['time'])
        values = np.array(self.data['value'])

        # 计算距离并找到最近点
        idx = np.abs(times - x).argmin()
        nearest_time = times[idx]
        nearest_value = values[idx]

        # 只在鼠标足够接近时显示
        if abs(nearest_time - x) > (times.max() - times.min()) / 30:
            self.hideHoverItems()
            return

        # 更新垂直线位置
        self.vLine.setPos(nearest_time)
        self.vLine.show()

        # 更新点标记位置
        self.point_marker.setData([nearest_time], [nearest_value])
        self.point_marker.show()

        # 保存当前选中点
        self.current_point = (nearest_time, nearest_value)

    def checkMouseLeave(self, event):
        """检查鼠标是否离开图表区域"""
        pos = event[0]
        if not self.plotItem.sceneBoundingRect().contains(pos):
            self.hideHoverItems()

    def hideHoverItems(self):
        """隐藏悬停相关的组件"""
        self.vLine.hide()
        self.point_marker.hide()
        self.current_point = None


class FluentChartCard(CardWidget):
    """Fluent Design风格的图表卡片"""

    def __init__(self, title="", y_label="", unit="", color_theme="blue", dark_mode=False, parent=None):
        super().__init__(parent)
        self.title = title
        self.y_label = y_label
        self.unit = unit
        self.color_theme = color_theme
        self.dark_mode = dark_mode

        # 设置卡片样式
        self.setBorderRadius(8)
        FluentStyleSheet.CARD_WIDGET.apply(self)

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(12, 12, 12, 12)  # 减小边距
        self.vBoxLayout.setSpacing(6)  # 减小间距

        # 添加标题 - 使用更符合Fluent Design的字体样式
        self.title_label = QLabel(title, self)
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Normal))
        self.title_label.setStyleSheet("font-weight: 500; margin-bottom: 4px;")
        self.vBoxLayout.addWidget(self.title_label)

        # 创建图表
        self.plot_widget = FluentChartPlot("", y_label, dark_mode, color_theme)
        self.plot_widget.setMinimumHeight(220)
        self.vBoxLayout.addWidget(self.plot_widget)

        # 创建数据点信息显示区域 - 居中显示
        self.info_container = QWidget(self)
        self.info_layout = QHBoxLayout(self.info_container)
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_layout.setSpacing(8)
        self.info_layout.setAlignment(Qt.AlignCenter)  # 使文本居中

        # 时间标签
        self.time_info = QLabel("", self.info_container)
        self.time_info.setFont(QFont("Segoe UI", 9))
        self.info_layout.addWidget(self.time_info)

        # 值标签
        self.value_info = QLabel("", self.info_container)
        self.value_info.setFont(QFont("Segoe UI", 9))
        self.info_layout.addWidget(self.value_info)

        # 添加信息区域到主布局
        self.vBoxLayout.addWidget(self.info_container)

        # 更新主题
        self.update_theme(dark_mode)

        # 定时检查悬停点并更新信息
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_point_info)
        self.timer.start(100)  # 每100ms更新一次

        # 初始显示最新数据信息
        self.show_latest_info()

    def update_data(self, times, values):
        """更新图表数据"""
        if times and values and len(times) > 0 and len(values) > 0:
            self.plot_widget.update_data(times, values)
            # 显示最新的数值
            self.show_latest_info()

    def update_theme(self, dark_mode):
        """更新主题"""
        self.dark_mode = dark_mode

        # 获取对应主题的颜色
        theme_colors = self.plot_widget.get_theme_colors(self.color_theme)

        # 更新图表主题
        self.plot_widget.update_theme(dark_mode, self.color_theme)

        # 更新标题样式
        if dark_mode:
            self.title_label.setStyleSheet("color: #ffffff; font-weight: 500;")
        else:
            self.title_label.setStyleSheet("color: #202020; font-weight: 500;")

        # 更新默认信息文本颜色（使用浅色文本）
        normal_text_color = theme_colors["normal_text"]
        self.time_info.setStyleSheet(f"color: {normal_text_color};")
        self.value_info.setStyleSheet(f"color: {normal_text_color};")

    def update_point_info(self):
        """更新数据点信息显示 - 鼠标悬停时"""
        point = self.plot_widget.current_point
        if point:
            # 获取主题对应的深色文本颜色
            hover_text_color = self.plot_widget.get_theme_colors(self.color_theme)["hover_text"]

            time_stamp, value = point

            # 格式化时间和值
            time_str = datetime.fromtimestamp(time_stamp).strftime("%H:%M:%S")

            # 更新文本和样式
            self.time_info.setText(f"数据点: 选中")
            self.time_info.setStyleSheet(f"color: {hover_text_color}; font-weight: 500;")

            self.value_info.setText(f"时间: {time_str} 数值: {value:.1f} {self.unit}")
            self.value_info.setStyleSheet(f"color: {hover_text_color}; font-weight: 500;")
        else:
            # 当鼠标不在图表上时，显示最新数据点
            self.show_latest_info()

    def show_latest_info(self):
        """显示最新数据点的信息"""
        # 获取主题对应的浅色文本颜色
        normal_text_color = self.plot_widget.get_theme_colors(self.color_theme)["normal_text"]

        # 检查是否有数据
        if self.plot_widget.data['time'] and len(self.plot_widget.data['time']) > 0:
            # 获取最新数据点
            latest_time = self.plot_widget.data['time'][-1]
            latest_value = self.plot_widget.data['value'][-1]

            # 格式化时间
            time_str = datetime.fromtimestamp(latest_time).strftime("%H:%M:%S")

            # 更新显示
            self.time_info.setText(f"数据点: 最新")
            self.time_info.setStyleSheet(f"color: {normal_text_color};")

            self.value_info.setText(f"时间: {time_str} 数值: {latest_value:.1f} {self.unit}")
            self.value_info.setStyleSheet(f"color: {normal_text_color};")
        else:
            # 无数据时显示占位符
            self.time_info.setText("数据点: --")
            self.time_info.setStyleSheet(f"color: {normal_text_color};")

            self.value_info.setText(f"时间: -- 数值: -- {self.unit}")
            self.value_info.setStyleSheet(f"color: {normal_text_color};")


class PlotsWidget(QWidget):
    """图表页面主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("plotsWidget")
        self.setup_ui()

    def setup_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 页面标题 - 使用Fluent风格
        self.title_label = QLabel("数据图表", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 500; margin-bottom: 10px; color: black;")
        self.title_label.setFont(QFont("Segoe UI", 22))
        layout.addWidget(self.title_label)

        # 滚动区域
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
        self.plots_container.setStyleSheet("#plotsContainerWidget {background: transparent; border: none;}")
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.setSpacing(16)

        # 获取当前主题
        dark_mode = isDarkTheme()

        # 创建图表卡片
        self.temp_plot = FluentChartCard("温度趋势", "温度", "°C", "orange", dark_mode)
        self.humidity_plot = FluentChartCard("湿度趋势", "湿度", "%", "blue", dark_mode)
        self.pm25_plot = FluentChartCard("PM2.5趋势", "PM2.5", "μg/m³", "green", dark_mode)
        self.noise_plot = FluentChartCard("噪声趋势", "噪声", "dB", "purple", dark_mode)

        # 添加图表到布局
        self.plots_layout.addWidget(self.temp_plot)
        self.plots_layout.addWidget(self.humidity_plot)
        self.plots_layout.addWidget(self.pm25_plot)
        self.plots_layout.addWidget(self.noise_plot)

        # 设置滚动区域的部件
        self.scroll_area.setWidget(self.plots_container)
        layout.addWidget(self.scroll_area, 1)

    def update_data(self, times=None, temp_history=None, humidity_history=None, pm25_history=None, noise_history=None):
        """更新所有图表数据"""
        if times is not None:
            if temp_history is not None and len(temp_history) > 0:
                self.temp_plot.update_data(times, temp_history)
            if humidity_history is not None and len(humidity_history) > 0:
                self.humidity_plot.update_data(times, humidity_history)
            if pm25_history is not None and len(pm25_history) > 0:
                self.pm25_plot.update_data(times, pm25_history)
            if noise_history is not None and len(noise_history) > 0:
                self.noise_plot.update_data(times, noise_history)

    def update_theme(self, dark_mode):
        """更新所有图表主题"""
        # 更新页面标题颜色
        if dark_mode:
            self.title_label.setStyleSheet("font-size: 22px; font-weight: 500; margin-bottom: 10px; color: #60cdff;")
        else:
            self.title_label.setStyleSheet("font-size: 22px; font-weight: 500; margin-bottom: 10px; color: #0078d4;")

        # 更新各图表主题
        self.temp_plot.update_theme(dark_mode)
        self.humidity_plot.update_theme(dark_mode)
        self.pm25_plot.update_theme(dark_mode)
        self.noise_plot.update_theme(dark_mode)