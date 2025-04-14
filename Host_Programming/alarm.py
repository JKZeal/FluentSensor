import json
import os
import uuid  # 导入 uuid 模块生成唯一 ID
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QDialog, QButtonGroup, QStackedWidget, QGridLayout
from qfluentwidgets import (HeaderCardWidget, BodyLabel, PrimaryPushButton, RadioButton, CheckBox, Slider, InfoBar,
                            InfoBarPosition, TransparentToolButton, FluentIcon, SingleDirectionScrollArea,
                            ElevatedCardWidget, CardWidget, StrongBodyLabel, CaptionLabel, PushButton,
                            Dialog, SpinBox, DoubleSpinBox, MessageBoxBase)
# 定义JSON文件路径
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(CONFIG_DIR, "rule.json")

# 确保配置目录存在
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)


def save_rules_to_json(rules):
    """将规则列表保存到JSON文件"""
    rules_data = [rule.to_dict() for rule in rules]
    try:
        with open(RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存规则时出错: {e}")
        return False


def load_rules_from_json():
    """从JSON文件加载规则列表"""
    if not os.path.exists(RULES_FILE):
        return []

    try:
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
        return [AlarmRule.from_dict(data) for data in rules_data]
    except Exception as e:
        print(f"加载规则时出错: {e}")
        return []


class AlarmRule:
    def __init__(self, sensor_type, condition_type, threshold, notification_type, rule_id=None):
        # 修改: 使用字符串形式的 UUID 作为 ID，确保序列化和反序列化时保持一致
        self.id = rule_id if rule_id is not None else str(uuid.uuid4())
        self.sensor_type = sensor_type
        self.condition_type = condition_type
        self.threshold = threshold
        self.notification_type = notification_type
        self.is_active = True

    def to_dict(self):
        """将规则转换为字典，用于JSON序列化"""
        return {
            'id': self.id,
            'sensor_type': self.sensor_type,
            'condition_type': self.condition_type,
            'threshold': self.threshold,
            'notification_type': self.notification_type,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建规则对象，用于JSON反序列化"""
        rule = cls(
            data['sensor_type'],
            data['condition_type'],
            data['threshold'],
            data['notification_type'],
            rule_id=data['id']
        )
        rule.is_active = data.get('is_active', True)
        return rule

    def check_condition(self, value):
        if self.condition_type == ">=":
            return value >= self.threshold
        elif self.condition_type == "<":
            return value < self.threshold
        return False

    def get_description(self):
        sensor_names = {'temperature': '温度', 'humidity': '湿度', 'pm25': 'PM2.5', 'noise': '噪声'}
        condition_symbols = {'>=': '≥', '<': '<'}
        units = {'temperature': '°C', 'humidity': '%', 'pm25': 'μg/m³', 'noise': 'dB'}
        notification_names = {'sound': '音频提醒', 'email': '邮件提醒', 'sound,email': '音频+邮件'}
        return f"{sensor_names[self.sensor_type]} {condition_symbols[self.condition_type]} {self.threshold}{units[self.sensor_type]} → {notification_names[self.notification_type]}"


class AlarmRuleDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rule = None

        # 设置按钮文本
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")

        # 初始化界面
        self.setup_ui()

        # 设置对话框大小
        self.widget.setMinimumWidth(400)

    def setup_ui(self):
        # 选择指标卡片 - 2行2列布局
        sensor_card = HeaderCardWidget(self)
        sensor_card.setTitle("选择指标")
        sensor_card.setBorderRadius(8)

        sensor_grid = QGridLayout()
        sensor_grid.setSpacing(10)

        self.temperature_radio = RadioButton("温度", sensor_card)
        self.humidity_radio = RadioButton("湿度", sensor_card)
        self.pm25_radio = RadioButton("PM2.5", sensor_card)
        self.noise_radio = RadioButton("噪声", sensor_card)

        self.temperature_radio.setChecked(True)

        self.sensor_group = QButtonGroup(self)
        self.sensor_group.addButton(self.temperature_radio, 0)
        self.sensor_group.addButton(self.humidity_radio, 1)
        self.sensor_group.addButton(self.pm25_radio, 2)
        self.sensor_group.addButton(self.noise_radio, 3)

        sensor_grid.addWidget(self.temperature_radio, 0, 0)
        sensor_grid.addWidget(self.humidity_radio, 0, 1)
        sensor_grid.addWidget(self.pm25_radio, 1, 0)
        sensor_grid.addWidget(self.noise_radio, 1, 1)

        sensor_card.viewLayout.addLayout(sensor_grid)
        self.viewLayout.addWidget(sensor_card)

        # 触发条件卡片 - 改为1行2列布局，使用下拉框
        condition_card = HeaderCardWidget(self)
        condition_card.setTitle("触发条件")
        condition_card.setBorderRadius(8)

        # 使用水平布局作为主布局
        condition_layout = QHBoxLayout()
        condition_layout.setSpacing(15)  # 增加组件之间的间距

        # 左侧：条件选择（标签和下拉框在同一行）
        from qfluentwidgets import ComboBox
        condition_row_layout = QHBoxLayout()
        condition_label = BodyLabel("条件:", condition_card)
        self.condition_combobox = ComboBox(condition_card)
        self.condition_combobox.addItems([" 大于 ", " 小于 "])
        self.condition_combobox.setCurrentIndex(0)

        # 将标签和下拉框放在同一行
        condition_row_layout.addWidget(condition_label)
        condition_row_layout.addWidget(self.condition_combobox, 1)  # 下拉框可以伸展

        # 右侧：阈值输入（标签和输入框在同一行）
        threshold_row_layout = QHBoxLayout()
        threshold_label = BodyLabel("阈值:", condition_card)
        self.threshold_stack = QStackedWidget(condition_card)

        # 温度输入 (-20~+60, 小数点后1位)
        self.temp_input = DoubleSpinBox(condition_card)
        self.temp_input.setRange(-20.0, 60.0)
        self.temp_input.setSingleStep(0.1)
        self.temp_input.setDecimals(1)
        self.temp_input.setValue(30.0)
        self.temp_input.setSuffix(" °C")

        # 湿度输入 (0.0~100.0, 小数点后1位)
        self.humidity_input = DoubleSpinBox(condition_card)
        self.humidity_input.setRange(0.0, 100.0)
        self.humidity_input.setSingleStep(0.1)
        self.humidity_input.setDecimals(1)
        self.humidity_input.setValue(60.0)
        self.humidity_input.setSuffix(" %")

        # PM2.5输入 (0~999, 整数)
        self.pm25_input = SpinBox(condition_card)
        self.pm25_input.setRange(0, 999)
        self.pm25_input.setSingleStep(1)
        self.pm25_input.setValue(75)
        self.pm25_input.setSuffix(" μg/m³")

        # 噪声输入 (0~120, 整数)
        self.noise_input = SpinBox(condition_card)
        self.noise_input.setRange(0, 120)
        self.noise_input.setSingleStep(1)
        self.noise_input.setValue(60)
        self.noise_input.setSuffix(" dB")

        # 添加所有输入控件到栈控件
        self.threshold_stack.addWidget(self.temp_input)
        self.threshold_stack.addWidget(self.humidity_input)
        self.threshold_stack.addWidget(self.pm25_input)
        self.threshold_stack.addWidget(self.noise_input)

        # 初始显示温度输入
        self.threshold_stack.setCurrentIndex(0)

        # 将标签和阈值输入放在同一行
        threshold_row_layout.addWidget(threshold_label)
        threshold_row_layout.addWidget(self.threshold_stack, 1)  # 输入框可以伸展

        # 将两行添加到主布局
        condition_layout.addLayout(condition_row_layout, 1)  # 条件选择占比1
        condition_layout.addLayout(threshold_row_layout, 1)  # 阈值输入占比2

        # 连接传感器选择信号
        self.temperature_radio.clicked.connect(lambda: self.threshold_stack.setCurrentIndex(0))
        self.humidity_radio.clicked.connect(lambda: self.threshold_stack.setCurrentIndex(1))
        self.pm25_radio.clicked.connect(lambda: self.threshold_stack.setCurrentIndex(2))
        self.noise_radio.clicked.connect(lambda: self.threshold_stack.setCurrentIndex(3))

        condition_card.viewLayout.addLayout(condition_layout)
        self.viewLayout.addWidget(condition_card)

        # 通知方式卡片
        notification_card = HeaderCardWidget(self)
        notification_card.setTitle("通知方式")
        notification_card.setBorderRadius(8)

        notification_layout = QVBoxLayout()
        self.sound_checkbox = CheckBox("音频提醒", notification_card)
        self.email_checkbox = CheckBox("邮件提醒", notification_card)
        self.sound_checkbox.setChecked(False)
        self.email_checkbox.setChecked(False)

        notification_layout.addWidget(self.sound_checkbox)
        notification_layout.addWidget(self.email_checkbox)
        notification_card.viewLayout.addLayout(notification_layout)
        self.viewLayout.addWidget(notification_card)

        # 连接确认按钮信号
        self.yesButton.clicked.disconnect()  # 断开原来的连接
        self.yesButton.clicked.connect(self.create_rule)

    def create_rule(self):
        sensor_types = ['temperature', 'humidity', 'pm25', 'noise']
        sensor_type = sensor_types[self.sensor_group.checkedId()]

        # 从下拉框获取条件类型
        condition_type = ">" if self.condition_combobox.currentIndex() == 0 else "<"

        # 根据当前选择的传感器类型获取阈值
        current_index = self.threshold_stack.currentIndex()
        if current_index == 0:
            threshold = self.temp_input.value()
        elif current_index == 1:
            threshold = self.humidity_input.value()
        elif current_index == 2:
            threshold = self.pm25_input.value()
        else:
            threshold = self.noise_input.value()

        notification_types = []
        if self.sound_checkbox.isChecked():
            notification_types.append('sound')
        if self.email_checkbox.isChecked():
            notification_types.append('email')

        notification_type = ','.join(notification_types)

        if not notification_types:
            InfoBar.error(
                title='错误',
                content="至少需要选择一种通知方式",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        self.rule = AlarmRule(sensor_type, condition_type, threshold, notification_type)
        self.accept()

    def validate(self):
        # 验证输入合法性
        notification_types = []
        if self.sound_checkbox.isChecked():
            notification_types.append('sound')
        if self.email_checkbox.isChecked():
            notification_types.append('email')

        if not notification_types:
            return False
        return True

    def add_rule(self):
        # 创建规则并返回
        if self.validate():
            sensor_types = ['temperature', 'humidity', 'pm25', 'noise']
            sensor_type = sensor_types[self.sensor_group.checkedId()]
            condition_type = ">=" if self.condition_combobox.currentIndex() == 0 else "<"

            # 根据当前选择的传感器类型获取阈值
            current_index = self.threshold_stack.currentIndex()
            if current_index == 0:
                threshold = self.temp_input.value()
            elif current_index == 1:
                threshold = self.humidity_input.value()
            elif current_index == 2:
                threshold = self.pm25_input.value()
            else:
                threshold = self.noise_input.value()

            notification_types = []
            if self.sound_checkbox.isChecked():
                notification_types.append('sound')
            if self.email_checkbox.isChecked():
                notification_types.append('email')

            notification_type = ','.join(notification_types)

            self.rule = AlarmRule(sensor_type, condition_type, threshold, notification_type)
            return self.rule
        return None


class AlarmRuleItem(CardWidget):
    deleteClicked = pyqtSignal(str)  # 修改: 使用字符串ID

    def __init__(self, rule, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.description_label = BodyLabel(self.rule.get_description(), self)
        layout.addWidget(self.description_label, 1)
        self.delete_button = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_button.setFixedSize(32, 32)
        self.delete_button.setIconSize(QSize(16, 16))
        self.delete_button.clicked.connect(self.on_delete_clicked)
        layout.addWidget(self.delete_button)

    def on_delete_clicked(self):
        # 发出删除信号，携带当前规则的 ID
        self.deleteClicked.emit(self.rule.id)
        print(f"发出删除信号，规则ID: {self.rule.id}")  # 调试输出


class AlarmWidget(QWidget):
    alarm_rules_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alarmWidget")
        self.alarm_rules = []
        self.setup_ui()

        # 加载保存的规则
        self.load_saved_rules()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.title_label = BodyLabel("警报规则", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        self.rules_card = HeaderCardWidget(self)
        self.rules_card.setTitle("已启用的规则")
        self.rules_card.setBorderRadius(8)
        self.rules_card.setFixedHeight(320)
        self.empty_hint = BodyLabel("暂无警报规则，点击下方按钮添加", self.rules_card)
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color: var(--text-color-secondary); padding: 20px;")
        self.rules_card.viewLayout.addWidget(self.empty_hint)
        self.rules_container = QWidget(self.rules_card)
        self.rules_layout = QVBoxLayout(self.rules_container)
        self.rules_layout.setContentsMargins(0, 0, 0, 0)
        self.rules_layout.setSpacing(8)
        self.scroll_area = SingleDirectionScrollArea(self.rules_card)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea {background: transparent; border: none;} QScrollArea > QWidget > QWidget {background: transparent;} QScrollArea > QWidget {background: transparent;}")
        self.scroll_area.setWidget(self.rules_container)
        self.rules_card.viewLayout.addWidget(self.scroll_area)
        self.rules_container.hide()
        layout.addWidget(self.rules_card)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.add_rule_button = PrimaryPushButton("添加规则", self)
        self.add_rule_button.setIcon(FluentIcon.ADD)
        self.add_rule_button.clicked.connect(self.show_add_rule_dialog)
        button_layout.addWidget(self.add_rule_button)
        layout.addLayout(button_layout)
        layout.addStretch()

    def load_saved_rules(self):
        """加载已保存的规则"""
        rules = load_rules_from_json()
        for rule in rules:
            self.add_rule(rule, save_to_file=False)  # 避免循环保存

        # 如果有规则，更新UI状态
        if self.alarm_rules:
            self.empty_hint.hide()
            self.rules_container.show()

    def show_add_rule_dialog(self):
        dialog = AlarmRuleDialog(self.window())
        if dialog.exec():
            if dialog.rule:
                self.add_rule(dialog.rule)

    def add_rule(self, rule, save_to_file=True):
        """添加一条警报规则"""
        self.alarm_rules.append(rule)
        rule_item = AlarmRuleItem(rule)
        rule_item.deleteClicked.connect(self.remove_rule)
        self.rules_layout.addWidget(rule_item)

        # 调试输出
        print(f"添加规则，ID: {rule.id}")

        if len(self.alarm_rules) == 1:
            self.empty_hint.hide()
            self.rules_container.show()

        # 发出规则变更信号
        self.alarm_rules_changed.emit(self.alarm_rules)

        # 保存规则到文件
        if save_to_file:
            save_rules_to_json(self.alarm_rules)
            InfoBar.success(
                title='添加成功',
                content='警报规则已成功添加并保存',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def remove_rule(self, rule_id):
        """删除指定ID的警报规则"""
        # 调试输出
        print(f"尝试删除规则，ID: {rule_id}")
        print(f"当前规则列表: {[rule.id for rule in self.alarm_rules]}")

        # 查找要删除的规则
        to_remove_index = -1
        for i, rule in enumerate(self.alarm_rules):
            if rule.id == rule_id:
                to_remove_index = i
                break

        if to_remove_index >= 0:
            # 从规则列表中移除规则
            removed_rule = self.alarm_rules.pop(to_remove_index)
            print(f"成功找到并移除规则，ID: {removed_rule.id}")

            # 找到并删除对应的UI项
            for i in range(self.rules_layout.count()):
                item = self.rules_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, AlarmRuleItem) and widget.rule.id == rule_id:
                        # 从布局中移除并删除控件
                        self.rules_layout.removeWidget(widget)
                        widget.setParent(None)
                        widget.deleteLater()
                        print(f"成功移除UI项，对应规则ID: {rule_id}")
                        break

            # 如果没有规则了，显示空提示
            if not self.alarm_rules:
                self.empty_hint.show()
                self.rules_container.hide()

            # 保存更新后的规则列表
            save_rules_to_json(self.alarm_rules)

            # 通知规则已更改
            self.alarm_rules_changed.emit(self.alarm_rules)

            # 显示成功提示
            InfoBar.success(
                title='删除成功',
                content='警报规则已成功删除',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        else:
            print(f"没有找到ID为 {rule_id} 的规则")
            InfoBar.warning(
                title='删除失败',
                content='找不到指定的警报规则',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )


class AlarmNotificationCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("警报通知")
        self.setBorderRadius(8)
        self.setMaximumHeight(250)
        self.alarm_layout = QVBoxLayout()
        self.viewLayout.addLayout(self.alarm_layout)
        self.no_alarm_label = BodyLabel("无警报", self)
        self.no_alarm_label.setAlignment(Qt.AlignCenter)
        self.alarm_layout.addWidget(self.no_alarm_label)
        self.scroll_area = SingleDirectionScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(
            "QScrollArea {background: transparent; border: none;} QScrollArea > QWidget > QWidget {background: transparent;} QScrollArea > QWidget {background: transparent;}")
        self.alarm_container = QWidget()
        self.alarm_container_layout = QVBoxLayout(self.alarm_container)
        self.alarm_container_layout.setContentsMargins(0, 0, 0, 0)
        self.alarm_container_layout.setSpacing(8)
        self.scroll_area.setWidget(self.alarm_container)
        self.alarm_layout.addWidget(self.scroll_area)
        self.scroll_area.hide()

    def show_alarm(self, rule, value):
        self.no_alarm_label.hide()
        self.scroll_area.show()
        alarm_item = ElevatedCardWidget()
        alarm_item.setBorderRadius(6)
        alarm_color = "#e11d48"
        alarm_item.setStyleSheet(f"ElevatedCardWidget {{border-left: 4px solid {alarm_color};}}")
        alarm_layout = QVBoxLayout(alarm_item)
        alarm_layout.setContentsMargins(12, 10, 12, 10)
        alarm_layout.setSpacing(4)
        sensor_names = {'temperature': '温度警报', 'humidity': '湿度警报', 'pm25': 'PM2.5警报', 'noise': '噪声警报'}
        alarm_title = StrongBodyLabel(sensor_names[rule.sensor_type], alarm_item)
        alarm_title.setStyleSheet("font-weight: bold; color: var(--text-color);")
        alarm_layout.addWidget(alarm_title)
        units = {'temperature': '°C', 'humidity': '%', 'pm25': 'μg/m³', 'noise': 'dB'}
        condition_symbols = {'>=': '≥', '<': '<'}
        alarm_detail = BodyLabel(
            f"当前值: {value}{units[rule.sensor_type]} {condition_symbols[rule.condition_type]} {rule.threshold}{units[rule.sensor_type]}",
            alarm_item)
        alarm_detail.setStyleSheet("color: var(--text-color-secondary);")
        alarm_layout.addWidget(alarm_detail)
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = CaptionLabel(f"触发时间: {timestamp}", alarm_item)
        time_label.setStyleSheet("color: var(--text-color-tertiary); font-size: 11px;")
        alarm_layout.addWidget(time_label)
        self.alarm_container_layout.addWidget(alarm_item)

    def clear_alarms(self):
        while self.alarm_container_layout.count():
            item = self.alarm_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.no_alarm_label.show()
        self.scroll_area.hide()