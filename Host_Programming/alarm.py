import json
import os
import smtplib
import time
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from PyQt5.QtCore import QObject, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent


def get_project_root():
    """获取项目根目录路径"""
    return os.path.dirname(os.path.abspath(__file__))


# 定义JSON文件路径
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(CONFIG_DIR, "rule.json")
ASSET_DIR = os.path.join(CONFIG_DIR, "asset")

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
    """警报规则类"""

    def __init__(self, sensor_type, condition_type, threshold, notification_type, rule_id=None, sound_file=None,
                 email_file=None):
        # 使用字符串形式的 UUID 作为 ID，确保序列化和反序列化时保持一致
        self.id = rule_id if rule_id is not None else str(uuid.uuid4())
        self.sensor_type = sensor_type
        self.condition_type = condition_type
        self.threshold = threshold
        self.notification_type = notification_type
        self.is_active = True
        self.sound_file = sound_file
        self.email_file = email_file
        self.last_email_time = 0
        self.is_triggered = False
        # 添加标记表示是否已发送恢复通知
        self.recovery_notified = True  # 初始值为True，避免未触发警报前就发送恢复通知

    def to_dict(self):
        """将规则转换为字典，用于JSON序列化"""
        return {
            'id': self.id,
            'sensor_type': self.sensor_type,
            'condition_type': self.condition_type,
            'threshold': self.threshold,
            'notification_type': self.notification_type,
            'is_active': self.is_active,
            'sound_file': self.sound_file,
            'email_file': self.email_file,
            'last_email_time': self.last_email_time,
            'is_triggered': self.is_triggered,
            'recovery_notified': self.recovery_notified
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建规则对象，用于JSON反序列化"""
        rule = cls(
            data['sensor_type'],
            data['condition_type'],
            data['threshold'],
            data['notification_type'],
            rule_id=data['id'],
            sound_file=data.get('sound_file'),
            email_file=data.get('email_file')
        )
        rule.is_active = data.get('is_active', True)
        rule.last_email_time = data.get('last_email_time', 0)
        rule.is_triggered = data.get('is_triggered', False)
        rule.recovery_notified = data.get('recovery_notified', True)
        return rule

    def check_condition(self, value):
        """检查条件是否满足"""
        if self.condition_type == ">":
            return value > self.threshold
        elif self.condition_type == "<":
            return value < self.threshold
        return False

    def get_description(self):
        """获取规则的描述文本"""
        sensor_names = {'temperature': '温度', 'humidity': '湿度', 'pm25': 'PM2.5', 'noise': '噪声'}
        condition_symbols = {'>': '>', '<': '<'}
        units = {'temperature': '°C', 'humidity': '%', 'pm25': 'μg/m³', 'noise': 'dB'}
        notification_names = {'sound': '音频提醒', 'email': '邮件提醒', 'sound,email': '音频+邮件'}

        # 添加文件名显示
        notification_details = []
        if 'sound' in self.notification_type.split(',') and self.sound_file:
            notification_details.append(f"音频:{os.path.basename(self.sound_file)}")
        if 'email' in self.notification_type.split(',') and self.email_file:
            notification_details.append(f"邮件:{os.path.basename(self.email_file)}")

        notification_info = notification_names[self.notification_type]
        if notification_details:
            notification_info += f" ({', '.join(notification_details)})"

        return f"{sensor_names[self.sensor_type]} {condition_symbols[self.condition_type]} {self.threshold}{units[self.sensor_type]} → {notification_info}"


class AlarmManager(QObject):
    """警报管理器，负责触发警报和处理警报恢复"""

    def __init__(self):
        super().__init__()
        self.active_players = {}  # 记录正在播放的音频 {rule_id: QMediaPlayer对象}
        # 增加邮件冷却时间为300秒(5分钟)
        self.EMAIL_COOLDOWN = 300

    def check_rule(self, rule, current_value):
        """检查规则是否触发"""
        is_triggered = rule.check_condition(current_value)

        # 如果规则状态改变
        if is_triggered != rule.is_triggered:
            rule.is_triggered = is_triggered

            if is_triggered:
                # 规则被触发
                rule.recovery_notified = False  # 重置恢复通知状态
                self.trigger_alarm(rule, current_value)
            else:
                # 规则恢复正常，触发恢复操作
                self.recover_alarm(rule, current_value)

        # 如果规则持续触发，检查邮件是否在冷却时间
        elif is_triggered and 'email' in rule.notification_type.split(','):
            # 检查是否需要重新发送邮件(增加到300秒钟间隔)
            current_time = time.time()
            if current_time - rule.last_email_time > self.EMAIL_COOLDOWN:
                self.send_email_alert(rule, current_value)
                rule.last_email_time = current_time

    def trigger_alarm(self, rule, current_value):
        """触发警报"""
        notification_types = rule.notification_type.split(',')

        if 'sound' in notification_types and rule.sound_file:
            self.play_sound_alert(rule)

        if 'email' in notification_types and rule.email_file:
            self.send_email_alert(rule, current_value)
            rule.last_email_time = time.time()

    def recover_alarm(self, rule, current_value=None):
        """警报恢复

        参数:
            rule: 警报规则
            current_value: 当前传感器值，用于发送恢复通知邮件
        """
        # 停止音频播放
        self.stop_sound_alert(rule)

        # 发送恢复通知邮件（如果已经触发过警报且未发送过恢复通知）
        if current_value is not None and 'email' in rule.notification_type.split(',') and not rule.recovery_notified:
            self.send_recovery_email(rule, current_value)
            rule.recovery_notified = True

    def play_sound_alert(self, rule):
        """播放音频警报，使用QMediaPlayer替代QSound"""
        if not rule.sound_file:
            return

        # 确保之前的声音已停止
        self.stop_sound_alert(rule)

        # 将相对路径转换为绝对路径
        sound_path = os.path.join(get_project_root(), rule.sound_file)

        try:
            # 创建新的QMediaPlayer对象
            player = QMediaPlayer()

            # 设置媒体内容
            url = QUrl.fromLocalFile(sound_path)
            media = QMediaContent(url)
            player.setMedia(media)

            # 设置循环播放
            player.mediaStatusChanged.connect(
                lambda status: player.play() if status == QMediaPlayer.EndOfMedia else None
            )

            # 开始播放
            player.play()

            # 保存播放器引用以便后续停止
            self.active_players[rule.id] = player
            print(f"开始播放音频警报: {rule.sound_file}")

        except Exception as e:
            print(f"播放音频警报失败: {e}")

    def stop_sound_alert(self, rule):
        """停止音频警报"""
        if rule.id in self.active_players:
            try:
                player = self.active_players[rule.id]
                player.stop()
                # 断开之前的信号连接以避免循环播放
                player.mediaStatusChanged.disconnect()
                print(f"停止音频警报: {rule.sound_file}")
            except Exception as e:
                print(f"停止音频警报失败: {e}")
            finally:
                # 从active_players中移除
                del self.active_players[rule.id]

    def send_email_alert(self, rule, current_value):
        """发送邮件警报"""
        if not rule.email_file:
            return

        try:
            # 将相对路径转换为绝对路径
            email_config_path = os.path.join(get_project_root(), rule.email_file)

            # 读取邮件配置
            with open(email_config_path, 'r', encoding='utf-8') as f:
                email_config = json.load(f)

            # 准备邮件内容
            sensor_names = {'temperature': '温度', 'humidity': '湿度', 'pm25': 'PM2.5', 'noise': '噪声'}
            units = {'temperature': '°C', 'humidity': '%', 'pm25': 'μg/m³', 'noise': 'dB'}

            msg = MIMEMultipart()
            msg['From'] = email_config.get('sender_email', 'smart_env_monitor@example.com')
            msg['To'] = email_config.get('receiver_email', '')
            msg['Subject'] = f"环境监测警报: {sensor_names[rule.sensor_type]}异常"

            # 构建邮件正文
            body = email_config.get('alarm_template', '').format(
                sensor_type=sensor_names[rule.sensor_type],
                current_value=f"{current_value}{units[rule.sensor_type]}",
                threshold=f"{rule.threshold}{units[rule.sensor_type]}",
                condition="高于" if rule.condition_type == ">" else "低于",
                time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 发送邮件
            smtp_server = email_config.get('smtp_server', '')
            smtp_port = email_config.get('smtp_port', 587)
            smtp_username = email_config.get('smtp_username', '')
            smtp_password = email_config.get('smtp_password', '')

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)

            print(f"成功发送警报邮件至 {msg['To']}")

        except Exception as e:
            print(f"发送邮件警报失败: {e}")

    def send_recovery_email(self, rule, current_value):
        """发送警报恢复通知邮件"""
        if not rule.email_file:
            return

        try:
            # 将相对路径转换为绝对路径
            email_config_path = os.path.join(get_project_root(), rule.email_file)

            # 读取邮件配置
            with open(email_config_path, 'r', encoding='utf-8') as f:
                email_config = json.load(f)

            # 准备邮件内容
            sensor_names = {'temperature': '温度', 'humidity': '湿度', 'pm25': 'PM2.5', 'noise': '噪声'}
            units = {'temperature': '°C', 'humidity': '%', 'pm25': 'μg/m³', 'noise': 'dB'}

            msg = MIMEMultipart()
            msg['From'] = email_config.get('sender_email', 'smart_env_monitor@example.com')
            msg['To'] = email_config.get('receiver_email', '')
            msg['Subject'] = f"环境监测通知: {sensor_names[rule.sensor_type]}已恢复正常"

            # 使用配置文件中的恢复通知邮件模板
            body = email_config['recovery_template'].format(
                sensor_type=sensor_names[rule.sensor_type],
                current_value=f"{current_value}{units[rule.sensor_type]}",
                threshold=f"{rule.threshold}{units[rule.sensor_type]}",
                condition="不再高于" if rule.condition_type == ">" else "不再低于",
                time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 发送邮件
            smtp_server = email_config.get('smtp_server', '')
            smtp_port = email_config.get('smtp_port', 587)
            smtp_username = email_config.get('smtp_username', '')
            smtp_password = email_config.get('smtp_password', '')

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)

            print(f"成功发送恢复通知邮件至 {msg['To']}")

        except Exception as e:
            print(f"发送恢复通知邮件失败: {e}")

    def stop_all_alarms(self):
        """停止所有活动的警报"""
        # 创建活动播放器的副本，因为在循环内部会修改字典
        player_ids = list(self.active_players.keys())
        for rule_id in player_ids:
            try:
                if rule_id in self.active_players:  # 再次检查，以防在迭代过程中已被删除
                    player = self.active_players[rule_id]
                    player.stop()
                    # 断开信号连接
                    try:
                        player.mediaStatusChanged.disconnect()
                    except Exception:
                        pass
                    del self.active_players[rule_id]
            except Exception as e:
                print(f"停止音频警报失败: {e}")

        # 确保清空活动的播放器字典
        self.active_players.clear()