
import flet as ft
import flet_audio
import json
import os
import time
import random
import requests
import threading
from datetime import datetime, timedelta

# ==========================================
# 🔔 跨平台闹钟/通知模块
# ==========================================

# 检测平台
PLATFORM = "unknown"
try:
    from android import mActivity

    PLATFORM = "android"
    print("✅ 检测到 Android 平台")
except:
    pass

if PLATFORM != "android":
    try:
        import platform

        PLATFORM = platform.system().lower()
    except:
        pass

# Android 专用模块
if PLATFORM == "android":
    try:
        from jnius import autoclass, cast

        # Android 类
        Intent = autoclass('android.content.Intent')
        AlarmClock = autoclass('android.provider.AlarmClock')
        Uri = autoclass('android.net.Uri')
        Context = autoclass('android.content.Context')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        NotificationBuilder = autoclass('android.app.Notification$Builder')
        NotificationManager = autoclass('android.app.NotificationManager')
        NotificationChannel = autoclass('android.app.NotificationChannel')
        Build = autoclass('android.os.Build')
        PendingIntent = autoclass('android.app.PendingIntent')
        RingtoneManager = autoclass('android.media.RingtoneManager')
        AudioManager = autoclass('android.media.AudioManager')
        MediaPlayer = autoclass('android.media.MediaPlayer')
        Vibrator = autoclass('android.os.Vibrator')
        PowerManager = autoclass('android.os.PowerManager')

        ANDROID_NATIVE = True
        print("✅ Android 原生模块加载成功")
    except Exception as e:
        ANDROID_NATIVE = False
        print(f"⚠️ Android 原生模块加载失败: {e}")
else:
    ANDROID_NATIVE = False

# Plyer 备用
try:
    from plyer import notification, vibrator

    PLYER_AVAILABLE = True
except:
    PLYER_AVAILABLE = False


