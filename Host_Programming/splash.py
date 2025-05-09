import sys
import multiprocessing
import time
import os

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QLabel, QWidget
from qfluentwidgets import ProgressRing, CardWidget, setTheme, Theme

# --- 目标函数：用于在新进程中运行其他脚本 ---

def run_fluent_app():
    """在新进程中启动 Fluent UI 应用程序"""
    try:
        from fluent import start_fluent_gui
        start_fluent_gui()
    except ImportError as e:
        print(f"启动 Fluent UI 失败: 无法导入模块 - {e}", file=sys.stderr)
    except Exception as e:
        print(f"启动 Fluent UI 时发生错误: {e}", file=sys.stderr)
        # 在这里可以添加更详细的错误记录或通知机制

def run_router_service():
    """在新进程中启动数据接收服务"""
    try:
        from router import receive_tcp_data
        receive_tcp_data()
    except ImportError as e:
        print(f"启动 Router 服务失败: 无法导入模块 - {e}", file=sys.stderr)
    except Exception as e:
        print(f"启动 Router 服务时发生错误: {e}", file=sys.stderr)

# --- 简单的启动画面 Widget ---

class SimpleSplashScreen(CardWidget):
    """一个简单的启动画面，包含进度环和状态文本"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置窗口属性：无边框、总在最前、启动画面样式
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        # 设置背景透明，依赖 CardWidget 的背景
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.progressRing = ProgressRing(self)
        self.statusLabel = QLabel("正在初始化...", self)

        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20) # 内边距
        layout.addStretch(1)
        layout.addWidget(self.progressRing, 0, Qt.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(self.statusLabel, 0, Qt.AlignCenter)
        layout.addStretch(1)

        # 样式和大小
        self.progressRing.setFixedSize(70, 70) # 调整进度环大小
        self.progressRing.setStrokeWidth(5)    # 调整进度环厚度
        self.progressRing.setTextVisible(True) # 显示百分比文本
        self.statusLabel.setStyleSheet("color: grey;") # 状态文本颜色
        self.setFixedSize(220, 180) # 设置卡片大小

        # 初始化进度
        self.progressRing.setRange(0, 100)
        self.progressRing.setValue(0)

    def update_progress(self, value, status_text):
        """更新进度环的值和状态文本"""
        self.progressRing.setValue(value)
        self.statusLabel.setText(status_text)
        QApplication.processEvents() # 强制 UI 更新

    def center_on_screen(self):
        """将窗口移动到屏幕中央"""
        try:
            screen_geometry = QApplication.primaryScreen().availableGeometry()
            self_geometry = self.frameGeometry()
            self.move(screen_geometry.center() - self_geometry.center())
        except AttributeError:
            # 在某些环境下 QApplication.primaryScreen() 可能不可用
            pass

# --- 应用程序启动器 ---

class AppLauncher:
    """管理启动画面显示和进程启动"""
    def __init__(self):
        self.splash = SimpleSplashScreen()
        self.splash.center_on_screen()
        self.splash.show()
        self.splash.update_progress(20, "初始化...")

        # 使用 QTimer 延迟启动进程，确保事件循环已开始运行
        QTimer.singleShot(200, self.start_processes)

    def start_processes(self):
        """启动数据服务和主界面进程"""
        try:
            # 1. 启动数据接收服务 (后台进程)
            self.splash.update_progress(50, "启动数据服务...")
            # daemon=True 意味着当主程序（启动器）退出时，这个进程也会被尝试终止
            # 但由于主程序很快会退出，而 fluent 进程会接管，实际效果是 router 会随 fluent 退出
            self.router_process = multiprocessing.Process(target=run_router_service, daemon=True)
            self.router_process.start()
            time.sleep(0.5) # 短暂等待，确保进程已启动

            # 检查 router 进程是否成功启动 (基本检查)
            if not self.router_process.is_alive():
                 raise RuntimeError("数据服务进程未能启动")

            # 2. 启动主界面 (前台进程)
            self.splash.update_progress(80, "启动图形界面...")
            self.fluent_process = multiprocessing.Process(target=run_fluent_app)
            self.fluent_process.start()
            time.sleep(0.5) # 短暂等待

            if not self.fluent_process.is_alive():
                 raise RuntimeError("图形界面进程未能启动")

            self.splash.update_progress(100, "启动完成!")

            # 启动成功，短暂显示 "完成" 后关闭启动画面
            QTimer.singleShot(800, self.finish)

        except Exception as e:
            error_message = f"启动失败: {e}"
            print(error_message, file=sys.stderr)
            self.splash.update_progress(0, error_message)
            # 发生错误时，保持启动画面显示几秒钟以便用户看到错误信息
            QTimer.singleShot(5000, self.splash.close)
            # 启动器本身也应该退出
            QTimer.singleShot(5100, QApplication.instance().quit)


    def finish(self):
        """关闭启动画面并退出启动器应用程序"""
        self.splash.close()
        # 启动器任务完成，退出其 QApplication 实例
        # fluent 进程有自己的 QApplication 实例在运行
        QApplication.instance().quit()


# --- 主执行入口 ---

if __name__ == '__main__':
    # 对于使用 multiprocessing 打包成 exe (如用 PyInstaller) 时，这行是必需的
    multiprocessing.freeze_support()

    # 为启动画面本身设置高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 可以为启动画面设置一个基础主题
    setTheme(Theme.LIGHT)

    # 创建并运行启动器
    launcher = AppLauncher()

    # 启动启动器应用程序的事件循环
    # 当 launcher.finish() 调用 app.quit() 时，事件循环会结束
    sys.exit(app.exec_())