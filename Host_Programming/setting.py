from enum import Enum
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QButtonGroup
from qfluentwidgets import (BodyLabel, HeaderCardWidget, ComboBox, Slider, PrimaryPushButton,
                            RadioButton, InfoBar, InfoBarPosition, isDarkTheme, StyleSheetBase,
                            Theme, qconfig)

class StyleSheet(StyleSheetBase, Enum):
    MAIN_WINDOW = "main_window"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f"qss/{theme.value.lower()}/{self.value}.qss"

class TimeRangeSettings(QWidget):
    timeRangeChanged = pyqtSignal(int)
    refreshRateChanged = pyqtSignal(int)
    themeChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timeRangeSettings")
        self.dark_mode = isDarkTheme()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.title_label = BodyLabel("系统设置", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        self.time_card = HeaderCardWidget(self)
        self.time_card.setTitle("时间范围")
        self.time_card.setBorderRadius(8)
        combo_layout = QHBoxLayout()
        combo_label = BodyLabel("显示历史数据时间范围:", self.time_card)
        self.timeComboBox = ComboBox(self.time_card)
        self.timeComboBox.addItems(["1 分钟", "5 分钟", "15 分钟", "30 分钟", "1 小时", "3 小时", "12 小时", "24 小时"])
        self.timeComboBox.setCurrentIndex(1)
        combo_layout.addWidget(combo_label)
        combo_layout.addWidget(self.timeComboBox)
        combo_layout.addStretch()
        self.time_card.viewLayout.addLayout(combo_layout)
        layout.addWidget(self.time_card)
        self.refresh_card = HeaderCardWidget(self)
        self.refresh_card.setTitle("刷新频率")
        self.refresh_card.setBorderRadius(8)
        slider_layout = QHBoxLayout()
        self.refresh_value_label = BodyLabel("数据更新间隔: 2 秒", self.refresh_card)
        self.refresh_value_label.setMinimumWidth(150)
        slider_layout.addWidget(self.refresh_value_label)
        self.refreshSlider = Slider(Qt.Horizontal, self.refresh_card)
        self.refreshSlider.setRange(1, 10)
        self.refreshSlider.setValue(2)
        self.refreshSlider.valueChanged.connect(self.on_refresh_slider_changed)
        slider_layout.addWidget(self.refreshSlider)
        self.refresh_card.viewLayout.addLayout(slider_layout)
        layout.addWidget(self.refresh_card)
        self.theme_card = HeaderCardWidget(self)
        self.theme_card.setTitle("外观主题")
        self.theme_card.setBorderRadius(8)
        radio_layout = QHBoxLayout()
        self.theme_button_group = QButtonGroup(self)
        self.light_radio = RadioButton("浅色主题", self.theme_card)
        self.dark_radio = RadioButton("深色主题", self.theme_card)
        self.light_radio.setChecked(not self.dark_mode)
        self.dark_radio.setChecked(self.dark_mode)
        self.theme_button_group.addButton(self.light_radio, 0)
        self.theme_button_group.addButton(self.dark_radio, 1)
        radio_layout.addWidget(self.light_radio)
        radio_layout.addWidget(self.dark_radio)
        radio_layout.addStretch()
        self.theme_card.viewLayout.addLayout(radio_layout)
        layout.addWidget(self.theme_card)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.applyButton = PrimaryPushButton("应用设置", self)
        self.applyButton.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.applyButton)
        layout.addLayout(button_layout)
        layout.addStretch()

    def on_refresh_slider_changed(self, value):
        self.refresh_value_label.setText(f"数据更新间隔: {value} 秒")

    def apply_settings(self):
        time_ranges = [1, 5, 15, 30, 60, 180, 720, 1440]
        index = self.timeComboBox.currentIndex()
        self.timeRangeChanged.emit(time_ranges[index])
        refresh_rate = self.refreshSlider.value()
        self.refreshRateChanged.emit(refresh_rate)
        dark_mode = self.dark_radio.isChecked()
        if dark_mode != self.dark_mode:
            self.themeChanged.emit(dark_mode)
            self.dark_mode = dark_mode
        InfoBar.success(title='设置已应用', content='您的设置已成功应用', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self.window())