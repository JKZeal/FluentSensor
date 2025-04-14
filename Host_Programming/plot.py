import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import HeaderCardWidget, BodyLabel, SingleDirectionScrollArea
import pyqtgraph as pg

class PlotWidget(pg.PlotWidget):
    def __init__(self, title="", y_label="", dark_mode=False):
        super().__init__()
        self.plot_title = title
        self.y_axis_label = y_label
        self.dark_mode = dark_mode
        self.setMinimumHeight(240)
        self.setBackground(None)
        self.data = {'time': [], 'value': []}
        self.curve = self.plot(pen=pg.mkPen(color='#0078d4', width=2.5))
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.plotItem.setAxisItems({'bottom': date_axis})
        font = QFont()
        font.setFamily("Microsoft YaHei UI")
        font.setPointSize(9)
        self.getAxis('bottom').tickFont = font
        self.getAxis('left').tickFont = font
        self.update_theme(dark_mode)

    def update_theme(self, dark_mode):
        self.dark_mode = dark_mode
        if dark_mode:
            bg_color = QColor(30, 30, 30, 0)
            curve_color = '#60cdff'
            text_color = '#ffffff'
            title_color = '#ffffff'
            grid_alpha = 0.2
        else:
            bg_color = QColor(250, 250, 250, 0)
            curve_color = '#0078d4'
            text_color = '#202020'
            title_color = '#000000'
            grid_alpha = 0.15
        self.setBackground(bg_color)
        self.plotItem.showGrid(x=True, y=True, alpha=grid_alpha)
        if self.plot_title:
            self.plotItem.setTitle(self.plot_title, color=title_color, size="13pt", bold=True)
        self.plotItem.setLabel('left', self.y_axis_label, color=text_color)
        self.plotItem.setLabel('bottom', 'Time', color=text_color)
        self.getAxis('left').setPen(pg.mkPen(color=text_color, width=1))
        self.getAxis('bottom').setPen(pg.mkPen(color=text_color, width=1))
        self.getAxis('left').setTextPen(text_color)
        self.getAxis('bottom').setTextPen(text_color)
        for axis in ['left', 'bottom']:
            ax = self.getAxis(axis)
            try:
                ax.setStyle(brush=QColor(0, 0, 0, 0))
            except:
                pass
        self.curve.setPen(pg.mkPen(color=curve_color, width=2.5))

    def update_data(self, new_times, new_values):
        if not isinstance(new_times, list):
            new_times = [new_times]
        if not isinstance(new_values, list):
            new_values = [new_values]
        self.data['time'] = new_times
        self.data['value'] = new_values
        self.curve.setData(np.array(new_times, dtype=np.float64), np.array(new_values, dtype=np.float64))
        if new_times:
            x_min, x_max = min(new_times), max(new_times)
            y_min, y_max = min(new_values), max(new_values)
            padding_x = (x_max - x_min) * 0.05 if x_min != x_max else 86400
            padding_y = (y_max - y_min) * 0.1 if y_min != y_max else 1
            self.plotItem.setXRange(x_min - padding_x, x_max + padding_x)
            self.plotItem.setYRange(y_min - padding_y, y_max + padding_y)

class PlotCard(HeaderCardWidget):
    def __init__(self, title, y_label, dark_mode=False, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setBorderRadius(8)
        self.plot_widget = PlotWidget("", y_label, dark_mode)
        self.plot_widget.setMinimumHeight(240)
        self.viewLayout.addWidget(self.plot_widget)

    def update_data(self, times, values):
        self.plot_widget.update_data(times, values)

    def update_theme(self, dark_mode):
        self.plot_widget.update_theme(dark_mode)

class PlotsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("plotsWidget")
        self.setup_ui()

    def setup_ui(self):
        from qfluentwidgets import isDarkTheme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.title_label = BodyLabel("数据图表", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        self.scroll_area = SingleDirectionScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea {background: transparent; border: none;} QScrollArea > QWidget > QWidget {background: transparent;} QScrollArea > QWidget {background: transparent;}")
        self.plots_container = QWidget()
        self.plots_container.setObjectName("plotsContainerWidget")
        self.plots_container.setStyleSheet("#plotsContainerWidget {background: transparent; border: none;}")
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.setSpacing(16)
        dark_mode = isDarkTheme()
        self.temp_plot = PlotCard("温度趋势", "温度 (°C)", dark_mode)
        self.humidity_plot = PlotCard("湿度趋势", "湿度 (%)", dark_mode)
        self.pm25_plot = PlotCard("PM2.5趋势", "PM2.5 (μg/m³)", dark_mode)
        self.noise_plot = PlotCard("噪声趋势", "噪声 (dB)", dark_mode)
        self.plots_layout.addWidget(self.temp_plot)
        self.plots_layout.addWidget(self.humidity_plot)
        self.plots_layout.addWidget(self.pm25_plot)
        self.plots_layout.addWidget(self.noise_plot)
        self.scroll_area.setWidget(self.plots_container)
        layout.addWidget(self.scroll_area, 1)

    def update_data(self, times=None, temp_history=None, humidity_history=None, pm25_history=None, noise_history=None):
        if times is not None:
            if temp_history is not None:
                self.temp_plot.update_data(times, temp_history)
            if humidity_history is not None:
                self.humidity_plot.update_data(times, humidity_history)
            if pm25_history is not None:
                self.pm25_plot.update_data(times, pm25_history)
            if noise_history is not None:
                self.noise_plot.update_data(times, noise_history)

    def update_theme(self, dark_mode):
        self.temp_plot.update_theme(dark_mode)
        self.humidity_plot.update_theme(dark_mode)
        self.pm25_plot.update_theme(dark_mode)
        self.noise_plot.update_theme(dark_mode)