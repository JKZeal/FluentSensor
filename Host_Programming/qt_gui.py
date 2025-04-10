import sys
import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from qfluentwidgets import (NavigationInterface, NavigationItemPosition, FluentWindow,
                            MessageBox, InfoBar, InfoBarPosition, PushButton,
                            RoundMenu, Action, FluentIcon, setTheme, Theme)
from qfluentwidgets.components.widgets.acrylic_label import AcrylicBrush
import pyqtgraph as pg

DB_PATH = "sensor_data.db"


class PlotWidget(pg.PlotWidget):
    def __init__(self, title="", y_label=""):
        super().__init__()
        self.setBackground((0, 0, 0, 0))  # 透明背景
        self.plotItem.showGrid(x=True, y=True, alpha=0.3)
        self.plotItem.setTitle(title, color='white', size="12pt")
        self.plotItem.setLabel('left', y_label, color='white')
        self.plotItem.setLabel('bottom', 'Time', color='white')
        self.setMinimumHeight(250)

        # 设置坐标轴颜色
        self.getAxis('left').setPen('white')
        self.getAxis('bottom').setPen('white')

        self.curve = self.plot(pen=pg.mkPen(color='#4ec9b0', width=2))
        self.data = {'time': [], 'value': []}

    def update_data(self, new_time, new_value):
        self.data['time'].append(new_time)
        self.data['value'].append(new_value)

        # 只保留最近60分钟的数据
        if len(self.data['time']) > 60:
            self.data['time'] = self.data['time'][-60:]
            self.data['value'] = self.data['value'][-60:]

        self.curve.setData(self.data['time'], self.data['value'])


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # 初始化界面
        self.setWindowTitle("Sensor Data Monitor")
        self.resize(1200, 800)

        # 创建亚克力效果
        self.acrylic = AcrylicBrush(self, 30)
        self.setStyleSheet("background: transparent")

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

    # 在 init_navigation 方法中做以下调整
    def init_navigation(self):
        # 添加导航项 - 改用正确的 fluent icon 常量
        self.addSubInterface(self.main_widget, FluentIcon.HOME, "Dashboard")

        # 创建分析界面（改用 CHART）
        self.analytics_widget = QWidget()
        self.analytics_widget.setObjectName("analyticsWidget")
        self.addSubInterface(self.analytics_widget,
                             FluentIcon.IOT,
                             "Analytics",
                             NavigationItemPosition.SCROLL)

        # 创建历史界面（改用 HISTORY）
        self.history_widget = QWidget()
        self.history_widget.setObjectName("historyWidget")
        self.addSubInterface(self.history_widget,
                             FluentIcon.HISTORY,
                             "History",
                             NavigationItemPosition.SCROLL)

        # 添加底部导航项
        self.navigationInterface.addSeparator()
        self.settings_widget = QWidget()
        self.settings_widget.setObjectName("settingsWidget")
        self.addSubInterface(self.settings_widget,
                             FluentIcon.SETTING,
                             "Settings",
                             NavigationItemPosition.BOTTOM)

        self.about_widget = QWidget()
        self.about_widget.setObjectName("aboutWidget")
        self.addSubInterface(self.about_widget,
                             FluentIcon.INFO,
                             "About",
                             NavigationItemPosition.BOTTOM)

    def init_plots(self):
        # 温度图表
        self.temp_plot = PlotWidget("Temperature", "°C")
        self.main_layout.addWidget(self.temp_plot)

        # 湿度图表
        self.humidity_plot = PlotWidget("Humidity", "%")
        self.main_layout.addWidget(self.humidity_plot)

        # PM2.5图表
        self.pm25_plot = PlotWidget("PM2.5", "μg/m³")
        self.main_layout.addWidget(self.pm25_plot)

        # 噪声图表
        self.noise_plot = PlotWidget("Noise Level", "dB")
        self.main_layout.addWidget(self.noise_plot)

        # 设置图表样式
        for plot in [self.temp_plot, self.humidity_plot, self.pm25_plot, self.noise_plot]:
            plot.setFixedHeight(200)

    def fetch_recent_data(self, minutes=60):
        """获取最近X分钟的数据"""
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

    def update_all_plots(self):
        data = self.fetch_recent_data(60)  # 获取最近60分钟数据

        if not data:
            return

        times = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in data]
        timestamps = [t.timestamp() for t in times]

        # 更新温度图表
        temps = [row[1] for row in data]
        self.temp_plot.update_data(timestamps, temps)

        # 更新湿度图表
        humids = [row[2] for row in data]
        self.humidity_plot.update_data(timestamps, humids)

        # 更新PM2.5图表
        pm25s = [row[3] for row in data]
        self.pm25_plot.update_data(timestamps, pm25s)

        # 更新噪声图表
        noises = [row[4] for row in data]
        self.noise_plot.update_data(timestamps, noises)

    def show_settings_menu(self):
        menu = RoundMenu(parent=self)

        menu.addAction(Action(FluentIcon.CHAT, 'Notification Settings'))
        menu.addAction(Action(FluentIcon.TIME_MANAGEMENT, 'Time Range'))
        menu.addAction(Action(FluentIcon.PALETTE, 'Theme Settings'))
        menu.addSeparator()
        menu.addAction(Action(FluentIcon.HELP, 'About'))

        # 显示菜单在按钮下方
        menu.exec_(self.setting_button.mapToGlobal(
            self.setting_button.rect().bottomLeft()
        ))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 设置Fluent风格
    setTheme(Theme.LIGHT)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
