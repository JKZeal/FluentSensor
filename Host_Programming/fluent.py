import sqlite3
import sys
from datetime import datetime, timedelta

from PyQt5.QtCore import QTimer, Qt, QCoreApplication
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, Theme, setTheme, isDarkTheme, FluentIcon, NavigationItemPosition

# 导入自定义模块
from dialog import AlarmWidget
from history import HistoryWidget
from home import HomeWidget
from plot import PlotsWidget
from setting import TimeRangeSettings, StyleSheet

# 数据库文件路径
DB_PATH = "db/sqlite.db"


class MainWindow(FluentWindow):
    """
    主窗口类，继承自 FluentWindow，构建应用的主要界面和逻辑。
    """

    def __init__(self):
        super().__init__()
        StyleSheet.MAIN_WINDOW.apply(self)  # 应用主窗口样式
        self.setWindowTitle("Fluent Sensor")  # <--- 更改窗口标题
        self.resize(960, 600)
        self.setMinimumSize(800, 500)

        # 初始化成员变量
        self.time_range_minutes = 5  # 默认图表显示时间范围（分钟）
        self.dark_mode = isDarkTheme()  # 当前是否为深色模式
        self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}  # 数据缓存
        self.last_known_data = None  # 上一次成功获取的数据，用于无新数据时回填

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
        self.set_refresh_rate(2)  # 默认刷新频率2秒

        # 延迟100ms后首次更新数据，确保UI加载完成
        QTimer.singleShot(100, self.update_all_data)

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
        参数:
            minutes (int): 新的时间范围（分钟）。
        """
        self.time_range_minutes = minutes
        self.update_all_data()  # 时间范围变化后立即更新数据

    def set_refresh_rate(self, seconds: int):
        """
        设置数据刷新频率。
        参数:
            seconds (int): 新的刷新频率（秒）。
        """
        seconds = max(1, seconds)  # 最小刷新间隔为1秒
        self.timer.start(seconds * 1000)

    def on_theme_changed(self, dark_mode: bool):
        """
        响应主题变化的槽函数。
        参数:
            dark_mode (bool): True表示深色模式，False表示浅色模式。
        """
        self.dark_mode = dark_mode
        setTheme(Theme.DARK if dark_mode else Theme.LIGHT)
        # 通知子组件主题已更改
        self.plotsWidget.update_theme(dark_mode)
        self.historyWidget.update_theme(dark_mode)
        StyleSheet.MAIN_WINDOW.apply(self)  # 重新应用主窗口样式以适配主题

    def get_last_record_from_db(self) -> dict | None:
        """
        从数据库获取最新的单条传感器数据记录。
        返回:
            dict | None: 包含最新数据的字典，或在失败时返回 None。
        """
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式提高并发性能
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
        参数:
            minutes (int): 要获取数据的时间范围（分钟）。
        返回:
            dict | None: 包含时间范围内最新一条数据的字典，或在无数据/失败时返回 None。
                         同时会更新 self.data_cache。
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

            # 重置数据缓存
            self.data_cache = {'times': [], 'temp': [], 'humidity': [], 'pm25': [], 'noise': []}

            if not results:
                return None  # 如果查询结果为空，直接返回

            for row in results:
                try:
                    # 将时间字符串转换为Unix时间戳 (float)
                    timestamp_dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    self.data_cache['times'].append(timestamp_dt.timestamp())
                    self.data_cache['temp'].append(row[1])
                    self.data_cache['humidity'].append(row[2])
                    self.data_cache['pm25'].append(row[3])
                    self.data_cache['noise'].append(row[4])
                except ValueError:
                    # 如果时间戳格式不正确，打印错误并跳过该行
                    print(f"跳过时间戳格式无效的行: {row[0]}", file=sys.stderr)
                    continue

            if not self.data_cache['times']:  # 如果有效数据为空 (例如所有时间戳都无效)
                return None

            # 使用原始的 results[-1] 来构建 last_known_data，以确保时间戳是原始字符串格式
            original_last_record = results[-1]
            self.last_known_data = {
                'timestamp': original_last_record[0],
                'temperature': original_last_record[1],
                'humidity': original_last_record[2],
                'pm25': original_last_record[3],
                'noise': original_last_record[4]
            }
            return self.last_known_data  # 返回最近一条数据（字典形式）

        except Exception as e:
            print(f"从数据库获取近期数据时出错: {e}", file=sys.stderr)
            return None

    def update_all_data(self):
        """
        核心数据更新函数，由定时器周期性调用。
        获取最新数据并更新各个子界面。
        """
        # 1. 尝试获取指定时间范围内的数据
        latest_data_in_range = self.fetch_recent_data(self.time_range_minutes)

        # 2. 如果范围内无数据，但之前有过数据，则使用上次的已知数据
        if not latest_data_in_range and self.last_known_data:
            current_data_to_display = self.last_known_data
        elif latest_data_in_range:
            current_data_to_display = latest_data_in_range
        else:
            # 3. 如果都没有，则尝试从数据库获取最后一条记录（不限时间范围）
            current_data_to_display = self.get_last_record_from_db()

        if current_data_to_display:
            # 更新主页数据
            self.homeWidget.update_data(
                temperature=current_data_to_display['temperature'],
                humidity=current_data_to_display['humidity'],
                pm25=current_data_to_display['pm25'],
                noise=current_data_to_display['noise'],
                timestamp=current_data_to_display['timestamp']
            )

            # 如果数据缓存中有数据（通常由 fetch_recent_data 填充），则更新图表
            if self.data_cache['times']:
                self.plotsWidget.update_data(
                    times=self.data_cache['times'],
                    temp_history=self.data_cache['temp'],
                    humidity_history=self.data_cache['humidity'],
                    pm25_history=self.data_cache['pm25'],
                    noise_history=self.data_cache['noise']
                )

            # 检查警报规则
            try:
                current_time = datetime.now()
                data_time = datetime.strptime(current_data_to_display['timestamp'], "%Y-%m-%d %H:%M:%S")
                time_diff_seconds = (current_time - data_time).total_seconds()

                # 仅当数据是最近3秒内的才检查警报规则
                if time_diff_seconds <= 3:
                    self.alarmWidget.check_all_rules({
                        'temperature': current_data_to_display['temperature'],
                        'humidity': current_data_to_display['humidity'],
                        'pm25': current_data_to_display['pm25'],
                        'noise': current_data_to_display['noise'],
                        'timestamp': current_data_to_display['timestamp']
                    })
                else:
                    # 数据过期,停止所有警报
                    self.alarmWidget.stop_all_alarms()
            except ValueError:
                print(f"警报检查时时间戳格式错误: {current_data_to_display['timestamp']}", file=sys.stderr)
                self.alarmWidget.stop_all_alarms()  # 时间戳错误也停止警报
            except Exception as e:
                print(f"检查警报规则时发生错误: {e}", file=sys.stderr)
                self.alarmWidget.stop_all_alarms()  # 其他错误也停止警报
        else:
            # 如果没有任何数据，也确保停止所有警报
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
            self.alarmWidget.stop_all_alarms()  # 确保关闭时停止所有警报声音

        super().closeEvent(event)
        app_instance = QCoreApplication.instance()
        if app_instance:
            app_instance.quit()  # 请求应用程序退出
        print("应用程序已请求退出。")


def start_fluent_application():
    """
    启动 Fluent UI 应用程序的入口函数。
    """
    import signal
    # 允许 Ctrl+C 终止应用
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 启用高 DPI 缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # 设置全局字体
    font = app.font()
    font.setFamily("Microsoft YaHei UI, Segoe UI")  # <--- 更改全局字体
    font.setPointSize(10)  # 默认字号
    app.setFont(font)

    # 设置初始主题
    setTheme(Theme.LIGHT)

    window = MainWindow()
    window.show()

    # 尝试将窗口居中显示
    try:
        desktop = QApplication.desktop().availableGeometry()  # QDesktopWidget 在 PyQt6 中已移除，PyQt5 中仍可用
        window_rect = window.frameGeometry()
        window_rect.moveCenter(desktop.center())

        # 确保窗口不会超出屏幕边界，并向上微调30像素
        target_top = max(window_rect.top() - 30, desktop.top())
        target_left = max(window_rect.left(), desktop.left())

        if target_left + window_rect.width() > desktop.right():
            target_left = desktop.right() - window_rect.width()
        if target_top + window_rect.height() > desktop.bottom():
            target_top = desktop.bottom() - window_rect.height()

        target_left = max(0, target_left)  # 确保不小于0
        target_top = max(0, target_top)  # 确保不小于0

        window.move(target_left, target_top)
    except Exception as e:
        # 如果居中失败（例如在某些窗口管理器下），则移动到默认位置
        print(f"无法将窗口居中: {e}", file=sys.stderr)
        window.move(100, 100)  # 默认位置

    sys.exit(app.exec_())


if __name__ == '__main__':
    start_fluent_application()