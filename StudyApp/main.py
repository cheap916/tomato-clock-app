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
# 🔔 跨平台通知模块 (增强版)
# ==========================================
try:
    from plyer import vibrator

    VIBRATOR_AVAILABLE = True
except ImportError:
    VIBRATOR_AVAILABLE = False

try:
    from plyer import notification

    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False

# 尝试导入 Android 专用模块 (用于后台闹钟)
ANDROID_NATIVE = False
try:
    from android import mActivity
    from jnius import autoclass

    Context = autoclass('android.content.Context')
    NotificationManager = autoclass('android.app.NotificationManager')
    NotificationChannel = autoclass('android.app.NotificationChannel')
    NotificationCompat = autoclass('androidx.core.app.NotificationCompat')
    PendingIntent = autoclass('android.app.PendingIntent')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    RingtoneManager = autoclass('android.media.RingtoneManager')
    AudioAttributes = autoclass('android.media.AudioAttributes')
    Build = autoclass('android.os.Build')

    ANDROID_NATIVE = True
    print("✅ Android 原生模块加载成功！")
except Exception as e:
    print(f"⚠️ Android 原生模块不可用: {e}")


# ==========================================
# 🔔 通知助手类
# ==========================================
class NotificationHelper:
    """跨平台通知助手"""

    CHANNEL_ID = "cat_focus_alarm"
    CHANNEL_NAME = "猫猫专注提醒"

    @classmethod
    def init_android_channel(cls):
        """初始化 Android 通知渠道 (Android 8.0+)"""
        if not ANDROID_NATIVE:
            return

        try:
            if Build.VERSION.SDK_INT >= 26:  # Android O+
                context = mActivity.getApplicationContext()
                nm = context.getSystemService(Context.NOTIFICATION_SERVICE)

                # 创建高优先级通知渠道
                channel = NotificationChannel(
                    cls.CHANNEL_ID,
                    cls.CHANNEL_NAME,
                    NotificationManager.IMPORTANCE_HIGH
                )
                channel.setDescription("专注计时完成提醒")
                channel.enableVibration(True)
                channel.setVibrationPattern([0, 500, 200, 500])

                # 设置提示音
                alarm_uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
                audio_attrs = AudioAttributes.Builder() \
                    .setUsage(AudioAttributes.USAGE_ALARM) \
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION) \
                    .build()
                channel.setSound(alarm_uri, audio_attrs)

                nm.createNotificationChannel(channel)
                print("✅ Android 通知渠道创建成功")
        except Exception as e:
            print(f"创建通知渠道失败: {e}")

    @classmethod
    def send_alarm_notification(cls, title, message):
        """发送高优先级闹钟通知 (会发出声音和震动)"""

        # 方案1: 使用 Android 原生通知 (最可靠)
        if ANDROID_NATIVE:
            try:
                context = mActivity.getApplicationContext()
                nm = context.getSystemService(Context.NOTIFICATION_SERVICE)

                # 创建点击通知打开应用的 Intent
                intent = context.getPackageManager().getLaunchIntentForPackage(
                    context.getPackageName()
                )
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)

                pending_intent = PendingIntent.getActivity(
                    context, 0, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                )

                # 获取系统闹钟铃声
                alarm_uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)

                # 构建通知
                builder = NotificationCompat.Builder(context, cls.CHANNEL_ID) \
                    .setSmallIcon(context.getApplicationInfo().icon) \
                    .setContentTitle(title) \
                    .setContentText(message) \
                    .setPriority(NotificationCompat.PRIORITY_MAX) \
                    .setCategory(NotificationCompat.CATEGORY_ALARM) \
                    .setAutoCancel(True) \
                    .setContentIntent(pending_intent) \
                    .setDefaults(NotificationCompat.DEFAULT_VIBRATE) \
                    .setSound(alarm_uri)

                # 全屏 Intent (让通知更醒目)
                builder.setFullScreenIntent(pending_intent, True)

                nm.notify(1001, builder.build())
                print("✅ Android 原生通知发送成功")
                return True

            except Exception as e:
                print(f"Android 原生通知失败: {e}")

        # 方案2: 使用 plyer 通知 (备用方案)
        if NOTIFICATION_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="猫猫专注",
                    timeout=30,
                    ticker=message,
                    toast=True
                )
                print("✅ Plyer 通知发送成功")
                return True
            except Exception as e:
                print(f"Plyer 通知失败: {e}")

        return False

    @classmethod
    def vibrate(cls, duration=2):
        """震动"""
        if VIBRATOR_AVAILABLE:
            try:
                vibrator.vibrate(duration)
            except:
                pass

        # Android 原生震动
        if ANDROID_NATIVE:
            try:
                context = mActivity.getApplicationContext()
                v = context.getSystemService(Context.VIBRATOR_SERVICE)
                if Build.VERSION.SDK_INT >= 26:
                    VibrationEffect = autoclass('android.os.VibrationEffect')
                    v.vibrate(VibrationEffect.createOneShot(duration * 1000, VibrationEffect.DEFAULT_AMPLITUDE))
                else:
                    v.vibrate(duration * 1000)
            except:
                pass