class AlarmHelper:
    """跨平台闹钟助手 - 解决后台提醒问题"""

    _ringtone = None
    _vibrator = None
    _wake_lock = None

    @classmethod
    def init(cls):
        """初始化"""
        if ANDROID_NATIVE:
            try:
                context = PythonActivity.mActivity
                # 获取震动器
                cls._vibrator = context.getSystemService(Context.VIBRATOR_SERVICE)

                # 获取 WakeLock（保持 CPU 唤醒）
                pm = context.getSystemService(Context.POWER_SERVICE)
                cls._wake_lock = pm.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK,
                    "CatFocus::AlarmWakeLock"
                )

                # 创建通知渠道 (Android 8.0+)
                if Build.VERSION.SDK_INT >= 26:
                    nm = context.getSystemService(Context.NOTIFICATION_SERVICE)
                    channel = NotificationChannel(
                        "cat_alarm",
                        "猫猫闹钟",
                        NotificationManager.IMPORTANCE_HIGH
                    )
                    channel.enableVibration(True)
                    channel.setVibrationPattern([0, 500, 200, 500, 200, 500])
                    nm.createNotificationChannel(channel)

                print("✅ AlarmHelper 初始化成功")
            except Exception as e:
                print(f"⚠️ AlarmHelper 初始化失败: {e}")

    @classmethod
    def set_system_alarm(cls, minutes, label="专注完成"):
        """
        设置系统闹钟（最可靠的方式！）
        即使 App 被杀死，系统闹钟也会响
        """
        if not ANDROID_NATIVE:
            print("⚠️ 非 Android 平台，无法设置系统闹钟")
            return False

        try:
            context = PythonActivity.mActivity

            # 计算闹钟时间
            now = datetime.now()
            alarm_time = now + timedelta(minutes=minutes)
            hour = alarm_time.hour
            minute = alarm_time.minute

            # 创建设置闹钟的 Intent
            intent = Intent(AlarmClock.ACTION_SET_ALARM)
            intent.putExtra(AlarmClock.EXTRA_HOUR, hour)
            intent.putExtra(AlarmClock.EXTRA_MINUTES, minute)
            intent.putExtra(AlarmClock.EXTRA_MESSAGE, label)
            intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True)  # 不显示闹钟界面
            intent.putExtra(AlarmClock.EXTRA_VIBRATE, True)

            # 启动系统闹钟
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)

            print(f"✅ 系统闹钟已设置: {hour}:{minute:02d} - {label}")
            return True

        except Exception as e:
            print(f"❌ 设置系统闹钟失败: {e}")
            return False

    @classmethod
    def set_timer(cls, seconds, label="计时完成"):
        """
        设置系统计时器（倒计时）
        """
        if not ANDROID_NATIVE:
            return False

        try:
            context = PythonActivity.mActivity

            intent = Intent(AlarmClock.ACTION_SET_TIMER)
            intent.putExtra(AlarmClock.EXTRA_LENGTH, seconds)
            intent.putExtra(AlarmClock.EXTRA_MESSAGE, label)
            intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True)

            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)

            print(f"✅ 系统计时器已设置: {seconds}秒 - {label}")
            return True

        except Exception as e:
            print(f"❌ 设置系统计时器失败: {e}")
            return False

    @classmethod
    def play_alarm_sound(cls):
        """播放系统闹钟铃声"""
        if ANDROID_NATIVE:
            try:
                context = PythonActivity.mActivity

                # 获取默认闹钟铃声
                alarm_uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)

                # 创建 MediaPlayer
                cls._ringtone = MediaPlayer()
                cls._ringtone.setDataSource(context, alarm_uri)
                cls._ringtone.setAudioStreamType(AudioManager.STREAM_ALARM)
                cls._ringtone.setLooping(True)
                cls._ringtone.prepare()
                cls._ringtone.start()

                print("✅ 闹钟铃声开始播放")
                return True
            except Exception as e:
                print(f"❌ 播放闹钟铃声失败: {e}")
        return False

    @classmethod
    def stop_alarm_sound(cls):
        """停止闹钟铃声"""
        if cls._ringtone:
            try:
                cls._ringtone.stop()
                cls._ringtone.release()
                cls._ringtone = None
            except:
                pass

    @classmethod
    def vibrate(cls, pattern=None):
        """震动"""
        if pattern is None:
            pattern = [0, 500, 200, 500, 200, 500]  # 默认模式

        if ANDROID_NATIVE and cls._vibrator:
            try:
                cls._vibrator.vibrate(pattern, -1)  # -1 表示不循环
                return True
            except:
                pass

        if PLYER_AVAILABLE:
            try:
                vibrator.vibrate(2)
                return True
            except:
                pass

        return False

    @classmethod
    def send_notification(cls, title, message):
        """发送高优先级通知"""
        if ANDROID_NATIVE:
            try:
                context = PythonActivity.mActivity
                nm = context.getSystemService(Context.NOTIFICATION_SERVICE)

                # 点击通知打开应用
                intent = context.getPackageManager().getLaunchIntentForPackage(
                    context.getPackageName()
                )
                pending = PendingIntent.getActivity(
                    context, 0, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                )

                # 构建通知
                if Build.VERSION.SDK_INT >= 26:
                    builder = NotificationBuilder(context, "cat_alarm")
                else:
                    builder = NotificationBuilder(context)

                builder.setSmallIcon(context.getApplicationInfo().icon)
                builder.setContentTitle(title)
                builder.setContentText(message)
                builder.setContentIntent(pending)
                builder.setAutoCancel(True)
                builder.setPriority(NotificationBuilder.PRIORITY_MAX)

                # 发送通知
                nm.notify(1001, builder.build())
                print(f"✅ 通知已发送: {title}")
                return True

            except Exception as e:
                print(f"❌ 发送通知失败: {e}")

        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="猫猫专注",
                    timeout=30
                )
                return True
            except:
                pass

        return False

    @classmethod
    def acquire_wake_lock(cls):
        """获取 WakeLock，防止 CPU 休眠"""
        if cls._wake_lock:
            try:
                cls._wake_lock.acquire(30 * 60 * 1000)  # 30分钟
                print("✅ WakeLock 已获取")
            except:
                pass

    @classmethod
    def release_wake_lock(cls):
        """释放 WakeLock"""
        if cls._wake_lock:
            try:
                if cls._wake_lock.isHeld():
                    cls._wake_lock.release()
                    print("✅ WakeLock 已释放")
            except:
                pass


