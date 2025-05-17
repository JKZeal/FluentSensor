import sys
import multiprocessing
import time
import os

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont
from qfluentwidgets import ProgressRing, setTheme, Theme, CardWidget, isDarkTheme

# --- 辅助函数，用于在独立进程中运行目标脚本 (保持不变) ---
def start_script_in_process(script_name, entry_function_name):
    module_name = script_name.replace(".py", "")
    try:
        module = __import__(module_name)
        entry_function = getattr(module, entry_function_name)
        entry_function()
    except ImportError as e:
        print(f"ERROR: Splash - Could not import module {module_name}: {e}", file=sys.stderr)
    except AttributeError as e:
        print(f"ERROR: Splash - Could not find entry function {entry_function_name} in {module_name}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Splash - Exception in {module_name} process: {e}", file=sys.stderr)


# --- 工作线程类，用于后台启动进程 ---
class ProcessLauncherThread(QThread):
    # 信号定义：参数 (状态文本, 百分比, 是否成功)
    update_progress_signal = pyqtSignal(str, int, bool)
    finished_signal = pyqtSignal(bool, list) # 参数 (是否所有进程都成功, 错误消息列表)

    def __init__(self):
        super().__init__()
        self.router_process = None
        self.fluent_process = None

    def run(self):
        all_ok = True
        error_messages = []
        current_progress = 10 # 初始进度

        try:
            self.update_progress_signal.emit("正在初始化...", current_progress, True)
            time.sleep(0.5) # 短暂模拟初始化

            # 1. 启动 Router 服务
            current_progress = 40
            self.update_progress_signal.emit("启动数据服务...", current_progress, True)
            self.router_process = multiprocessing.Process(
                target=start_script_in_process,
                args=("router.py", "receive_tcp_data"),
                daemon=False
            )
            self.router_process.start()
            time.sleep(1) # 给进程一点时间启动

            if not self.router_process.is_alive():
                all_ok = False
                error_messages.append("数据服务未能启动。")
                self.update_progress_signal.emit("数据服务启动失败!", current_progress, False) # 失败时也更新
            else:
                self.update_progress_signal.emit("数据服务已启动。", current_progress, True)
                print("INFO: Splash Thread - Router process started.")

            # 2. 启动 Fluent 主程序 (仅当 router 成功时)
            if all_ok:
                current_progress = 70
                self.update_progress_signal.emit("启动主程序...", current_progress, True)
                self.fluent_process = multiprocessing.Process(
                    target=start_script_in_process,
                    args=("fluent.py", "start_fluent_application"),
                    daemon=False
                )
                self.fluent_process.start()
                time.sleep(1) # 给GUI更多时间

                if not self.fluent_process.is_alive():
                    all_ok = False
                    error_messages.append("主程序未能启动。")
                    self.update_progress_signal.emit("主程序启动失败!", current_progress, False)
                    if self.router_process and self.router_process.is_alive():
                        print("INFO: Splash Thread - Terminating router due to fluent failure.")
                        self.router_process.terminate()
                        self.router_process.join(timeout=1)
                else:
                    current_progress = 100
                    self.update_progress_signal.emit("主程序已启动。", current_progress, True)
                    print("INFO: Splash Thread - Fluent process started.")
            else: # 如果router失败，直接跳过fluent的启动
                self.update_progress_signal.emit("因依赖服务失败，主程序未启动。", current_progress, False)


        except Exception as e:
            all_ok = False
            error_messages.append(f"启动时发生意外错误: {e}")
            self.update_progress_signal.emit(f"发生错误: {e}", current_progress, False)
            print(f"ERROR: Splash Thread - Exception during process startup: {e}", file=sys.stderr)

        self.finished_signal.emit(all_ok, error_messages)

    def get_processes(self):
        return self.router_process, self.fluent_process


class SplashScreen(CardWidget):
    def __init__(self, parent_app, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app
        self.launcher_thread = None # 初始化线程变量

        setTheme(Theme.LIGHT)
        self.init_ui()

        # 启动后台线程
        self.start_launcher_thread()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(300, 220) # 可以稍微调大一点以容纳更长的文本

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25) # 增加边距
        layout.addStretch(1)

        self.progressRing = ProgressRing(self)
        self.progressRing.setFixedSize(80, 80) # 稍大一点的环
        self.progressRing.setStrokeWidth(6)
        self.progressRing.setRange(0, 100)
        self.progressRing.setValue(0)
        self.progressRing.setTextVisible(True)

        layout.addWidget(self.progressRing, 0, Qt.AlignCenter)
        layout.addSpacing(20) # 增加间距

        self.statusLabel = QLabel("请稍候...", self)
        font = QFont("Microsoft YaHei UI", 11) # 稍大一点的字体
        self.statusLabel.setFont(font)
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.statusLabel.setWordWrap(True) # 允许文本换行
        if isDarkTheme():
             self.statusLabel.setStyleSheet("color: #E0E0E0;")
        else:
            self.statusLabel.setStyleSheet("color: #303030;") # 更深的灰色

        layout.addWidget(self.statusLabel, 0, Qt.AlignCenter)
        layout.addStretch(1)
        self.center_on_screen()

    def start_launcher_thread(self):
        self.launcher_thread = ProcessLauncherThread()
        self.launcher_thread.update_progress_signal.connect(self.handle_progress_update)
        self.launcher_thread.finished_signal.connect(self.handle_launch_finished)
        self.launcher_thread.start() # 启动线程

    def handle_progress_update(self, status_text, percentage, success):
        self.statusLabel.setText(status_text)
        self.progressRing.setValue(percentage)
        # 可以根据 success 参数改变进度环颜色，但 qfluentwidgets.ProgressRing 可能不直接支持
        # if not success:
        #     self.progressRing.setStyleSheet("QProgressBar::chunk { background-color: red; }") # 示例
        if self.parent_app:
            self.parent_app.processEvents()

    def handle_launch_finished(self, all_ok, error_messages):
        if all_ok:
            self.statusLabel.setText("启动完成!")
            self.progressRing.setValue(100) # 确保最终是100%
            QTimer.singleShot(700, self.close_splash_and_exit)
        else:
            final_error_message = "启动失败。\n" + "\n".join(error_messages) if error_messages else "未知启动错误。"
            self.statusLabel.setText(error_messages[0] if error_messages else "启动失败")
            # self.progressRing.setValue(0) # 或者保持在失败时的进度
            print(final_error_message, file=sys.stderr)
            QTimer.singleShot(6000, self.close_splash_and_exit)

    def center_on_screen(self):
        try:
            if self.parent_app:
                screen_geometry = self.parent_app.primaryScreen().availableGeometry()
                self_geometry = self.frameGeometry()
                self.move(screen_geometry.center() - self_geometry.center())
        except AttributeError:
            pass

    def close_splash_and_exit(self):
        self.close()
        if self.parent_app:
            self.parent_app.quit()

    def closeEvent(self, event):
        # 确保在splash意外关闭时，如果进程仍在运行且主应用未成功启动，则尝试终止它们
        if self.launcher_thread: # 检查线程是否存在
            router_process, fluent_process = self.launcher_thread.get_processes()
            if router_process and router_process.is_alive():
                if not fluent_process or not fluent_process.is_alive():
                    print("INFO: Splash (closeEvent) - Fluent process not running, terminating router process.")
                    router_process.terminate()
                    router_process.join(timeout=1)
        super().closeEvent(event)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    splash_screen = SplashScreen(parent_app=app)
    splash_screen.show()
    exit_code = app.exec_()
    sys.exit(exit_code)