# ==========================================
# 1. 逻辑层
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
            "streak_days": 0
        }
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
                    if "daily_stats" not in self.data:
                        self.data["daily_stats"] = {}
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
            today = datetime.now().date()
            return (target - today).days
        except:
            return 0

    def update_settings(self, name, date, city, focus_min, break_min):
        self.data["target_name"] = name
        self.data["target_date"] = date
        self.data["city"] = city
        try:
            self.data["focus_min"] = int(focus_min)
        except:
            self.data["focus_min"] = 25
        try:
            self.data["break_min"] = int(break_min)
        except:
            self.data["break_min"] = 5
        self.save_data()

    def add_task(self, text, priority="green"):
        if text:
            task_obj = {"text": text, "priority": priority, "created": datetime.now().strftime("%Y-%m-%d")}
            self.data["tasks"].append(task_obj)
            self.save_data()

    def remove_task(self, index):
        if 0 <= index < len(self.data["tasks"]):
            task_item = self.data["tasks"][index]
            content = task_item["text"] if isinstance(task_item, dict) else task_item
            self.data["tasks"].pop(index)
            time_str = datetime.now().strftime("%H:%M")
            self.data["history"].append(f"[{time_str}] 爪子一挥，完成: {content}")
            self.save_data()

    def add_countdown_event(self, title, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            self.data["countdowns"].append({"title": title, "date": date_str})
            self.save_data()
            return True
        except:
            return False

    def remove_countdown_event(self, index):
        if 0 <= index < len(self.data["countdowns"]):
            event = self.data["countdowns"][index]
            self.data["countdowns"].pop(index)
            time_str = datetime.now().strftime("%H:%M")
            self.data["history"].append(f"[{time_str}] 🗑️ 埋掉旧目标: {event['title']}")
            self.save_data()

    def increment_tomato(self):
        self.data["tomatoes"] += 1
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data.get("daily_stats", {}):
            self.data["daily_stats"][today] = 0
        self.data["daily_stats"][today] += 1
        time_str = datetime.now().strftime("%H:%M")
        self.data["history"].append(f"[{time_str}] 捕获一只番茄 🍅 (嚼嚼嚼)")
        self.save_data()
        return self.data["tomatoes"]

    def clear_daily_stats(self):
        self.data["tomatoes"] = 0
        self.save_data()

    def check_in(self):
        today = datetime.now().strftime("%Y-%m-%d")
        last = self.data.get("last_checkin", "")
        if last == today:
            return False, "喵？今天已经按过爪印啦！"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last == yesterday:
            self.data["streak_days"] = self.data.get("streak_days", 0) + 1
        else:
            self.data["streak_days"] = 1
        self.data["last_checkin"] = today
        time_str = datetime.now().strftime("%H:%M")
        self.data["history"].append(f"[{time_str}] 🐾 按下今日爪印")
        self.save_data()
        return True, f"喵！签到成功！连签 {self.data['streak_days']} 天 🎉"

    def is_checked_in(self):
        return self.data.get("last_checkin") == datetime.now().strftime("%Y-%m-%d")

    def get_random_quote(self):
        quotes = [
            "既然上了贼船\n就做个快乐的海盗猫",
            "与其仰望星空\n不如去抓那只蝴蝶",
            "哪怕是流浪猫\n也有看夕阳的权利",
            "保持好奇心\n是猫咪长寿的秘诀",
            "没有什么烦恼\n是一个罐头解决不了的",
            "只要步履不停\n小鱼干终将抵达",
            "现在的努力\n是为了以后能躺平晒太阳"
        ]
        return random.choice(quotes)

    def fetch_weather(self):
        city = self.data.get("city", "郑州")
        try:
            url = f"https://wttr.in/{city}?format=%C+%t&lang=zh&_={int(time.time())}"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, timeout=10, headers=headers)
            if res.status_code == 200:
                current_time = datetime.now().strftime("%H:%M")
                return f"{city} {res.text.strip()} ({current_time})"
            return f"{city}: 信号被外星猫劫持了"
        except:
            return "网络线被咬断了..."

    def get_weekly_data(self):
        stats = []
        today = datetime.now().date()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            count = self.data.get("daily_stats", {}).get(day_str, 0)
            stats.append({"date": day.strftime("%m-%d"), "count": count, "full_date": day_str})
        return stats


