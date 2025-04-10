import sys
import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from PyQt5.QtGui import QPainter, QColor, QPen

from qfluentwidgets import (FluentWindow, ScrollArea, TitleLabel, BodyLabel,
                            CardWidget, ComboBox, PrimaryPushButton, SwitchButton,
                            FluentIcon as FIF, InfoBar)


class ChartWidget(QChartView):
    """自定义图表组件"""

    def __init__(self, title, color="#1890FF", parent=None):
        super().__init__(parent)
        self.title = title
        self.line_color = color

        # 创建图表
        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.setTheme(QChart.ChartThemeLight)
        self.chart.setBackgroundVisible(False)
        self.chart.legend().hide()

        # 创建折线系列
        self.series = QLineSeries()
        pen = QPen(QColor(self.line_color))
        pen.setWidth(2)
        self.series.setPen(pen)
        self.chart.addSeries(self.series)

        # 创建坐标轴
        self.init_axes()

        # 设置图表视图属性
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)

    def init_axes(self):
        """初始化坐标轴"""
        self.time_axis = QDateTimeAxis()
        self.time_axis.setFormat("HH:mm:ss")
        self.time_axis.setTitleText("时间")

        self.value_axis = QValueAxis()
        self.value_axis.setTitleText(self.title)

        self.chart.addAxis(self.time_axis, Qt.AlignBottom)
        self.chart.addAxis(self.value_axis, Qt.AlignLeft)

        self.series.attachAxis(self.time_axis)
        self.series.attachAxis(self.value_axis)

    def update_data(self, timestamps, values):
        """更新图表数据"""
        if not timestamps or not values:
            return

        self.series.clear()

        for ts, val in zip(timestamps, values):
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                ms = int(dt.timestamp() * 1000)
                self.series.append(ms, float(val))
            except (ValueError, TypeError) as e:
                print(f"数据转换错误: {e}")
                continue

        if self.series.count() > 0:
            min_x = self.series.at(0).x()
            max_x = self.series.at(self.series.count() - 1).x()
            self.time_axis.setRange(
                QDateTime.fromMSecsSinceEpoch(int(min_x)),
                QDateTime.fromMSecsSinceEpoch(int(max_x))
            )

            values = [p.y() for p in (self.series.pointsVector())]
            if values:
                min_y = min(values)
                max_y = max(values)
                range_padding = (max_y - min_y) * 0.1
                self.value_axis.setRange(
                    max(0, min_y - range_padding),
                    max_y + range_padding
                )


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartEnviroSense - 传感器数据监控")
        self.resize(1200, 800)

        self.db_path = "sensor_data.db"
        self.time_ranges = {
            "最近30分钟": timedelta(minutes=30),
            "最近1小时": timedelta(hours=1),
            "最近2小时": timedelta(hours=2),
            "最近6小时": timedelta(hours=6),
            "最近12小时": timedelta(hours=12),
            "最近24小时": timedelta(hours=24),
        }
        self.current_range = "最近1小时"

        self.setup_ui()
        self.setup_charts()
        self.setup_timer()

    def setup_ui(self):
        """设置UI界面"""
        self.content_widget = ScrollArea(self)
        self.content_widget.setWidget(QWidget())
        self.content_widget.setWidgetResizable(True)
        # self.setCentralWidget(self.content_widget)

        self.main_layout = QVBoxLayout(self.content_widget.widget())
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题区域
        title_card = CardWidget(self)
        title_layout = QHBoxLayout(title_card)

        title = TitleLabel("实时环境数据监控", self)
        title_layout.addWidget(title)

        # 控制区域
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        range_label = BodyLabel("时间范围:", self)
        control_layout.addWidget(range_label)

        self.range_combo = ComboBox(self)
        self.range_combo.addItems(self.time_ranges.keys())
        self.range_combo.setCurrentText(self.current_range)
        self.range_combo.currentTextChanged.connect(self.on_range_changed)
        control_layout.addWidget(self.range_combo)

        self.refresh_btn = PrimaryPushButton("刷新", self, FIF.SYNC)
        self.refresh_btn.clicked.connect(self.refresh_charts)
        control_layout.addWidget(self.refresh_btn)

        self.auto_refresh = SwitchButton("自动刷新", self)
        self.auto_refresh.setChecked(True)
        self.auto_refresh.checkedChanged.connect(self.on_auto_refresh_changed)
        control_layout.addWidget(self.auto_refresh)

        control_layout.addStretch()
        title_layout.addLayout(control_layout)

        self.main_layout.addWidget(title_card)

    def setup_charts(self):
        """设置图表"""
        # 上方两个图表
        top_layout = QHBoxLayout()

        self.temp_card = self.create_chart_card("温度", "实时环境温度监测",
                                                "温度 (°C)", "#FF7043")
        top_layout.addWidget(self.temp_card)

        self.humidity_card = self.create_chart_card("湿度", "实时环境湿度监测",
                                                    "湿度 (%)", "#42A5F5")
        top_layout.addWidget(self.humidity_card)

        self.main_layout.addLayout(top_layout)

        # 下方两个图表
        bottom_layout = QHBoxLayout()

        self.pm25_card = self.create_chart_card("PM2.5", "实时PM2.5浓度监测",
                                                "PM2.5 (μg/m³)", "#66BB6A")
        bottom_layout.addWidget(self.pm25_card)

        self.noise_card = self.create_chart_card("噪声", "实时环境噪声监测",
                                                 "噪声 (dB)", "#FFA726")
        bottom_layout.addWidget(self.noise_card)

        self.main_layout.addLayout(bottom_layout)

    def create_chart_card(self, title, subtitle, chart_title, color):
        """创建图表卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)

        title_label = BodyLabel(title, self)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        subtitle_label = BodyLabel(subtitle, self)
        subtitle_label.setStyleSheet("color: gray;")
        layout.addWidget(subtitle_label)

        chart = ChartWidget(chart_title, color, self)
        chart.setMinimumHeight(250)
        layout.addWidget(chart)

        return card

    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_charts)
        self.timer.start(5000)  # 5秒刷新一次

    def on_range_changed(self, text):
        """时间范围变化响应"""
        self.current_range = text
        self.refresh_charts()

    def on_auto_refresh_changed(self, checked):
        """自动刷新开关响应"""
        if checked:
            self.timer.start()
        else:
            self.timer.stop()

    def refresh_charts(self):
        """刷新所有图表"""
        try:
            time_delta = self.time_ranges[self.current_range]
            data = self.fetch_data(time_delta)

            if not data:
                InfoBar.info(
                    title="提示",
                    content="所选时间范围内没有数据",
                    parent=self
                )
                return

            timestamps = [record[1] for record in data]
            temps = [record[2] for record in data]
            humidity = [record[3] for record in data]
            pm25 = [record[4] for record in data]
            noise = [record[5] for record in data]

            self.update_chart(self.temp_card, timestamps, temps)
            self.update_chart(self.humidity_card, timestamps, humidity)
            self.update_chart(self.pm25_card, timestamps, pm25)
            self.update_chart(self.noise_card, timestamps, noise)

        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"刷新数据失败: {str(e)}",
                parent=self
            )

    def update_chart(self, chart_card, timestamps, values):
        """更新图表数据"""
        chart = None
        for child in chart_card.findChildren(ChartWidget):
            chart = child
            break

        if chart:
            chart.update_data(timestamps, values)

    def fetch_data(self, time_delta):
        """从数据库获取数据"""
        try:
            start_time = (datetime.now() - time_delta).strftime("%Y-%m-%d %H:%M:%S")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, temperature, humidity, pm25, noise
                    FROM sensor_data
                    WHERE timestamp >= ?
                    ORDER BY timestamp
                """, (start_time,))

                return cursor.fetchall()

        except sqlite3.Error as e:
            InfoBar.error(
                title="数据库错误",
                content=f"无法获取数据: {str(e)}",
                parent=self
            )
            return []

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())