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

    def __init__(self, parent_app, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app
        # self.router_process = None # 移除 - router 不再由 splash 管理
        self.fluent_process = None
        self.processes_launched_successfully = False

        setTheme(Theme.LIGHT) # 或者 Theme.DARK
        self.init_ui()
        self.start_background_processes()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(300, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addStretch(1)

        self.progressRing = ProgressRing(self)
        self.progressRing.setFixedSize(70, 70)
        self.progressRing.setStrokeWidth(5)
        self.progressRing.setRange(0, 100)
        self.progressRing.setValue(0)
        self.progressRing.setTextVisible(True)

        layout.addWidget(self.progressRing, 0, Qt.AlignCenter)
        layout.addSpacing(15)

        self.statusLabel = QLabel("正在准备...", self) # 初始状态
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
        self.statusLabel.setText("启动主界面...")
        self.progressRing.setValue(30)
        if self.parent_app: self.parent_app.processEvents()


        self.statusLabel.setText("启动主界面...")
        self.progressRing.setValue(60)
        if self.parent_app: self.parent_app.processEvents()
        print("INFO: Splash - Starting fluent.py process...")
        self.fluent_process = multiprocessing.Process(
            target=start_script_in_process,
            args=("fluent", "start_fluent_application"),
            daemon=False
        )
        self.fluent_process.start()
        time.sleep(0.1) # 给 fluent 一点时间启动

        if not self.fluent_process.is_alive():
            print("ERROR: Splash - fluent.py process failed to start.", file=sys.stderr)
            self.statusLabel.setText("主界面启动失败!")
            self.progressRing.setValue(80)
            QTimer.singleShot(3000, self.close_and_exit_app)
            return

        print("INFO: Splash - Fluent process seems to be alive.")
        self.statusLabel.setText("加载完成!")
        self.progressRing.setValue(100)
        self.processes_launched_successfully = True
        QTimer.singleShot(700, self.close_splash_only)

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

    def close_and_exit_app(self):
        print("INFO: Splash - Closing splash and exiting application due to failure.")
        self.close()
        if self.parent_app:
            self.parent_app.quit()

    def closeEvent(self, event):
        if not self.processes_launched_successfully:
            print("INFO: Splash (closeEvent) - Splash closed before successful launch.")
            if self.fluent_process and self.fluent_process.is_alive():
                print("INFO: Splash (closeEvent) - Terminating fluent.py process.")
                self.fluent_process.terminate()
                self.fluent_process.join(timeout=1)
        super().closeEvent(event)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    splash_screen = SplashScreenClientSimplified(parent_app=app)
    splash_screen.show()

    exit_code = app.exec_()

    print(f"INFO: Main (Splash) - Splash application event loop finished with code {exit_code}.")

    if not splash_screen.processes_launched_successfully:
        if splash_screen.fluent_process and splash_screen.fluent_process.is_alive():
            print("WARN: Main (Splash) - Fluent process still alive after splash indicated launch failure. Attempting to terminate.")
            splash_screen.fluent_process.terminate()
            splash_screen.fluent_process.join(timeout=1)

    sys.exit(exit_code)