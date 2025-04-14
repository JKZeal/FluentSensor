import sqlite3

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QTableWidgetItem
from qfluentwidgets import (HeaderCardWidget, BodyLabel, PrimaryPushButton, PushButton,
                            ZhDatePicker, TableWidget,InfoBar, InfoBarPosition, StrongBodyLabel)

DB_PATH = "db/sensor_data.db"

class EnvironmentStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.temp_status = StrongBodyLabel("适宜")
        self.temp_status.setFixedHeight(28)
        self.temp_status.setAlignment(Qt.AlignCenter)
        self.temp_status.setObjectName("tempLabel")
        self.humidity_status = StrongBodyLabel("适宜")
        self.humidity_status.setFixedHeight(28)
        self.humidity_status.setAlignment(Qt.AlignCenter)
        self.humidity_status.setObjectName("humidityLabel")
        self.pm25_status = StrongBodyLabel("良好")
        self.pm25_status.setFixedHeight(28)
        self.pm25_status.setAlignment(Qt.AlignCenter)
        self.pm25_status.setObjectName("pm25Label")
        self.noise_status = StrongBodyLabel("安静")
        self.noise_status.setFixedHeight(28)
        self.noise_status.setAlignment(Qt.AlignCenter)
        self.noise_status.setObjectName("noiseLabel")
        self._setup_label_style(self.temp_status)
        self._setup_label_style(self.humidity_status)
        self._setup_label_style(self.pm25_status)
        self._setup_label_style(self.noise_status)
        self.set_status_colors("适宜", "适宜", "良好", "安静")
        layout.addWidget(self.temp_status)
        layout.addWidget(self.humidity_status)
        layout.addWidget(self.pm25_status)
        layout.addWidget(self.noise_status)

    def _setup_label_style(self, label):
        label.setStyleSheet("StrongBodyLabel {border-radius: 4px; padding: 2px 8px; color: white; font-weight: bold;}")

    def set_status_colors(self, temp_status, humidity_status, pm25_status, noise_status):
        self.temp_status.setText(temp_status)
        self.temp_status.setStyleSheet(f"StrongBodyLabel#tempLabel {{background-color: {'#007ad9' if temp_status == '寒冷' else '#16a34a' if temp_status == '适宜' else '#e11d48'}; border-radius: 4px; padding: 2px 8px; color: white; font-weight: bold;}}")
        self.humidity_status.setText(humidity_status)
        self.humidity_status.setStyleSheet(f"StrongBodyLabel#humidityLabel {{background-color: {'#eab308' if humidity_status == '干燥' else '#16a34a' if humidity_status == '适宜' else '#0284c7'}; border-radius: 4px; padding: 2px 8px; color: white; font-weight: bold;}}")
        self.pm25_status.setText(pm25_status)
        self.pm25_status.setStyleSheet(f"StrongBodyLabel#pm25Label {{background-color: {'#16a34a' if pm25_status == '良好' else '#eab308' if pm25_status == '轻度污染' else '#e11d48'}; border-radius: 4px; padding: 2px 8px; color: white; font-weight: bold;}}")
        self.noise_status.setText(noise_status)
        self.noise_status.setStyleSheet(f"StrongBodyLabel#noiseLabel {{background-color: {'#16a34a' if noise_status == '安静' else '#eab308' if noise_status == '一般' else '#e11d48'}; border-radius: 4px; padding: 2px 8px; color: white; font-weight: bold;}}")

class HistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyWidget")
        self.dark_mode = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.title_label = BodyLabel("历史记录", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        self.date_card = HeaderCardWidget(self)
        self.date_card.setTitle("选择日期")
        self.date_card.setBorderRadius(8)
        picker_layout = QHBoxLayout()
        self.date_picker = ZhDatePicker(self.date_card)
        self.date_picker.setDate(QDate.currentDate())
        picker_layout.addWidget(self.date_picker)
        self.query_button = PrimaryPushButton("查询", self.date_card)
        self.query_button.clicked.connect(self.query_data)
        picker_layout.addWidget(self.query_button)
        self.export_button = PushButton("导出为CSV", self.date_card)
        self.export_button.clicked.connect(self.export_data)
        picker_layout.addWidget(self.export_button)
        picker_layout.addStretch()
        self.date_card.viewLayout.addLayout(picker_layout)
        layout.addWidget(self.date_card)
        self.results_card = HeaderCardWidget(self)
        self.results_card.setTitle("查询结果")
        self.results_card.setBorderRadius(8)
        self.table = TableWidget(self.results_card)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setColumnCount(6)
        self.table.setEditTriggers(TableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(['时间', '温度(°C)', '湿度(%)', 'PM2.5(μg/m³)', '噪声(dB)', '状态'])
        self.table.verticalHeader().hide()
        self.table.setSelectRightClickedRow(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.results_card.viewLayout.addWidget(self.table)
        layout.addWidget(self.results_card, 1)

    def query_data(self):
        selected_date = self.date_picker.getDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            cursor = conn.cursor()
            start_date = f"{date_str} 00:00:00"
            end_date = f"{date_str} 23:59:59"
            cursor.execute("SELECT timestamp, temperature, humidity, pm25, noise FROM sensor_data WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC", (start_date, end_date))
            results = cursor.fetchall()
            conn.close()
            self.update_table(results)
            if results:
                InfoBar.success(title='查询成功', content=f'找到 {len(results)} 条记录', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self.window())
            else:
                InfoBar.info(title='无数据', content=f'所选日期 {date_str} 没有记录', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self.window())
        except Exception as e:
            InfoBar.error(title='查询错误', content=f'发生错误: {str(e)}', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self.window())

    def update_table(self, data):
        self.table.setRowCount(0)
        if not data:
            return
        thresholds = {'temp': {'寒冷': (-20, 10), '适宜': (10, 26), '炎热': (26, 60)}, 'humidity': {'干燥': (0, 40), '适宜': (40, 70), '潮湿': (70, 100)}, 'pm25': {'良好': (0, 35), '轻度污染': (35, 75), '重度污染': (75, 1000)}, 'noise': {'安静': (0, 45), '一般': (45, 65), '嘈杂': (65, 120)}}
        for row_idx, row_data in enumerate(data):
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(row_data[0]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{row_data[1]:.1f}"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{row_data[2]:.1f}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{row_data[3]}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{row_data[4]}"))
            temp_status = self._evaluate_temp(row_data[1], thresholds['temp'])
            humidity_status = self._evaluate_humidity(row_data[2], thresholds['humidity'])
            pm25_status = self._evaluate_pm25(row_data[3], thresholds['pm25'])
            noise_status = self._evaluate_noise(row_data[4], thresholds['noise'])
            status_widget = EnvironmentStatusWidget()
            status_widget.set_status_colors(temp_status, humidity_status, pm25_status, noise_status)
            self.table.setCellWidget(row_idx, 5, status_widget)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(5, 300)

    def _evaluate_temp(self, value, thresholds):
        if value < thresholds['适宜'][0]:
            return "寒冷"
        elif value > thresholds['适宜'][1]:
            return "炎热"
        return "适宜"

    def _evaluate_humidity(self, value, thresholds):
        if value < thresholds['适宜'][0]:
            return "干燥"
        elif value > thresholds['适宜'][1]:
            return "潮湿"
        return "适宜"

    def _evaluate_pm25(self, value, thresholds):
        if value <= thresholds['良好'][1]:
            return "良好"
        elif value <= thresholds['轻度污染'][1]:
            return "轻度污染"
        return "重度污染"

    def _evaluate_noise(self, value, thresholds):
        if value <= thresholds['安静'][1]:
            return "安静"
        elif value <= thresholds['一般'][1]:
            return "一般"
        return "嘈杂"

    def export_data(self):
        if self.table.rowCount() == 0:
            InfoBar.warning(title='导出失败', content='没有数据可导出', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self.window())
            return
        selected_date = self.date_picker.getDate().toString("yyyy-MM-dd")
        default_name = f"环境数据_{selected_date}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存CSV文件", default_name, "CSV 文件 (*.csv)")
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                f.write(','.join(headers) + '\n')
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        if col == 5:
                            status_widget = self.table.cellWidget(row, col)
                            row_data.append(f"{status_widget.temp_status.text()},{status_widget.humidity_status.text()},{status_widget.pm25_status.text()},{status_widget.noise_status.text()}")
                        else:
                            item = self.table.item(row, col)
                            row_data.append(item.text() if item else '')
                    f.write(','.join(row_data) + '\n')
            InfoBar.success(title='导出成功', content=f'数据已保存至 {file_path}', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self.window())
        except Exception as e:
            InfoBar.error(title='导出失败', content=f'发生错误: {str(e)}', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self.window())

    def update_theme(self, dark_mode):
        self.dark_mode = dark_mode