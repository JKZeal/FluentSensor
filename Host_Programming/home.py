from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout
from qfluentwidgets import HeaderCardWidget, BodyLabel, ElevatedCardWidget, FluentIcon, IconWidget, CaptionLabel

class RealtimeDataCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("实时环境数据")
        self.setBorderRadius(8)
        indicator_layout = QGridLayout()
        indicator_layout.setHorizontalSpacing(16)
        indicator_layout.setVerticalSpacing(12)
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_indicator = self._create_indicator("更新时间", current_time, FluentIcon.HISTORY, time_card=True)
        self.temp_indicator = self._create_indicator("温度", "0°C", FluentIcon.CALORIES)
        self.humidity_indicator = self._create_indicator("湿度", "0%", FluentIcon.CLOUD)
        self.pm25_indicator = self._create_indicator("PM2.5", "0 μg/m³", FluentIcon.LEAF)
        self.noise_indicator = self._create_indicator("噪声", "0 dB", FluentIcon.SPEAKERS)
        indicator_layout.addWidget(self.time_indicator, 0, 0, 1, 2)
        indicator_layout.addWidget(self.temp_indicator, 1, 0)
        indicator_layout.addWidget(self.humidity_indicator, 1, 1)
        indicator_layout.addWidget(self.pm25_indicator, 2, 0)
        indicator_layout.addWidget(self.noise_indicator, 2, 1)
        indicator_layout.setColumnStretch(0, 1)
        indicator_layout.setColumnStretch(1, 1)
        self.viewLayout.addLayout(indicator_layout)

    def _create_indicator(self, name, value, icon, time_card=False):
        card = ElevatedCardWidget()
        card.setBorderRadius(8)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        header_layout = QHBoxLayout()
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(20, 20)
        name_label = CaptionLabel(name)
        name_label.setStyleSheet("font-size: 13px; font-weight: 500; color: var(--text-color-secondary);")
        header_layout.addWidget(icon_widget)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        value_label = BodyLabel(value)
        value_label.setObjectName(f"{name.lower().replace('.', '_')}_value")
        if time_card:
            value_label.setStyleSheet("font-size: 16px; font-weight: 600;")
            card.setMinimumHeight(100)
        else:
            value_label.setStyleSheet("font-size: 22px; font-weight: 600;")
            card.setMinimumHeight(100)
        value_label.setAlignment(Qt.AlignCenter)
        layout.addLayout(header_layout)
        layout.addWidget(value_label)
        return card

    def update_data(self, temperature=None, humidity=None, pm25=None, noise=None, timestamp=None):
        from datetime import datetime
        if timestamp:
            self.time_indicator.findChild(BodyLabel, "更新时间_value").setText(timestamp)
        else:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_indicator.findChild(BodyLabel, "更新时间_value").setText(current_time)
        if temperature is not None:
            self.temp_indicator.findChild(BodyLabel, "温度_value").setText(f"{temperature:.1f}°C")
        if humidity is not None:
            self.humidity_indicator.findChild(BodyLabel, "湿度_value").setText(f"{humidity:.1f}%")
        if pm25 is not None:
            self.pm25_indicator.findChild(BodyLabel, "pm2_5_value").setText(f"{pm25:.0f} μg/m³")
        if noise is not None:
            self.noise_indicator.findChild(BodyLabel, "噪声_value").setText(f"{noise:.0f} dB")

class HomeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeWidget")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.data_card = RealtimeDataCard(self)
        layout.addWidget(self.data_card)
        layout.addStretch()

    def update_data(self, temperature=None, humidity=None, pm25=None, noise=None, timestamp=None):
        self.data_card.update_data(temperature, humidity, pm25, noise, timestamp)