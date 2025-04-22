import sqlite3
import sys
from datetime import datetime, timedelta

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, Theme, setTheme, isDarkTheme

from dialog import AlarmWidget
from history import HistoryWidget
from home import HomeWidget
from plot import PlotsWidget
from setting import TimeRangeSettings, StyleSheet

DB_PATH = "db/sqlite.db"

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        # 应用样式表
        StyleSheet.MAIN_WINDOW.apply(self)

        # 窗口设置
        self.setWindowTitle("环境监测系统")
        self.resize(960, 600)
        self.move(100, 100)
        self.setMinimumSize(800, 500)

        # 初始化变量
        self.time_range_minutes = 5
        self.dark_mode = isDarkTheme()
        self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}
        self.last_known_data = None

        # 创建界面
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
        self.set_refresh_rate(2)

        # 第一次更新数据
        QTimer.singleShot(100, self.update_all_data)

    def init_navigation(self):
        from qfluentwidgets import FluentIcon, NavigationItemPosition
        self.addSubInterface(self.homeWidget, FluentIcon.HOME, "主页")
        self.addSubInterface(self.plotsWidget, FluentIcon.IOT, "数据图表")
        self.addSubInterface(self.historyWidget, FluentIcon.HISTORY, "历史记录")
        self.addSubInterface(self.alarmWidget, FluentIcon.RINGER, "警报规则")
        self.addSubInterface(self.settingsWidget, FluentIcon.SETTING, "设置", NavigationItemPosition.BOTTOM)

    def on_time_range_changed(self, minutes):
        self.time_range_minutes = minutes
        self.update_all_data()

    def set_refresh_rate(self, seconds):
        seconds = max(1, seconds)
        self.timer.start(seconds * 1000)

    def on_theme_changed(self, dark_mode):
        self.dark_mode = dark_mode
        setTheme(Theme.DARK if dark_mode else Theme.LIGHT)
        self.plotsWidget.update_theme(dark_mode)
        self.historyWidget.update_theme(dark_mode)
        StyleSheet.MAIN_WINDOW.apply(self)

    def get_last_record_from_db(self):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            # 设置WAL模式
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, temperature, humidity, pm25, noise FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            if result:
                return {'timestamp': result[0], 'temperature': result[1], 'humidity': result[2], 'pm25': result[3],
                        'noise': result[4]}
            return None
        except Exception as e:
            print(f"Error fetching last record: {e}")
            return None

    def fetch_recent_data(self, minutes=5):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes)
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT timestamp, temperature, humidity, pm25, noise FROM sensor_data WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC", (start_time_str, end_time_str))
            self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}
            results = cursor.fetchall()
            conn.close()
            if not results:
                return None
            for row in results:
                timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp()
                self.data_cache['times'].append(timestamp)
                self.data_cache['temp'].append(row[1])
                self.data_cache['humidity'].append(row[2])
                self.data_cache['pm25'].append(row[3])
                self.data_cache['noise'].append(row[4])
            last_record = results[-1]
            self.last_known_data = {'timestamp': last_record[0], 'temperature': last_record[1], 'humidity': last_record[2], 'pm25': last_record[3], 'noise': last_record[4]}
            return self.last_known_data
        except Exception as e:
            print(f"Error fetching db: {e}")
            return None

    def update_all_data(self):
        latest = self.fetch_recent_data(self.time_range_minutes)
        if not latest and self.last_known_data:
            latest = self.last_known_data
        if not latest:
            latest = self.get_last_record_from_db()
        if latest:
            self.homeWidget.update_data(temperature=latest['temperature'], humidity=latest['humidity'],
                                        pm25=latest['pm25'], noise=latest['noise'], timestamp=latest['timestamp'])
            if self.data_cache['times']:
                self.plotsWidget.update_data(times=self.data_cache['times'], temp_history=self.data_cache['temp'],
                                             humidity_history=self.data_cache['humidity'],
                                             pm25_history=self.data_cache['pm25'],
                                             noise_history=self.data_cache['noise'])

            # 检查数据时间戳
            current_time = datetime.now()
            data_time = datetime.strptime(latest['timestamp'], "%Y-%m-%d %H:%M:%S")
            time_diff = (current_time - data_time).total_seconds()

            if time_diff <= 3:  # 只有当数据是最近3秒内的才检查警报规则
                self.alarmWidget.check_all_rules({
                    'temperature': latest['temperature'],
                    'humidity': latest['humidity'],
                    'pm25': latest['pm25'],
                    'noise': latest['noise'],
                    'timestamp': latest['timestamp']
                })
            else:
                # 数据过期,停止所有警报
                self.alarmWidget.stop_all_alarms()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("Microsoft YaHei UI")
    font.setPointSize(10)
    app.setFont(font)
    setTheme(Theme.LIGHT)
    window = MainWindow()
    window.show()
    desktop = app.desktop().availableGeometry()
    windowRect = window.frameGeometry()
    windowRect.moveCenter(desktop.center())
    windowRect.moveTop(max(windowRect.top() - 30, 50))
    windowRect.moveLeft(max(windowRect.left(), 50))
    window.move(windowRect.topLeft())
    sys.exit(app.exec_())