# ==========================================
# 2. 界面层
# ==========================================
def main(page: ft.Page):
    page.window_width = 390
    page.window_height = 844
    page.title = "猫猫专注助手"
    page.theme_mode = ft.ThemeMode.LIGHT

    # 初始化 Android 通知渠道
    NotificationHelper.init_android_channel()

    THEME = {
        "bg": "#FFCCCC",
        "fg": "#D24D57",
        "comp_bg": "#FFF0E6",
        "green": "#4CAF50",
        "white": "#FFFFFF",
        "red": "#FF5252",
        "card_bg": "#FFFFFF",
        "orange": "#FF9800",
        "ring_bg": "#FFEEEE"
    }
    page.bgcolor = THEME["bg"]
    page.padding = 0
    page.keep_screen_on = True

    logic = StudyLogic()

    # ==========================================
    # 🔑 关键状态变量
    # ==========================================
    timer_running = False
    is_break_mode = False
    end_timestamp = 0  # 🔑 结束时间戳 (关键!)
    total_duration = logic.data["focus_min"] * 60
    alarm_triggered = False  # 🔑 防止重复触发
    bgm_enabled = True
    current_bgm_index = 0

    bgm_playlist = [
        {"name": "卡农", "src": "assets/kanong.mp3"},
    ]

    emojis = {
        "idle": ["( =ω=)..zzZ", "(=^･ω･^=)", "ฅ(ﾐ・ﻌ・ﾐ)ฅ", "( -ω-)", "₍ ᐢ. ̫ .ᐢ ₎"],
        "work": ["( * >ω<)p", "q(>ω< * )", "φ(．．;)", "(ง •̀_•́)ง", "(=`ω´=)"],
        "break": ["( ~ o ~ )~", "旦_(^O^ )", "(=^ ◡ ^=)", "☕(・ω・)", "🧴(舔毛中)"],
        "happy": ["(≧◡≦) ♡", "(=^･^=)♪", "(/ =ω=)/", "o(>ω<)o", "⸜( ˙˘˙)⸝"],
        "touch": ["(///ω///)", "(=ﾟωﾟ)ﾉ", "(/ω＼)", "Meow~"]
    }

    # 音频初始化
    audio_alarm = flet_audio.Audio(src="assets/alarm.mp3", autoplay=False)
    audio_bg = flet_audio.Audio(src=bgm_playlist[0]["src"], autoplay=False, release_mode="loop")
    page.overlay.append(audio_alarm)
    page.overlay.append(audio_bg)

    # ==========================================
    # 🔔 核心：完成周期处理
    # ==========================================
    def finish_cycle():
        nonlocal timer_running, is_break_mode, total_duration, end_timestamp, alarm_triggered

        print(f"🔔 finish_cycle 被调用! is_break_mode={is_break_mode}")

        # 停止背景音乐
        try:
            audio_bg.pause()
        except:
            pass

        # 🔔 播放闹钟声音 (应用内)
        try:
            audio_alarm.seek(0)
            page.update()
            audio_alarm.play()
        except Exception as e:
            print(f"闹钟播放失败: {e}")

        # 🔔 发送系统通知 + 震动 (即使在后台也能收到)
        if not is_break_mode:
            NotificationHelper.send_alarm_notification(
                "🎉 专注完成！",
                "喵！捕猎结束啦，该休息一下~ 🐾"
            )
            logic.increment_tomato()
            txt_tomato_stats.value = f"今日渔获: {get_tomato_str()}"
            is_break_mode = True
            next_min = logic.data["break_min"]
            total_duration = next_min * 60
            txt_timer_title.value = f"☕ 舔毛时间 {next_min} 分钟"
            txt_timer.color = THEME["green"]
            ring_timer.color = THEME["green"]
            btn_start.text = "开始舔毛"
            btn_start.bgcolor = THEME["green"]
            btn_start.color = "white"
            btn_skip.visible = True
            txt_cat.value = random.choice(emojis["break"])
            msg = "喵！捕猎完成！该休息啦 (呼噜呼噜~)"
        else:
            NotificationHelper.send_alarm_notification(
                "☀️ 休息结束！",
                "睡醒了，准备继续抓鱼喵~ 🐟"
            )
            is_break_mode = False
            next_min = logic.data["focus_min"]
            total_duration = next_min * 60
            txt_timer_title.value = "准备捕猎"
            txt_timer.color = THEME["fg"]
            ring_timer.color = THEME["fg"]
            btn_start.text = "开始捕猎"
            btn_start.bgcolor = THEME["white"]
            btn_start.color = THEME["fg"]
            btn_skip.visible = False
            txt_cat.value = random.choice(emojis["idle"])
            msg = "睡醒了，准备继续抓鱼！"

        # 震动提醒
        NotificationHelper.vibrate(3)

        txt_timer.value = f"{next_min:02}:00"
        ring_timer.value = 1.0
        timer_running = False
        end_timestamp = 0
        alarm_triggered = True

        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
        page.update()

    # ==========================================
    # 🔑 后台监控线程 (关键!)
    # ==========================================
    def background_alarm_monitor():
        """后台监控线程 - 检测时间到达并发送系统通知"""
        nonlocal alarm_triggered
        last_check = 0

        while True:
            try:
                now = time.time()

                # 每秒检查一次
                if timer_running and end_timestamp > 0 and not alarm_triggered:
                    remaining = end_timestamp - now

                    if remaining <= 0:
                        print(f"⏰ 后台检测到时间到！发送通知...")

                        # 🔔 发送系统级通知 (这是关键! 即使线程被挂起后恢复也会执行)
                        if not is_break_mode:
                            NotificationHelper.send_alarm_notification(
                                "🎉 专注完成！",
                                "喵！25分钟到了，快回来看看吧~ 🐾"
                            )
                        else:
                            NotificationHelper.send_alarm_notification(
                                "☀️ 休息结束！",
                                "喵！休息时间结束啦~ 🐟"
                            )

                        NotificationHelper.vibrate(3)
                        alarm_triggered = True

                    # 还剩1分钟时提前通知
                    elif remaining <= 60 and remaining > 55 and now - last_check > 60:
                        NotificationHelper.send_alarm_notification(
                            "⏳ 还剩1分钟",
                            "马上就要完成啦，坚持住喵！"
                        )
                        last_check = now

            except Exception as e:
                print(f"后台监控异常: {e}")

            time.sleep(1)

    # 启动后台监控线程
    monitor_thread = threading.Thread(target=background_alarm_monitor, daemon=True)
    monitor_thread.start()

    # ==========================================
    # 🔑 生命周期处理 (应用恢复时检查)
    # ==========================================
    def handle_lifecycle_change(e):
        nonlocal timer_running, alarm_triggered

        print(f"📱 生命周期变化: {e.data}")

        if e.data == "resumed":
            now = time.time()

            # 检查是否有正在进行的计时
            if end_timestamp > 0:
                remaining = int(end_timestamp - now)

                if remaining <= 0 and not alarm_triggered:
                    # ⏰ 时间已到，立即触发完成逻辑
                    print("📱 恢复时检测到时间已到，触发闹钟！")
                    finish_cycle()
                    return

                elif remaining > 0 and timer_running:
                    # 更新显示
                    txt_timer.value = f"{remaining // 60:02}:{remaining % 60:02}"
                    if total_duration > 0:
                        progress = max(0, min(1, remaining / total_duration))
                        ring_timer.value = progress

                    # 确保计时线程在运行
                    ensure_timer_running()
                    page.update()

        elif e.data == "inactive" or e.data == "paused":
            # 应用进入后台，记录状态
            print(f"📱 应用进入后台, end_timestamp={end_timestamp}")

    page.on_app_lifecycle_state_change = handle_lifecycle_change

    # ==========================================
    # 确保计时器线程运行
    # ==========================================
    def ensure_timer_running():
        """检查并重启计时器线程"""
        if timer_running:
            thread_alive = any(t.name == "timer_loop" for t in threading.enumerate())
            if not thread_alive:
                print("🔄 重启计时器线程")
                t = threading.Thread(target=timer_loop, daemon=True, name="timer_loop")
                t.start()

    # ==========================================
    # 计时器主循环
    # ==========================================
    def timer_loop():
        nonlocal timer_running, alarm_triggered

        while timer_running:
            now = time.time()
            remaining = int(end_timestamp - now)

            if remaining <= 0:
                if not alarm_triggered:
                    finish_cycle()
                break

            txt_timer.value = f"{remaining // 60:02}:{remaining % 60:02}"
            if total_duration > 0:
                ratio = max(0, min(1, remaining / total_duration))
                ring_timer.value = ratio

            try:
                page.update()
            except:
                pass

            time.sleep(0.5)

    # ==========================================
    # 开始/暂停计时
    # ==========================================
    def toggle_timer(e):
        nonlocal timer_running, end_timestamp, total_duration, alarm_triggered

        if not timer_running:
            timer_running = True
            alarm_triggered = False  # 重置触发标志
            btn_start.text = "爪下留情(暂停)"
            txt_cat.value = random.choice(emojis["work"])

            if bgm_enabled:
                try:
                    audio_bg.play()
                except:
                    pass

            try:
                parts = txt_timer.value.split(":")
                current_secs = int(parts[0]) * 60 + int(parts[1])
            except:
                current_secs = logic.data["focus_min"] * 60

            if not is_break_mode and current_secs == logic.data["focus_min"] * 60:
                total_duration = current_secs
            elif is_break_mode and current_secs == logic.data["break_min"] * 60:
                total_duration = current_secs

            # 🔑 记录结束时间戳
            end_timestamp = time.time() + current_secs
            print(f"⏱️ 计时开始! 结束时间戳: {end_timestamp}, 持续 {current_secs} 秒")

            # 启动计时线程
            t = threading.Thread(target=timer_loop, daemon=True, name="timer_loop")
            t.start()

        else:
            timer_running = False
            btn_start.text = "继续捕猎" if not is_break_mode else "继续舔毛"
            txt_cat.value = random.choice(emojis["idle"])
            try:
                audio_bg.pause()
            except:
                pass

        page.update()

    # ==========================================
    # 其余 UI 组件 (保持不变的部分)
    # ==========================================

    def get_watermark():
        return ft.Container(
            content=ft.Text("Created by lian · 陪你一同努力\n科技服务于人民 · 也不要忘了喂猫", size=10,
                            color=THEME["fg"], opacity=0.5, text_align="center"),
            padding=ft.padding.only(top=10, bottom=5),
            alignment=ft.alignment.center
        )

    txt_weather = ft.Text(value="正在召唤气象喵...", size=11, color=THEME["fg"])
    weather_icon = ft.Icon(name=ft.Icons.PETS, size=14, color=THEME["fg"])

    weather_pill = ft.Container(
        content=ft.Row([weather_icon, txt_weather], alignment="center", spacing=5),
        bgcolor="#80FFF0E6",
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border_radius=20,
    )

    def weather_loop_thread():
        while True:
            w_str = logic.fetch_weather()
            txt_weather.value = w_str
            weather_icon.name = random.choice([ft.Icons.PETS, ft.Icons.CLOUD_QUEUE, ft.Icons.WB_SUNNY])
            try:
                page.update()
            except:
                pass
            time.sleep(300)

    btn_checkin = ft.ElevatedButton(
        text="📅 按爪",
        bgcolor=THEME["white"],
        color=THEME["fg"],
        elevation=1,
        height=32,
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=10),
            shape=ft.RoundedRectangleBorder(radius=20),
            text_style=ft.TextStyle(size=12)
        )
    )

    def toggle_bgm(e):
        nonlocal bgm_enabled
        bgm_enabled = not bgm_enabled
        if bgm_enabled:
            btn_bgm.icon = ft.Icons.MUSIC_NOTE
            if timer_running:
                try:
                    audio_bg.play()
                except:
                    pass
        else:
            btn_bgm.icon = ft.Icons.MUSIC_OFF
            try:
                audio_bg.pause()
            except:
                pass
        btn_bgm.update()
        page.update()

    def next_bgm(e):
        nonlocal current_bgm_index
        current_bgm_index = (current_bgm_index + 1) % len(bgm_playlist)
        new_song = bgm_playlist[current_bgm_index]
        try:
            audio_bg.pause()
        except:
            pass
        audio_bg.src = new_song["src"]
        audio_bg.update()
        if bgm_enabled and timer_running:
            try:
                audio_bg.play()
            except:
                pass
        page.snack_bar = ft.SnackBar(ft.Text(f"🎵 切换至: {new_song['name']} 🐾"), open=True)
        page.update()

    btn_bgm = ft.IconButton(icon=ft.Icons.MUSIC_NOTE, icon_color=THEME["fg"], icon_size=20, on_click=toggle_bgm)
    btn_next_bgm = ft.IconButton(icon=ft.Icons.SKIP_NEXT, icon_color=THEME["fg"], icon_size=20, on_click=next_bgm)

    music_bar = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.MUSIC_NOTE, size=14, color=THEME["fg"]),
            ft.Text("背景音:", size=12, color=THEME["fg"]),
            btn_bgm,
            btn_next_bgm
        ], alignment="center", spacing=0),
        bgcolor="#80FFF0E6",
        padding=ft.padding.symmetric(horizontal=10, vertical=0),
        border_radius=20,
        height=32
    )

    def refresh_checkin_ui():
        if logic.is_checked_in():
            btn_checkin.text = f"✅ 已按爪 ({logic.data['streak_days']})"
            btn_checkin.bgcolor = THEME["green"]
            btn_checkin.color = "white"
        else:
            btn_checkin.text = "🐾 按爪签到"
            btn_checkin.bgcolor = THEME["white"]
            btn_checkin.color = THEME["fg"]
        page.update()

    def checkin_click(e):
        success, msg = logic.check_in()
        refresh_checkin_ui()
        if success:
            txt_cat.value = random.choice(emojis["happy"])
        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
        page.update()

    btn_checkin.on_click = checkin_click
    refresh_checkin_ui()

    txt_days_label = ft.Text(f"距离{logic.data['target_name']}还剩", size=13, color="grey")
    txt_days_num = ft.Text(f"{logic.get_main_days_left()}", size=36, weight="bold", color=THEME["fg"])
    txt_days_unit = ft.Text("个罐头", size=12, color=THEME["fg"], weight="bold", offset=ft.Offset(0, 0.6))

    countdown_card = ft.Container(
        content=ft.Column([
            txt_days_label,
            ft.Row([txt_days_num, txt_days_unit], alignment="center", vertical_alignment="end")
        ], horizontal_alignment="center", spacing=0),
        bgcolor=THEME["white"],
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        border_radius=15,
        width=300,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#1A000000")
    )

    txt_timer_title = ft.Text("准备捕猎", size=16, weight="bold", color=THEME["fg"])
    txt_cat = ft.Text(random.choice(emojis["idle"]), size=18, color=THEME["fg"])
    txt_timer = ft.Text(f"{logic.data['focus_min']:02}:00", size=50, weight="bold", color=THEME["fg"])

    RING_SIZE = 230
    ring_timer = ft.ProgressRing(width=RING_SIZE, height=RING_SIZE, stroke_width=12, value=1.0, color=THEME["fg"],
                                 bgcolor=THEME["ring_bg"])

    stack_timer_display = ft.Stack(
        controls=[
            ft.Container(width=RING_SIZE, height=RING_SIZE, border_radius=115, bgcolor=THEME["white"],
                         shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="#1A000000")),
            ring_timer,
            ft.Container(
                content=ft.Column([ft.Container(height=10), txt_cat, txt_timer], alignment="center",
                                  horizontal_alignment="center", spacing=5),
                alignment=ft.alignment.center, width=RING_SIZE, height=RING_SIZE, border_radius=115,
            )
        ],
        width=RING_SIZE, height=RING_SIZE
    )

    btn_start = ft.ElevatedButton(
        text="开始捕猎", width=130, height=45,
        style=ft.ButtonStyle(bgcolor=THEME["white"], color=THEME["fg"], shape=ft.RoundedRectangleBorder(radius=25),
                             elevation=3),
        on_click=toggle_timer
    )

    def skip_break_e(e):
        nonlocal timer_running, is_break_mode, total_duration, end_timestamp
        timer_running = False
        is_break_mode = False
        end_timestamp = 0
        next_min = logic.data["focus_min"]
        total_duration = next_min * 60
        txt_timer_title.value = "准备捕猎"
        txt_timer.color = THEME["fg"]
        ring_timer.color = THEME["fg"]
        ring_timer.value = 1.0
        txt_timer.value = f"{next_min:02}:00"
        btn_start.text = "开始捕猎"
        btn_start.bgcolor = THEME["white"]
        btn_skip.visible = False
        txt_cat.value = random.choice(emojis["idle"])
        try:
            audio_bg.pause()
        except:
            pass
        page.snack_bar = ft.SnackBar(ft.Text("休息结束，准备出击！"), open=True)
        page.update()

    btn_skip = ft.ElevatedButton(
        text="不舔毛了", width=130, height=45, visible=False, on_click=skip_break_e,
        style=ft.ButtonStyle(bgcolor=THEME["orange"], color="white", shape=ft.RoundedRectangleBorder(radius=25),
                             elevation=3)
    )

    def get_tomato_str():
        t = "🐟 " * min(logic.data["tomatoes"], 6)
        if logic.data["tomatoes"] > 6:
            t += "..."
        if logic.data["tomatoes"] == 0:
            t = "(空空如也)"
        return t

    txt_tomato_stats = ft.Text(f"今日渔获: {get_tomato_str()}", color=THEME["fg"], size=13)
    txt_slogan = ft.Text(logic.get_random_quote(), italic=True, text_align="center", color=THEME["fg"], size=11,
                         opacity=0.8)

    def pet_the_cat(e):
        txt_cat.value = random.choice(emojis["touch"])
        txt_cat.color = THEME["orange"]
        txt_cat.update()
        NotificationHelper.vibrate(0.3)
        page.snack_bar = ft.SnackBar(ft.Text("喵！(蹭蹭)"), open=True, duration=1000)
        page.update()
        time.sleep(0.5)
        txt_cat.color = THEME["fg"]
        txt_cat.update()

    stack_timer_display.controls[2].on_click = pet_the_cat

    def open_share_card(e):
        today_date = datetime.now().strftime("%Y年%m月%d日")
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]
        tomato_count = logic.data["tomatoes"]
        focus_minutes = tomato_count * logic.data["focus_min"]
        poster_content = ft.Container(
            bgcolor=THEME["card_bg"], padding=30, border_radius=20, width=300, height=450,
            border=ft.border.all(4, THEME["fg"]),
            content=ft.Column([
                ft.Row([ft.Text(f"{today_date} {weekday}", color="grey", size=14)], alignment="center"),
                ft.Divider(color=THEME["fg"], thickness=1),
                ft.Container(height=20),
                ft.Text("今日战绩", size=16, color=THEME["fg"]),
                ft.Text(f"{tomato_count}", size=80, weight="bold", color=THEME["fg"]),
                ft.Text(f"条小鱼干 ({focus_minutes}分钟)", size=14, color="grey"),
                ft.Container(height=20),
                ft.Text(random.choice(emojis["happy"]), size=40, color=THEME["fg"]),
                ft.Container(height=20),
                ft.Container(
                    content=ft.Text(txt_slogan.value, italic=True, text_align="center", color=THEME["fg"], size=14),
                    padding=10),
                ft.Container(expand=True),
                ft.Divider(color=THEME["fg"], thickness=1),
                ft.Row([ft.Icon(ft.Icons.PETS, color=THEME["fg"], size=20),
                        ft.Text("猫猫专注助手", weight="bold", color=THEME["fg"])], alignment="center")
            ], horizontal_alignment="center")
        )
        dlg_share = ft.AlertDialog(
            content=ft.Column([
                poster_content,
                ft.Container(height=10),
                ft.Text("✨ 截图炫耀一下战绩 ✨", color="white", size=12, text_align="center"),
                ft.IconButton(icon="close", icon_color="white", on_click=lambda e: page.close(dlg_share))
            ], tight=True, horizontal_alignment="center"),
            bgcolor="transparent", modal=True
        )
        page.open(dlg_share)

    btn_share = ft.IconButton(icon="share", icon_color=THEME["fg"], tooltip="生成海报", on_click=open_share_card)

    view_home = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=10, bottom=160),
        content=ft.Column([
            ft.Row([weather_pill, ft.Container(expand=True), btn_checkin], alignment="spaceBetween"),
            ft.Container(height=10),
            music_bar,
            ft.Container(height=10),
            countdown_card,
            ft.Container(height=20),
            stack_timer_display,
            ft.Container(height=20),
            ft.Column([btn_start, ft.Container(height=5), btn_skip], horizontal_alignment="center"),
            ft.Container(height=15),
            ft.Container(
                content=ft.Row([txt_tomato_stats, ft.Container(width=10), btn_share], alignment="center",
                               vertical_alignment="center"),
                bgcolor=THEME["comp_bg"], padding=5, border_radius=10
            ),
            ft.Container(height=10),
            txt_slogan,
            get_watermark(),
            ft.Container(height=30)
        ], horizontal_alignment="center", scroll="auto")
    )

    # ==========================================
    # 待办和设置页面 (简化版，保持核心功能)
    # ==========================================

    def show_history_e(e):
        hist_text = "\n".join(reversed(logic.data["history"][-20:]))
        if not hist_text:
            hist_text = "日记本被老鼠偷走了(空的)..."
        dlg = ft.AlertDialog(
            title=ft.Text("猫猫日记 🐾"),
            content=ft.Container(content=ft.Text(hist_text, size=12, selectable=True), height=300, width=300),
            actions=[ft.TextButton("关上日记", on_click=lambda e: page.close(dlg))],
            bgcolor=THEME["comp_bg"]
        )
        page.open(dlg)

    lv_events = ft.Column(spacing=10)
    lv_tasks = ft.ListView(expand=True, spacing=5)

    def render_events():
        lv_events.controls.clear()
        for i, item in enumerate(logic.data.get("countdowns", [])):
            title = item["title"]
            date_str = item["date"]
            days = logic.calculate_days(date_str)
            day_color = THEME["red"] if days < 0 else THEME["fg"]
            day_text = f"{days} 天" if days >= 0 else f"过期 {-days} 天"
            card = ft.Container(
                bgcolor=THEME["white"], padding=15, border_radius=10,
                shadow=ft.BoxShadow(blur_radius=5, color="#0D000000"),
                content=ft.Row([
                    ft.Column([ft.Text(title, size=16, weight="bold", color=THEME["fg"]),
                               ft.Text(date_str, size=12, color="grey")], expand=True),
                    ft.Column([ft.Text("剩余", size=10, color="grey"),
                               ft.Text(day_text, size=20, weight="bold", color=day_color)],
                              horizontal_alignment="center"),
                    ft.IconButton(icon="close", icon_size=18, icon_color="grey",
                                  on_click=lambda e, idx=i: delete_event(idx))
                ], alignment="space_between")
            )
            lv_events.controls.append(card)
        page.update()

    def delete_event(index):
        logic.remove_countdown_event(index)
        render_events()

    def render_tasks():
        lv_tasks.controls.clear()
        if not logic.data["tasks"]:
            lv_tasks.controls.append(ft.Container(
                content=ft.Column(
                    [ft.Text("( =ω=)..zzZ", size=40, color="grey"), ft.Text("暂无任务，去晒太阳吧~ ☀️", color="grey")],
                    horizontal_alignment="center"),
                alignment=ft.alignment.center, padding=40
            ))
        else:
            priority_map = {"red": THEME["red"], "orange": THEME["orange"], "green": THEME["green"]}
            for i, task_item in enumerate(logic.data["tasks"]):
                text = task_item["text"] if isinstance(task_item, dict) else task_item
                prio = task_item.get("priority", "green") if isinstance(task_item, dict) else "green"
                p_icon = ft.Icon(ft.Icons.CIRCLE, size=12, color=priority_map.get(prio, THEME["green"]))
                lv_tasks.controls.append(ft.Container(
                    bgcolor=THEME["comp_bg"], padding=12, border_radius=8,
                    content=ft.Row([
                        ft.Row([p_icon, ft.Text(text, size=14, color=THEME["fg"], expand=True)], expand=True,
                               spacing=10),
                        ft.IconButton(icon="delete_outline", icon_color=THEME["fg"], icon_size=20,
                                      on_click=lambda e, idx=i: delete_task(idx))
                    ])
                ))
        page.update()

    def delete_task(idx):
        logic.remove_task(idx)
        render_tasks()

    txt_input_task = ft.TextField(hint_text="输入待办...", expand=True, bgcolor=THEME["white"], color=THEME["fg"],
                                  border_radius=10, border_color="transparent")

    def add_task_e(e):
        if txt_input_task.value:
            logic.add_task(txt_input_task.value, "green")
            txt_input_task.value = ""
            render_tasks()

    dlg_event_title = ft.TextField(label="猎物名称(目标)", color=THEME["fg"])
    dlg_event_date = ft.TextField(label="狩猎日期 (YYYY-MM-DD)", color=THEME["fg"])

    def save_new_event(e):
        if logic.add_countdown_event(dlg_event_title.value, dlg_event_date.value):
            page.close(dlg_add_event)
            render_events()
            dlg_event_title.value = ""
            dlg_event_date.value = ""
            page.snack_bar = ft.SnackBar(ft.Text("喵！新目标锁定！"), open=True)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("日期写错啦(挠头)"), open=True)
        page.update()

    dlg_add_event = ft.AlertDialog(
        title=ft.Text("添加倒计时"),
        content=ft.Column([dlg_event_title, dlg_event_date], height=150),
        actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg_add_event)),
                 ft.TextButton("锁定目标", on_click=save_new_event)],
        bgcolor=THEME["comp_bg"]
    )

    def open_add_event_dialog(e):
        if not dlg_event_date.value:
            dlg_event_date.value = datetime.now().strftime("%Y-%m-%d")
        page.open(dlg_add_event)

    render_events()
    render_tasks()

    view_todo = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=20, bottom=160),
        content=ft.Column([
            ft.Row([
                ft.Text("鱼干清单 🐟", size=24, weight="bold", color=THEME["fg"]),
                ft.Row([
                    ft.IconButton(icon="history", icon_color=THEME["fg"], on_click=show_history_e),
                    ft.IconButton(icon="alarm_add", icon_color=THEME["fg"], on_click=open_add_event_dialog)
                ])
            ], alignment="space_between"),
            lv_events,
            ft.Divider(color=THEME["fg"], thickness=1, height=30),
            ft.Container(content=lv_tasks, expand=True, bgcolor=THEME["bg"]),
            ft.Row([txt_input_task,
                    ft.IconButton("add_circle", icon_color=THEME["fg"], icon_size=40, on_click=add_task_e)]),
            get_watermark()
        ])
    )

    # 设置页面
    def create_input(label, val):
        return ft.TextField(label=label, value=val, label_style=ft.TextStyle(color=THEME["fg"]), color=THEME["fg"],
                            bgcolor=THEME["white"], border_radius=10, border_color="transparent")

    input_name = create_input("猎物名称", logic.data["target_name"])
    input_date = create_input("狩猎日期", logic.data["target_date"])
    input_city = create_input("地盘(城市)", logic.data.get("city", "郑州"))
    input_focus = create_input("捕猎时长(分)", str(logic.data["focus_min"]))
    input_break = create_input("舔毛时长(分)", str(logic.data["break_min"]))

    def save_settings(e):
        logic.update_settings(input_name.value, input_date.value, input_city.value, input_focus.value,
                              input_break.value)
        txt_days_label.value = f"距离{input_name.value}还剩"
        txt_days_num.value = f"{logic.get_main_days_left()}"
        if not timer_running and not is_break_mode:
            mins = int(logic.data["focus_min"])
            txt_timer.value = f"{mins:02}:00"
            nonlocal total_duration
            total_duration = mins * 60
            ring_timer.value = 1.0
        page.snack_bar = ft.SnackBar(ft.Text("喵！设置保存成功！"), open=True)
        page.update()

    def clear_stats_e(e):
        logic.clear_daily_stats()
        txt_tomato_stats.value = "今日渔获: (空空如也)"
        page.snack_bar = ft.SnackBar(ft.Text("已清空，一切归零喵"), open=True)
        page.update()

    view_settings = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=20, bottom=160),
        content=ft.Column([
            ft.Text("猫窝设置 ⚙️", size=24, weight="bold", color=THEME["fg"]),
            ft.Container(height=10),
            input_name, input_date, input_city, input_focus, input_break,
            ft.Container(height=10),
            ft.ElevatedButton("保存设置喵", on_click=save_settings, bgcolor=THEME["white"], color=THEME["fg"],
                              width=120, elevation=2),
            ft.Divider(color=THEME["fg"]),
            ft.ElevatedButton("📜 翻看日记本", on_click=show_history_e, bgcolor=THEME["white"], color=THEME["fg"],
                              width=390, elevation=2),
            ft.Container(height=20),
            ft.Container(content=ft.TextButton("🗑️ 倒掉今日猫粮(清空数据)", on_click=clear_stats_e,
                                               style=ft.ButtonStyle(color=THEME["fg"])), alignment=ft.alignment.center),
            get_watermark()
        ], scroll="auto")
    )

    def nav_change(e):
        idx = e.control.selected_index
        page.controls.clear()
        if idx == 0:
            page.add(view_home)
        elif idx == 1:
            page.add(view_todo)
        elif idx == 2:
            page.add(view_settings)
        page.add(nav_bar)
        page.update()

    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.TIMER, label="捕猎"),
            ft.NavigationBarDestination(icon=ft.Icons.FORMAT_LIST_BULLETED, label="鱼干"),
            ft.NavigationBarDestination(icon=ft.Icons.HOME_FILLED, label="猫窝"),
        ],
        on_change=nav_change,
        bgcolor=THEME["white"],
        indicator_color=THEME["bg"],
        selected_index=0,
        elevation=10
    )

    page.add(view_home)
    page.add(nav_bar)
    threading.Thread(target=weather_loop_thread, daemon=True).start()


ft.app(target=main)