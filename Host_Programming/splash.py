# splash_client_simplified.py
import sys
import multiprocessing
import time
import os

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont
from qfluentwidgets import ProgressRing, setTheme, Theme, CardWidget, isDarkTheme

def start_script_in_process(script_name, entry_function_name, *args_for_entry):
    module_name = script_name.replace(".py", "")
    try:
        module = __import__(module_name)
        entry_function = getattr(module, entry_function_name)
        if args_for_entry:
            print(f"INFO: Splash Process - Calling {module_name}.{entry_function_name} with args: {args_for_entry}")
            entry_function(*args_for_entry)
        else:
            print(f"INFO: Splash Process - Calling {module_name}.{entry_function_name} without args")
            entry_function()
        print(f"INFO: Splash Process - {module_name}.{entry_function_name} finished.")
    except ImportError as e:
        print(f"ERROR: Splash Process - Could not import module {module_name}: {e}", file=sys.stderr)
    except AttributeError as e:
        print(f"ERROR: Splash Process - Could not find entry function {entry_function_name} in {module_name}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Splash Process - Exception in {module_name} ({entry_function_name}) process: {e}", file=sys.stderr)

class SplashScreenClientSimplified(CardWidget):
    ROUTER_TARGET_IP = "192.168.4.1"  # 默认连接的 IP
    ROUTER_TARGET_PORT = 6666        # 默认连接的端口

    def __init__(self, parent_app, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app
        self.router_process = None
        self.fluent_process = None
        self.processes_launched_successfully = False # 标志位

        setTheme(Theme.LIGHT) # 或者 Theme.DARK
        self.init_ui()
        self.start_background_processes()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(300, 200) # 稍微调整大小

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addStretch(1)

        self.progressRing = ProgressRing(self)
        self.progressRing.setFixedSize(70, 70)
        self.progressRing.setStrokeWidth(5)
        self.progressRing.setRange(0, 100) # 我们会模拟进度
        self.progressRing.setValue(0)
        self.progressRing.setTextVisible(True)

        layout.addWidget(self.progressRing, 0, Qt.AlignCenter)
        layout.addSpacing(15)

        self.statusLabel = QLabel("正在准备...", self)
        font = QFont("Microsoft YaHei UI", 10)
        self.statusLabel.setFont(font)
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.statusLabel.setWordWrap(True)
        if isDarkTheme():
             self.statusLabel.setStyleSheet("color: #E0E0E0;")
        else:
            self.statusLabel.setStyleSheet("color: #303030;")

        layout.addWidget(self.statusLabel, 0, Qt.AlignCenter)
        layout.addStretch(1)
        self.center_on_screen()

    def start_background_processes(self):
        # 模拟进度更新
        self.statusLabel.setText("启动数据服务...")
        self.progressRing.setValue(30)
        if self.parent_app: self.parent_app.processEvents()

        print("INFO: Splash - Starting router.py process...")
        self.router_process = multiprocessing.Process(
            target=start_script_in_process,
            args=("router", "run_tcp_client", self.ROUTER_TARGET_IP, self.ROUTER_TARGET_PORT),
            daemon=True # 设置为守护进程，如果splash意外退出，它也会退出
                        # 但如果fluent成功启动，fluent的生命周期会更长
        )
        self.router_process.start()
        time.sleep(0.1)

        if not self.router_process.is_alive():
            print("ERROR: Splash - router.py process failed to start.", file=sys.stderr)
            self.statusLabel.setText("数据服务启动失败!")
            self.progressRing.setValue(50) # 更新到某个表示失败的进度
            QTimer.singleShot(3000, self.close_and_exit_app) # 失败则退出整个应用
            return

        self.statusLabel.setText("启动主界面...")
        self.progressRing.setValue(60)
        if self.parent_app: self.parent_app.processEvents()
        print("INFO: Splash - Starting fluent.py process...")
        self.fluent_process = multiprocessing.Process(
            target=start_script_in_process,
            args=("fluent", "start_fluent_application"), # fluent.py 的入口
            daemon=False # 主GUI不应是守护进程
        )
        self.fluent_process.start()
        time.sleep(0.1)

        if not self.fluent_process.is_alive():
            print("ERROR: Splash - fluent.py process failed to start.", file=sys.stderr)
            self.statusLabel.setText("主界面启动失败!")
            self.progressRing.setValue(80)
            if self.router_process and self.router_process.is_alive():
                print("INFO: Splash - Terminating router.py due to fluent.py failure.")
                self.router_process.terminate()
                self.router_process.join(timeout=1)
            QTimer.singleShot(3000, self.close_and_exit_app)
            return

        print("INFO: Splash - Both processes seem to be alive.")
        self.statusLabel.setText("加载完成!")
        self.progressRing.setValue(100)
        self.processes_launched_successfully = True
        QTimer.singleShot(700, self.close_splash_only) # 成功则只关闭splash

    def center_on_screen(self):
        try:
            if self.parent_app:
                screen_geometry = self.parent_app.primaryScreen().availableGeometry()
                self_geometry = self.frameGeometry()
                self.move(screen_geometry.center() - self_geometry.center())
        except AttributeError:
            pass

    def close_splash_only(self):
        print("INFO: Splash - Closing splash screen. Fluent GUI should take over.")
        self.close()
        # 不调用 self.parent_app.quit()，让 fluent 的 QApplication 控制

    def close_and_exit_app(self):
        print("INFO: Splash - Closing splash and exiting application due to failure.")
        self.close()
        if self.parent_app:
            self.parent_app.quit()

    def closeEvent(self, event):
        # 如果 splash 在 fluent 成功启动前被关闭 (例如用户手动关闭)
        # 并且 router 仍在运行，我们应该终止 router，因为 fluent 可能没有机会启动来管理它。
        if not self.processes_launched_successfully:
            print("INFO: Splash (closeEvent) - Splash closed before successful launch.")
            if self.router_process and self.router_process.is_alive():
                print("INFO: Splash (closeEvent) - Terminating router.py process.")
                self.router_process.terminate()
                self.router_process.join(timeout=1)
            if self.fluent_process and self.fluent_process.is_alive(): # 以防万一
                print("INFO: Splash (closeEvent) - Terminating fluent.py process.")
                self.fluent_process.terminate()
                self.fluent_process.join(timeout=1)
        super().closeEvent(event)

if __name__ == '__main__':
    multiprocessing.freeze_support() # 必须在所有 multiprocessing 代码之前
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv) # Splash 自己的 QApplication
    splash_screen = SplashScreenClientSimplified(parent_app=app)
    splash_screen.show()

    exit_code = app.exec_() # 运行 Splash 的事件循环

    print(f"INFO: Main (Splash) - Splash application event loop finished with code {exit_code}.")

    if not splash_screen.processes_launched_successfully:
        if splash_screen.fluent_process and splash_screen.fluent_process.is_alive():
            print("WARN: Main (Splash) - Fluent process still alive after splash indicated launch failure. Attempting to terminate.")
            splash_screen.fluent_process.terminate()
            splash_screen.fluent_process.join(timeout=1)

    sys.exit(exit_code)