# ==========================================
# 数据逻辑层
# ==========================================
class StudyLogic:
    def __init__(self):
        self.data_file = 'station_data.json'
        self.data = {
            "target_name": "上岸",
            "target_date": "2026-12-21",
            "city": "郑州",
            "focus_min": 25,
            "break_min": 5,
            "tomatoes": 0,
            "tasks": [],
            "daily_stats": {},
            "countdowns": [],
            "history": [],
            "last_checkin": "",
            "streak_days": 0,
            "use_system_alarm": True  # 新增：是否使用系统闹钟
        }
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data.update(json.load(f))
            except:
                pass

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def get_main_days_left(self):
        return self.calculate_days(self.data.get("target_date", "2025-12-20"))

    def calculate_days(self, date_str):
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
            return (target - datetime.now().date()).days
        except:
            return 0

    def update_settings(self, name, date, city, focus_min, break_min):
        self.data["target_name"] = name
        self.data["target_date"] = date
        self.data["city"] = city
        self.data["focus_min"] = int(focus_min) if str(focus_min).isdigit() else 25
        self.data["break_min"] = int(break_min) if str(break_min).isdigit() else 5
        self.save_data()

    def add_task(self, text, priority="green"):
        if text:
            self.data["tasks"].append({
                "text": text, "priority": priority,
                "created": datetime.now().strftime("%Y-%m-%d")
            })
            self.save_data()

    def remove_task(self, index):
        if 0 <= index < len(self.data["tasks"]):
            task = self.data["tasks"].pop(index)
            content = task["text"] if isinstance(task, dict) else task
            self.data["history"].append(f"[{datetime.now().strftime('%H:%M')}] ✅ 完成: {content}")
            self.save_data()

    def increment_tomato(self):
        self.data["tomatoes"] += 1
        today = datetime.now().strftime("%Y-%m-%d")
        self.data.setdefault("daily_stats", {})[today] = self.data["daily_stats"].get(today, 0) + 1
        self.data["history"].append(f"[{datetime.now().strftime('%H:%M')}] 🍅 捕获番茄")
        self.save_data()
        return self.data["tomatoes"]

    def check_in(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data.get("last_checkin") == today:
            return False, "今天已经签到啦！"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.data["streak_days"] = self.data.get("streak_days", 0) + 1 if self.data.get(
            "last_checkin") == yesterday else 1
        self.data["last_checkin"] = today
        self.data["history"].append(f"[{datetime.now().strftime('%H:%M')}] 🐾 签到")
        self.save_data()
        return True, f"签到成功！连续 {self.data['streak_days']} 天"

    def is_checked_in(self):
        return self.data.get("last_checkin") == datetime.now().strftime("%Y-%m-%d")

    def get_random_quote(self):
        quotes = [
            "既然上了贼船\n就做个快乐的海盗猫",
            "保持好奇心\n是猫咪长寿的秘诀",
            "没有什么烦恼\n是一个罐头解决不了的",
            "只要步履不停\n小鱼干终将抵达",
        ]
        return random.choice(quotes)

    def fetch_weather(self):
        city = self.data.get("city", "郑州")
        try:
            res = requests.get(
                f"https://wttr.in/{city}?format=%C+%t&lang=zh",
                timeout=10, headers={"User-Agent": "Mozilla/5.0"}
            )
            if res.status_code == 200:
                return f"{city} {res.text.strip()}"
        except:
            pass
        return f"{city}: 获取失败"


# ==========================================
# 界面层
# ==========================================
def main(page: ft.Page):
    page.title = "猫猫专注助手"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 390
    page.window_height = 844

    # 初始化闹钟助手
    AlarmHelper.init()

    THEME = {
        "bg": "#FFCCCC", "fg": "#D24D57", "comp_bg": "#FFF0E6",
        "green": "#4CAF50", "white": "#FFFFFF", "red": "#FF5252",
        "orange": "#FF9800", "ring_bg": "#FFEEEE"
    }
    page.bgcolor = THEME["bg"]
    page.padding = 0
    page.keep_screen_on = True

    logic = StudyLogic()

    # 状态变量
    timer_running = False
    is_break_mode = False
    end_timestamp = 0
    total_duration = logic.data["focus_min"] * 60
    bgm_enabled = True
    use_system_alarm = logic.data.get("use_system_alarm", True)

    emojis = {
        "idle": ["( =ω=)..zzZ", "(=^･ω･^=)", "ฅ(ﾐ・ﻌ・ﾐ)ฅ"],
        "work": ["(ง •̀_•́)ง", "(=`ω´=)", "φ(．．;)"],
        "break": ["☕(・ω・)", "(=^ ◡ ^=)"],
        "happy": ["(≧◡≦) ♡", "o(>ω<)o"],
    }

    # 音频
    audio_alarm = flet_audio.Audio(src="assets/alarm.mp3", autoplay=False)
    audio_bg = flet_audio.Audio(src="assets/kanong.mp3", autoplay=False, release_mode="loop")
    page.overlay.extend([audio_alarm, audio_bg])

    # ==========================================
    # 🔔 核心：完成周期
    # ==========================================
    def finish_cycle():
        nonlocal timer_running, is_break_mode, total_duration, end_timestamp

        print("🔔 计时完成！")
        timer_running = False
        end_timestamp = 0

        # 停止背景音乐
        try:
            audio_bg.pause()
        except:
            pass

        # 释放 WakeLock
        AlarmHelper.release_wake_lock()

        # 🔔 播放闹钟 + 震动 + 通知
        AlarmHelper.play_alarm_sound()
        AlarmHelper.vibrate()

        if not is_break_mode:
            logic.increment_tomato()
            txt_tomato_stats.value = f"今日: {logic.data['tomatoes']} 🐟"
            AlarmHelper.send_notification("🎉 专注完成！", "喵！该休息一下啦~")

            is_break_mode = True
            next_min = logic.data["break_min"]
            txt_timer_title.value = f"☕ 休息 {next_min} 分钟"
            txt_timer.color = THEME["green"]
            ring_timer.color = THEME["green"]
            btn_start.text = "开始休息"
            btn_start.bgcolor = THEME["green"]
            btn_skip.visible = True
            txt_cat.value = random.choice(emojis["break"])
        else:
            AlarmHelper.send_notification("☀️ 休息结束！", "继续加油喵~")

            is_break_mode = False
            next_min = logic.data["focus_min"]
            txt_timer_title.value = "准备专注"
            txt_timer.color = THEME["fg"]
            ring_timer.color = THEME["fg"]
            btn_start.text = "开始专注"
            btn_start.bgcolor = THEME["white"]
            btn_skip.visible = False
            txt_cat.value = random.choice(emojis["idle"])

        total_duration = next_min * 60
        txt_timer.value = f"{next_min:02}:00"
        ring_timer.value = 1.0

        # 5秒后停止闹钟声
        def stop_alarm():
            time.sleep(5)
            AlarmHelper.stop_alarm_sound()

        threading.Thread(target=stop_alarm, daemon=True).start()

        page.update()

    # ==========================================
    # 生命周期处理
    # ==========================================
    def handle_lifecycle(e):
        nonlocal timer_running
        print(f"📱 生命周期: {e.data}")

        if e.data == "resumed" and end_timestamp > 0:
            remaining = int(end_timestamp - time.time())
            if remaining <= 0:
                finish_cycle()
            elif timer_running:
                txt_timer.value = f"{remaining // 60:02}:{remaining % 60:02}"
                if total_duration > 0:
                    ring_timer.value = max(0, remaining / total_duration)
                page.update()

    page.on_app_lifecycle_state_change = handle_lifecycle

    # ==========================================
    # 计时器循环
    # ==========================================
    def timer_loop():
        nonlocal timer_running
        while timer_running and end_timestamp > 0:
            remaining = int(end_timestamp - time.time())
            if remaining <= 0:
                finish_cycle()
                break
            txt_timer.value = f"{remaining // 60:02}:{remaining % 60:02}"
            if total_duration > 0:
                ring_timer.value = max(0, min(1, remaining / total_duration))
            try:
                page.update()
            except:
                pass
            time.sleep(0.5)

    # ==========================================
    # 开始/暂停
    # ==========================================
    def toggle_timer(e):
        nonlocal timer_running, end_timestamp, total_duration

        if not timer_running:
            # 开始计时
            timer_running = True
            btn_start.text = "暂停"
            txt_cat.value = random.choice(emojis["work"])

            # 获取 WakeLock
            AlarmHelper.acquire_wake_lock()

            # 播放背景音乐
            if bgm_enabled:
                try:
                    audio_bg.play()
                except:
                    pass

            # 计算时长
            try:
                parts = txt_timer.value.split(":")
                current_secs = int(parts[0]) * 60 + int(parts[1])
            except:
                current_secs = logic.data["focus_min"] * 60

            total_duration = current_secs
            end_timestamp = time.time() + current_secs

            # 🔔 设置系统闹钟作为备份（最可靠！）
            if use_system_alarm and ANDROID_NATIVE:
                minutes = current_secs // 60
                label = "休息时间到" if is_break_mode else "专注完成啦"
                AlarmHelper.set_system_alarm(minutes + 1, label)  # +1分钟作为缓冲
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"📢 已设置系统闹钟备份 ({minutes}分钟后)"),
                    open=True
                )

            # 启动计时线程
            threading.Thread(target=timer_loop, daemon=True).start()

        else:
            # 暂停
            timer_running = False
            btn_start.text = "继续"
            txt_cat.value = random.choice(emojis["idle"])

            # 释放 WakeLock
            AlarmHelper.release_wake_lock()

            try:
                audio_bg.pause()
            except:
                pass

        page.update()

    # ==========================================
    # UI 组件
    # ==========================================
    txt_weather = ft.Text("加载中...", size=11, color=THEME["fg"])

    def weather_thread():
        while True:
            txt_weather.value = logic.fetch_weather()
            try:
                page.update()
            except:
                pass
            time.sleep(300)

    threading.Thread(target=weather_thread, daemon=True).start()

    # 系统闹钟开关
    switch_system_alarm = ft.Switch(
        value=use_system_alarm,
        active_color=THEME["fg"],
        on_change=lambda e: toggle_system_alarm(e)
    )

    def toggle_system_alarm(e):
        nonlocal use_system_alarm
        use_system_alarm = e.control.value
        logic.data["use_system_alarm"] = use_system_alarm
        logic.save_data()

    txt_days_label = ft.Text(f"距离{logic.data['target_name']}还剩", size=13, color="grey")
    txt_days_num = ft.Text(f"{logic.get_main_days_left()}", size=36, weight="bold", color=THEME["fg"])

    txt_timer_title = ft.Text("准备专注", size=16, weight="bold", color=THEME["fg"])
    txt_cat = ft.Text(random.choice(emojis["idle"]), size=18, color=THEME["fg"])
    txt_timer = ft.Text(f"{logic.data['focus_min']:02}:00", size=50, weight="bold", color=THEME["fg"])

    ring_timer = ft.ProgressRing(
        width=220, height=220, stroke_width=12,
        value=1.0, color=THEME["fg"], bgcolor=THEME["ring_bg"]
    )

    btn_start = ft.ElevatedButton(
        text="开始专注", width=140, height=50,
        style=ft.ButtonStyle(
            bgcolor=THEME["white"], color=THEME["fg"],
            shape=ft.RoundedRectangleBorder(radius=25)
        ),
        on_click=toggle_timer
    )

    def skip_break(e):
        nonlocal timer_running, is_break_mode, total_duration, end_timestamp
        timer_running = False
        is_break_mode = False
        end_timestamp = 0
        AlarmHelper.release_wake_lock()
        AlarmHelper.stop_alarm_sound()
        try:
            audio_bg.pause()
        except:
            pass

        mins = logic.data["focus_min"]
        total_duration = mins * 60
        txt_timer_title.value = "准备专注"
        txt_timer.value = f"{mins:02}:00"
        txt_timer.color = THEME["fg"]
        ring_timer.color = THEME["fg"]
        ring_timer.value = 1.0
        btn_start.text = "开始专注"
        btn_start.bgcolor = THEME["white"]
        btn_skip.visible = False
        txt_cat.value = random.choice(emojis["idle"])
        page.update()

    btn_skip = ft.ElevatedButton(
        text="跳过休息", width=140, height=50, visible=False,
        style=ft.ButtonStyle(bgcolor=THEME["orange"], color="white"),
        on_click=skip_break
    )

    txt_tomato_stats = ft.Text(f"今日: {logic.data['tomatoes']} 🐟", size=13, color=THEME["fg"])
    txt_slogan = ft.Text(logic.get_random_quote(), size=11, color=THEME["fg"], italic=True, text_align="center")

    # ==========================================
    # 首页视图
    # ==========================================
    view_home = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=15, bottom=100),
        content=ft.Column([
            # 天气 + 系统闹钟开关
            ft.Row([
                ft.Container(
                    content=ft.Row([ft.Icon(ft.Icons.PETS, size=14, color=THEME["fg"]), txt_weather], spacing=5),
                    bgcolor="#80FFF0E6", padding=ft.padding.symmetric(horizontal=12, vertical=6), border_radius=20
                ),
                ft.Container(expand=True),
                ft.Row([
                    ft.Text("系统闹钟", size=10, color="grey"),
                    switch_system_alarm
                ], spacing=5)
            ]),

            ft.Container(height=15),

            # 提示信息
            ft.Container(
                content=ft.Text(
                    "💡 开启「系统闹钟」后，即使切屏/熄屏也能收到提醒！",
                    size=11, color=THEME["fg"], text_align="center"
                ),
                bgcolor="#40FFFFFF",
                padding=10,
                border_radius=10,
                width=350
            ),

            ft.Container(height=15),

            # 倒计时卡片
            ft.Container(
                content=ft.Column([
                    txt_days_label,
                    ft.Row([txt_days_num, ft.Text("天", size=14, color=THEME["fg"])],
                           alignment="center", vertical_alignment="end")
                ], horizontal_alignment="center", spacing=0),
                bgcolor=THEME["white"], padding=15, border_radius=15, width=280,
                shadow=ft.BoxShadow(blur_radius=10, color="#1A000000")
            ),

            ft.Container(height=20),

            # 计时器
            ft.Stack([
                ft.Container(width=220, height=220, border_radius=110, bgcolor=THEME["white"],
                             shadow=ft.BoxShadow(blur_radius=15, color="#1A000000")),
                ring_timer,
                ft.Container(
                    content=ft.Column([txt_cat, txt_timer], alignment="center", horizontal_alignment="center"),
                    alignment=ft.alignment.center, width=220, height=220
                )
            ], width=220, height=220),

            ft.Container(height=20),

            # 按钮
            ft.Column([btn_start, ft.Container(height=5), btn_skip], horizontal_alignment="center"),

            ft.Container(height=15),
            txt_tomato_stats,
            ft.Container(height=10),
            txt_slogan,

        ], horizontal_alignment="center", scroll="auto")
    )

    # ==========================================
    # 设置页面
    # ==========================================
    input_name = ft.TextField(label="目标名称", value=logic.data["target_name"], bgcolor=THEME["white"])
    input_date = ft.TextField(label="目标日期", value=logic.data["target_date"], bgcolor=THEME["white"])
    input_focus = ft.TextField(label="专注时长(分)", value=str(logic.data["focus_min"]), bgcolor=THEME["white"])
    input_break = ft.TextField(label="休息时长(分)", value=str(logic.data["break_min"]), bgcolor=THEME["white"])

    def save_settings(e):
        logic.update_settings(
            input_name.value, input_date.value, logic.data["city"],
            input_focus.value, input_break.value
        )
        txt_days_label.value = f"距离{input_name.value}还剩"
        txt_days_num.value = f"{logic.get_main_days_left()}"
        if not timer_running:
            mins = logic.data["focus_min"]
            txt_timer.value = f"{mins:02}:00"
            nonlocal total_duration
            total_duration = mins * 60
        page.snack_bar = ft.SnackBar(ft.Text("设置已保存！"), open=True)
        page.update()

    view_settings = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=20, bottom=100),
        content=ft.Column([
            ft.Text("设置 ⚙️", size=24, weight="bold", color=THEME["fg"]),
            ft.Container(height=15),
            input_name, input_date, input_focus, input_break,
            ft.Container(height=15),
            ft.ElevatedButton("保存设置", on_click=save_settings, bgcolor=THEME["white"], color=THEME["fg"]),
            ft.Container(height=20),

            # 系统闹钟说明
            ft.Container(
                content=ft.Column([
                    ft.Text("🔔 关于后台提醒", size=14, weight="bold", color=THEME["fg"]),
                    ft.Text(
                        "开启「系统闹钟」后，应用会调用手机自带的闹钟功能，"
                        "即使应用被关闭也能收到提醒。\n\n"
                        "首次使用时，手机可能会询问是否允许设置闹钟，请点击「允许」。",
                        size=12, color="grey"
                    )
                ], spacing=5),
                bgcolor=THEME["comp_bg"],
                padding=15,
                border_radius=10
            )
        ], scroll="auto")
    )

    # ==========================================
    # 导航栏
    # ==========================================
    def nav_change(e):
        page.controls.clear()
        idx = e.control.selected_index
        if idx == 0:
            page.add(view_home)
        else:
            page.add(view_settings)
        page.add(nav_bar)
        page.update()

    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.TIMER, label="专注"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="设置"),
        ],
        on_change=nav_change,
        bgcolor=THEME["white"],
        selected_index=0
    )

    page.add(view_home)
    page.add(nav_bar)


ft.app(target=main)
