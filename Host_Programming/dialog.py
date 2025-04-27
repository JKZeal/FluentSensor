import os

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QButtonGroup,
                             QStackedWidget, QGridLayout)
from qfluentwidgets import (HeaderCardWidget, BodyLabel, PrimaryPushButton, RadioButton,
                            CheckBox, InfoBar, InfoBarPosition, TransparentToolButton,
                            FluentIcon, SingleDirectionScrollArea, CardWidget,
                            SpinBox, DoubleSpinBox, MessageBoxBase, ComboBox,
                            SwitchButton, StrongBodyLabel, SubtitleLabel, CaptionLabel)

from alarm import (AlarmRule, AlarmManager, save_rules_to_json,
                   load_rules_from_json, get_project_root)


class AlarmRuleDialog(MessageBoxBase):
    """添加警报规则的对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rule = None

        # 设置按钮文本
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")

        # 初始化音频文件和邮件配置文件列表
        self.sound_files = []
        self.email_files = []
        self.load_asset_files()

        # 初始化界面
        self.setup_ui()

        # 设置对话框大小
        self.widget.setMinimumWidth(400)

    def load_asset_files(self):
        """加载asset目录下的wav和json文件"""
        asset_dir = os.path.join(get_project_root(), "asset")
        if not os.path.exists(asset_dir):
            os.makedirs(asset_dir)

        # 加载wav文件
        self.sound_files = [os.path.join(asset_dir, f) for f in os.listdir(asset_dir)
                            if f.lower().endswith('.wav')]

        # 加载json文件(排除rule.json)
        self.email_files = [os.path.join(asset_dir, f) for f in os.listdir(asset_dir)
                            if f.lower().endswith('.json') and f != "rule.json"]

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

        # 触发条件卡片
        condition_card = HeaderCardWidget(self)
        condition_card.setTitle("触发条件")
        condition_card.setBorderRadius(8)

        # 使用水平布局作为主布局
        condition_layout = QHBoxLayout()
        condition_layout.setSpacing(15)  # 增加组件之间的间距

        # 左侧：条件选择（标签和下拉框在同一行）
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

        # PM2.5输入 (0~1000, 整数)
        self.pm25_input = SpinBox(condition_card)
        self.pm25_input.setRange(0, 1000)
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
        condition_layout.addLayout(threshold_row_layout, 1)  # 阈值输入占比1

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

        # 音频提醒行
        sound_layout = QHBoxLayout()
        self.sound_checkbox = CheckBox("音频提醒", notification_card)
        sound_layout.addWidget(self.sound_checkbox)

        # 音频文件选择框
        self.sound_file_combobox = ComboBox(notification_card)
        self.sound_file_combobox.addItems(
            [os.path.basename(f) for f in self.sound_files] if self.sound_files else ["无可用音频文件"])
        self.sound_file_combobox.setEnabled(len(self.sound_files) > 0)
        self.sound_file_combobox.setMinimumHeight(28)
        sound_layout.addWidget(self.sound_file_combobox)

        # 邮件提醒行
        email_layout = QHBoxLayout()
        self.email_checkbox = CheckBox("邮件提醒", notification_card)
        email_layout.addWidget(self.email_checkbox)

        # 邮件配置选择框
        self.email_file_combobox = ComboBox(notification_card)
        self.email_file_combobox.addItems(
            [os.path.basename(f) for f in self.email_files] if self.email_files else ["无可用邮件配置"])
        self.email_file_combobox.setEnabled(len(self.email_files) > 0)
        self.email_file_combobox.setMinimumHeight(28)
        email_layout.addWidget(self.email_file_combobox)

        # 连接复选框状态变化信号到槽函数
        self.sound_checkbox.stateChanged.connect(
            lambda: self.update_combobox_state(self.sound_checkbox, self.sound_file_combobox))
        self.email_checkbox.stateChanged.connect(
            lambda: self.update_combobox_state(self.email_checkbox, self.email_file_combobox))

        # 初始设置为禁用状态
        self.sound_file_combobox.setEnabled(False)
        self.email_file_combobox.setEnabled(False)

        notification_layout.addLayout(sound_layout)
        notification_layout.addLayout(email_layout)
        notification_card.viewLayout.addLayout(notification_layout)
        self.viewLayout.addWidget(notification_card)

        # 连接确认按钮信号
        self.yesButton.clicked.disconnect()  # 断开原来的连接
        self.yesButton.clicked.connect(self.create_rule)

    def update_combobox_state(self, checkbox, combobox):
        """更新下拉框的启用状态"""
        combobox.setEnabled(checkbox.isChecked() and combobox.count() > 0)

    def create_rule(self):
        """创建规则对象"""
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

        # 获取选择的音频文件和邮件文件
        sound_file = None
        if self.sound_checkbox.isChecked() and self.sound_files:
            absolute_path = self.sound_files[self.sound_file_combobox.currentIndex()]
            # 转换为相对路径
            sound_file = os.path.join("asset", os.path.basename(absolute_path))

        email_file = None
        if self.email_checkbox.isChecked() and self.email_files:
            absolute_path = self.email_files[self.email_file_combobox.currentIndex()]
            # 转换为相对路径
            email_file = os.path.join("asset", os.path.basename(absolute_path))

        self.rule = AlarmRule(
            sensor_type,
            condition_type,
            threshold,
            notification_type,
            sound_file=sound_file,
            email_file=email_file
        )
        self.accept()

    def validate(self):
        """验证输入合法性"""
        notification_types = []
        if self.sound_checkbox.isChecked():
            notification_types.append('sound')
        if self.email_checkbox.isChecked():
            notification_types.append('email')

        if not notification_types:
            return False
        return True


class AlarmRuleItem(CardWidget):
    """报警规则项UI组件"""
    deleteClicked = pyqtSignal(str)  # 使用字符串ID
    switchChanged = pyqtSignal(str, bool)  # 规则ID和开关状态

    def __init__(self, rule, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # 启用/禁用开关
        self.switch_button = SwitchButton(self)
        self.switch_button.setChecked(self.rule.is_active)
        self.switch_button.setOnText("启用")
        self.switch_button.setOffText("禁用")
        self.switch_button.checkedChanged.connect(self.on_switch_changed)
        layout.addWidget(self.switch_button)

        # 中间部分: 规则信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # 顶部部分: 传感器和条件
        rule_title_layout = QHBoxLayout()

        # 传感器图标和名称
        sensor_icons = {
            'temperature': FluentIcon.CALORIES,
            'humidity': FluentIcon.CLOUD,
            'pm25': FluentIcon.LEAF,
            'noise': FluentIcon.SPEAKERS
        }
        sensor_names = {
            'temperature': '温度',
            'humidity': '湿度',
            'pm25': 'PM2.5',
            'noise': '噪声'
        }

        icon_button = TransparentToolButton(sensor_icons.get(self.rule.sensor_type, FluentIcon.RINGER), self)
        icon_button.setIconSize(QSize(20, 20))
        icon_button.setFixedSize(28, 28)
        rule_title_layout.addWidget(icon_button)

        # 传感器名称和条件
        condition_text = f"{sensor_names.get(self.rule.sensor_type, '未知')} {self.rule.condition_type} {self.rule.threshold}"
        units = {
            'temperature': '°C',
            'humidity': '%',
            'pm25': 'μg/m³',
            'noise': 'dB'
        }
        condition_text += units.get(self.rule.sensor_type, '')

        condition_label = StrongBodyLabel(condition_text, self)
        rule_title_layout.addWidget(condition_label)
        rule_title_layout.addStretch(1)

        info_layout.addLayout(rule_title_layout)

        # 底部部分: 通知方式
        notification_layout = QHBoxLayout()
        notification_layout.setSpacing(8)

        notification_types = self.rule.notification_type.split(',')

        # 通知方式图标
        if 'sound' in notification_types:
            sound_icon = TransparentToolButton(FluentIcon.MUSIC, self)
            sound_icon.setToolTip("音频提醒")
            sound_icon.setIconSize(QSize(14, 14))
            sound_icon.setFixedSize(20, 20)
            notification_layout.addWidget(sound_icon)

            if self.rule.sound_file:
                sound_file = os.path.basename(self.rule.sound_file)
                sound_label = CaptionLabel(sound_file, self)
                notification_layout.addWidget(sound_label)

        if 'email' in notification_types:
            email_icon = TransparentToolButton(FluentIcon.MAIL, self)
            email_icon.setToolTip("邮件提醒")
            email_icon.setIconSize(QSize(14, 14))
            email_icon.setFixedSize(20, 20)
            notification_layout.addWidget(email_icon)

            if self.rule.email_file:
                email_file = os.path.basename(self.rule.email_file)
                email_label = CaptionLabel(email_file, self)
                notification_layout.addWidget(email_label)

        notification_layout.addStretch(1)
        info_layout.addLayout(notification_layout)

        layout.addLayout(info_layout, 1)  # 信息部分占据大部分空间

        # 删除按钮
        self.delete_button = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_button.setIconSize(QSize(16, 16))
        self.delete_button.setFixedSize(32, 32)
        self.delete_button.setToolTip("删除规则")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        layout.addWidget(self.delete_button)

        # 设置样式
        self.setAttribute(Qt.WA_StyledBackground)
        if not self.rule.is_active:
            self.setStyleSheet("AlarmRuleItem { opacity: 0.7; }")

    def on_delete_clicked(self):
        # 发出删除信号，携带当前规则的 ID
        self.deleteClicked.emit(self.rule.id)

    def on_switch_changed(self, checked):
        # 更新规则状态
        self.rule.is_active = checked
        # 根据开关状态更新卡片样式
        if checked:
            self.setStyleSheet("AlarmRuleItem { opacity: 1.0; }")
        else:
            self.setStyleSheet("AlarmRuleItem { opacity: 0.7; }")
        # 发出信号
        self.switchChanged.emit(self.rule.id, checked)


class AlarmWidget(QWidget):
    """警报管理界面"""
    alarm_rules_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alarmWidget")
        self.alarm_rules = []
        self.alarm_manager = AlarmManager()
        self.setup_ui()

        # 加载保存的规则
        self.load_saved_rules()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # 标题
        self.title_label = BodyLabel("警报规则", self)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 500; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        # 警报规则卡片
        self.rules_card = HeaderCardWidget(self)
        self.rules_card.setTitle("已启用的规则")
        self.rules_card.setBorderRadius(8)
        self.rules_card.setFixedHeight(420)

        # 没有规则时显示的提示
        self.empty_hint = BodyLabel("暂无警报规则，点击下方按钮添加", self.rules_card)
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color: var(--text-color-secondary); padding: 20px;")
        self.rules_card.viewLayout.addWidget(self.empty_hint)

        # 规则列表容器
        self.rules_container = QWidget(self.rules_card)
        self.rules_layout = QVBoxLayout(self.rules_container)
        self.rules_layout.setContentsMargins(0, 0, 0, 0)
        self.rules_layout.setSpacing(6)

        # 滚动区域
        self.scroll_area = SingleDirectionScrollArea(self.rules_card)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea {background: transparent; border: none;}"
            "QScrollArea > QWidget > QWidget {background: transparent;}"
            "QScrollArea > QWidget {background: transparent;}")
        self.scroll_area.setWidget(self.rules_container)
        self.rules_card.viewLayout.addWidget(self.scroll_area)
        self.rules_container.hide()
        layout.addWidget(self.rules_card)

        # 按钮布局
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
        """显示添加规则对话框"""
        dialog = AlarmRuleDialog(self.window())
        if dialog.exec():
            if dialog.rule:
                self.add_rule(dialog.rule)

    def add_rule(self, rule, save_to_file=True):
        """添加一条警报规则"""
        self.alarm_rules.append(rule)
        rule_item = AlarmRuleItem(rule)
        rule_item.deleteClicked.connect(self.remove_rule)
        rule_item.switchChanged.connect(self.toggle_rule_active)
        self.rules_layout.addWidget(rule_item)

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

    def toggle_rule_active(self, rule_id, is_active):
        """启用/禁用规则"""
        for rule in self.alarm_rules:
            if rule.id == rule_id:
                rule.is_active = is_active
                # 如果规则正在触发警报且被禁用，停止警报
                if not is_active and rule.is_triggered:
                    self.alarm_manager.recover_alarm(rule)
                break

        # 保存规则到文件
        save_rules_to_json(self.alarm_rules)

        # 通知规则已更改
        self.alarm_rules_changed.emit(self.alarm_rules)

    def remove_rule(self, rule_id):
        """删除指定ID的警报规则"""
        # 查找要删除的规则
        to_remove_index = -1
        for i, rule in enumerate(self.alarm_rules):
            if rule.id == rule_id:
                to_remove_index = i
                break

        if to_remove_index >= 0:
            # 从规则列表中移除规则
            removed_rule = self.alarm_rules.pop(to_remove_index)

            # 如果规则正在触发警报，停止警报
            if removed_rule.is_triggered:
                self.alarm_manager.recover_alarm(removed_rule)

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
            InfoBar.warning(
                title='删除失败',
                content='找不到指定的警报规则',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def check_all_rules(self, data):
        """检查所有规则是否触发"""
        if not data:
            return

        # 检查每个规则是否触发
        for rule in self.alarm_rules:
            if not rule.is_active:
                continue

            sensor_value = data.get(rule.sensor_type)
            if sensor_value is not None:
                self.alarm_manager.check_rule(rule, sensor_value)

    def stop_all_alarms(self):
        """停止所有活动的警报"""
        if hasattr(self, 'alarm_manager'):
            self.alarm_manager.stop_all_alarms()