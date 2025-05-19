import multiprocessing
import sqlite3
import sys
import time
from datetime import datetime, timedelta

from PyQt5.QtCore import QTimer, Qt, QCoreApplication
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, Theme, setTheme, isDarkTheme, FluentIcon, NavigationItemPosition

import router as router_module
from dialog import AlarmWidget
from history import HistoryWidget
from home import HomeWidget
from plot import PlotsWidget
from setting import TimeRangeSettings, StyleSheet

DB_PATH = "db/sqlite.db"


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        StyleSheet.MAIN_WINDOW.apply(self)
        self.setWindowTitle("Fluent Sensor")
        self.resize(960, 600)
        self.setMinimumSize(800, 500)

        # 初始化成员变量
        self.time_range_minutes = 5
        self.dark_mode = isDarkTheme()
        self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}
        self.last_known_data = None

        # 初始化各个子界面
        self.homeWidget = HomeWidget(self)
        self.plotsWidget = PlotsWidget(self)
        self.historyWidget = HistoryWidget(self)
        self.alarmWidget = AlarmWidget(self)
        self.settingsWidget = TimeRangeSettings(self)

        # 初始化导航栏
        self.init_navigation()

        # 连接信号与槽
        self.settingsWidget.timeRangeChanged.connect(self.on_time_range_changed)
        self.settingsWidget.refreshRateChanged.connect(self.set_refresh_rate)
        self.settingsWidget.themeChanged.connect(self.on_theme_changed)

        # 初始化定时器用于数据刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_all_data)
        self.set_refresh_rate(2)

        # --- 启动 ROUTER 进程 ---
        self.router_process = None
        self.start_router_service()
        # --- 结束 ROUTER 进程 ---

        # 延迟100ms后首次更新数据，确保UI加载完成
        QTimer.singleShot(100, self.update_all_data)

    def start_router_service(self):
        """在单独的进程中启动 router.py 脚本。"""
        print("INFO: Fluent - 尝试启动数据服务...")
        try:
            self.router_process = multiprocessing.Process(
                target=router_module.run_tcp_client,  # 直接调用 router 模块的函数
                args=(router_module.ESP_TARGET_IP, router_module.ESP_TARGET_PORT),
                daemon=True  # 设置为守护进程，如果 fluent.py 崩溃，它可能会退出
            )
            self.router_process.start()
            time.sleep(0.2)  # 给它一点时间初始化或失败
            if self.router_process.is_alive():
                print(f"INFO: Fluent - 数据服务已成功启动 (PID: {self.router_process.pid}).")
            else:
                print("ERROR: Fluent - 数据服务启动失败或过早退出。", file=sys.stderr)
                self.router_process = None  # 如果失败，确保它是 None
        except Exception as e:
            print(f"ERROR: Fluent - 启动数据服务时发生异常: {e}", file=sys.stderr)
            self.router_process = None

    def init_navigation(self):
        """
        初始化导航栏，添加各个子界面到导航菜单。
        """
        self.addSubInterface(self.homeWidget, FluentIcon.HOME, "主页")
        self.addSubInterface(self.plotsWidget, FluentIcon.IOT, "数据图表")
        self.addSubInterface(self.historyWidget, FluentIcon.HISTORY, "历史记录")
        self.addSubInterface(self.alarmWidget, FluentIcon.RINGER, "警报规则")
        self.addSubInterface(self.settingsWidget, FluentIcon.SETTING, "设置", NavigationItemPosition.BOTTOM)

    def on_time_range_changed(self, minutes: int):
        """
        响应时间范围设置变化的槽函数。
        """
        self.time_range_minutes = minutes
        self.update_all_data()

    def set_refresh_rate(self, seconds: int):
        """
        设置数据刷新频率。
        """
        seconds = max(1, seconds)
        self.timer.start(seconds * 1000)

    def on_theme_changed(self, dark_mode: bool):
        """
        响应主题变化的槽函数。
        """
        self.dark_mode = dark_mode
        setTheme(Theme.DARK if dark_mode else Theme.LIGHT)
        self.plotsWidget.update_theme(dark_mode)
        self.historyWidget.update_theme(dark_mode)
        StyleSheet.MAIN_WINDOW.apply(self)

    def get_last_record_from_db(self) -> dict | None:
        """
        从数据库获取最新的单条传感器数据记录。
        """
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, temperature, humidity, pm25, noise FROM sensor_data ORDER BY timestamp DESC LIMIT 1"
            )
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
            print(f"从数据库获取最后记录时出错: {e}", file=sys.stderr)
            return None

    def fetch_recent_data(self, minutes: int = 5) -> dict | None:
        """
        从数据库获取指定时间范围内的传感器数据。
        """
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()

            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes)
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "SELECT timestamp, temperature, humidity, pm25, noise FROM sensor_data "
                "WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
                (start_time_str, end_time_str)
            )
            results = cursor.fetchall()
            conn.close()

            self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}

            if not results:
                return None

            for row in results:
                try:
                    timestamp_dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    self.data_cache['times'].append(timestamp_dt.timestamp())
                    self.data_cache['temp'].append(row[1])
                    self.data_cache['humidity'].append(row[2])
                    self.data_cache['pm25'].append(row[3])
                    self.data_cache['noise'].append(row[4])
                except ValueError:
                    print(f"跳过时间戳格式无效的行: {row[0]}", file=sys.stderr)
                    continue

            if not self.data_cache['times']:
                return None

            original_last_record = results[-1]
            self.last_known_data = {
                'timestamp': original_last_record[0],
                'temperature': original_last_record[1],
                'humidity': original_last_record[2],
                'pm25': original_last_record[3],
                'noise': original_last_record[4]
            }
            return self.last_known_data

        except Exception as e:
            print(f"从数据库获取近期数据时出错: {e}", file=sys.stderr)
            return None

    def update_all_data(self):
        """
        核心数据更新函数，由定时器周期性调用。
        """
        latest_data_in_range = self.fetch_recent_data(self.time_range_minutes)

        if not latest_data_in_range and self.last_known_data:
            current_data_to_display = self.last_known_data
        elif latest_data_in_range:
            current_data_to_display = latest_data_in_range
        else:
            current_data_to_display = self.get_last_record_from_db()

        if current_data_to_display:
            self.homeWidget.update_data(
                temperature=current_data_to_display['temperature'],
                humidity=current_data_to_display['humidity'],
                pm25=current_data_to_display['pm25'],
                noise=current_data_to_display['noise'],
                timestamp=current_data_to_display['timestamp']
            )

            if self.data_cache['times']:
                self.plotsWidget.update_data(
                    times=self.data_cache['times'],
                    temp_history=self.data_cache['temp'],
                    humidity_history=self.data_cache['humidity'],
                    pm25_history=self.data_cache['pm25'],
                    noise_history=self.data_cache['noise']
                )

            try:
                current_time = datetime.now()
                data_time = datetime.strptime(current_data_to_display['timestamp'], "%Y-%m-%d %H:%M:%S")
                time_diff_seconds = (current_time - data_time).total_seconds()

                if time_diff_seconds <= 3:
                    self.alarmWidget.check_all_rules({
                        'temperature': current_data_to_display['temperature'],
                        'humidity': current_data_to_display['humidity'],
                        'pm25': current_data_to_display['pm25'],
                        'noise': current_data_to_display['noise'],
                        'timestamp': current_data_to_display['timestamp']
                    })
                else:
                    self.alarmWidget.stop_all_alarms()
            except ValueError:
                print(f"警报检查时时间戳格式错误: {current_data_to_display['timestamp']}", file=sys.stderr)
                self.alarmWidget.stop_all_alarms()
            except Exception as e:
                print(f"检查警报规则时发生错误: {e}", file=sys.stderr)
                self.alarmWidget.stop_all_alarms()
        else:
            self.alarmWidget.stop_all_alarms()
            print("未能获取到任何数据进行更新。", file=sys.stderr)

    def closeEvent(self, event):
        """
        处理窗口关闭事件。
        """
        print("主窗口关闭事件触发。")
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        if hasattr(self, 'alarmWidget') and self.alarmWidget:
            self.alarmWidget.stop_all_alarms()

        # --- 终止 ROUTER 进程 ---
        if self.router_process and self.router_process.is_alive():
            print("INFO: Fluent - 正在终止数据服务进程...")
            try:
                self.router_process.terminate()  # 发送 SIGTERM
                self.router_process.join(timeout=3)  # 等待最多3秒
                if self.router_process.is_alive():
                    print("WARN: Fluent - 数据服务进程未能优雅终止，将强制结束...")
                    self.router_process.kill()  # 如果仍然存活，发送 SIGKILL
                    self.router_process.join(timeout=1)  # 等待强制结束

                if not self.router_process.is_alive():
                    print("INFO: Fluent - 数据服务进程已终止。")
                else:
                    print("ERROR: Fluent - 数据服务进程未能终止。", file=sys.stderr)

            except Exception as e:
                print(f"ERROR: Fluent - 终止数据服务进程时发生异常: {e}", file=sys.stderr)
        # --- 结束终止 ROUTER 进程 ---

        super().closeEvent(event)
        app_instance = QCoreApplication.instance()
        if app_instance:
            app_instance.quit()
        print("应用程序已请求退出。")


def start_fluent_application():
    """
    启动 Fluent UI 应用程序的入口函数。
    """
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    font = app.font()
    font.setFamily("Microsoft YaHei UI, Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    setTheme(Theme.LIGHT)

    window = MainWindow()
    window.show()

    try:
        desktop = QApplication.desktop().availableGeometry()
        window_rect = window.frameGeometry()
        window_rect.moveCenter(desktop.center())
        target_top = max(window_rect.top() - 30, desktop.top())
        target_left = max(window_rect.left(), desktop.left())
        if target_left + window_rect.width() > desktop.right():
            target_left = desktop.right() - window_rect.width()
        if target_top + window_rect.height() > desktop.bottom():
            target_top = desktop.bottom() - window_rect.height()
        target_left = max(0, target_left)
        target_top = max(0, target_top)
        window.move(target_left, target_top)
    except Exception as e:
        print(f"无法将窗口居中: {e}", file=sys.stderr)
        window.move(100, 100)

    sys.exit(app.exec_())


if __name__ == '__main__':
    multiprocessing.freeze_support()
    start_fluent_application()