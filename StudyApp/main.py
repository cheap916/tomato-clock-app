import flet as ft
import flet_audio
import json
import os
import time
import random
import requests
import threading
from datetime import datetime, timedelta
from plyer import vibrator, notification


# ==========================================
# 1. 逻辑层 (已修复时长累加 & 周报统计)
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
            "today_minutes": 0,  # 新增：今日累计时长
            "tasks": [],
            "daily_stats": {},
            "countdowns": [],
            "history": [],
            "last_checkin": "",
            "streak_days": 0
        }
        self.load_data()

        # 🐱 猫咪冷知识库
        self.cat_facts = [
            "猫咪的耳朵有32块肌肉，能转180度喵！",
            "猫咪一天要睡12-16个小时，羡慕吧？",
            "猫咪的肉垫会排汗，是它们唯一的汗腺。",
            "每只猫的鼻纹都是独一无二的，像指纹一样。",
            "猫咪尝不出甜味，所以别给朕吃糖！",
            "猫咪即使从高处落下也能调整姿态安全着陆。",
            "世界上最长寿的猫活了38岁！",
            "猫咪呼噜声的频率可以促进骨骼愈合。",
            "三花猫绝大多数都是女孩子哦。",
            "猫咪看不清近处的东西，它是大远视眼。",
        ]

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
            task_obj = {
                "text": text,
                "priority": priority,
                "created": datetime.now().strftime("%Y-%m-%d")
            }
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

    # ✅ 修复1：时长累加逻辑
    def increment_tomato(self):
        self.data["tomatoes"] += 1

        # 获取当前专注时长
        current_min = self.data.get("focus_min", 25)

        # 1. 更新今日累加器 (给分享卡片用的)
        current_total = self.data.get("today_minutes", 0)
        self.data["today_minutes"] = current_total + current_min

        # 2. 更新每日统计 (给周报用的)
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data.get("daily_stats", {}):
            self.data["daily_stats"][today] = {"count": 0, "minutes": 0}

        # 兼容旧数据
        entry = self.data["daily_stats"][today]
        if isinstance(entry, int):
            entry = {"count": entry, "minutes": entry * current_min}
            self.data["daily_stats"][today] = entry

        self.data["daily_stats"][today]["count"] += 1
        self.data["daily_stats"][today]["minutes"] += current_min

        time_str = datetime.now().strftime("%H:%M")
        self.data["history"].insert(0, f"[{time_str}] 🍅 捕获成功 ({current_min}分钟)")
        if len(self.data["history"]) > 50: self.data["history"].pop()

        self.save_data()
        return self.data["tomatoes"]

    # ✅ 修复2：清空逻辑包含时长
    def clear_daily_stats(self):
        self.data["tomatoes"] = 0
        self.data["today_minutes"] = 0
        self.save_data()

    def check_in(self):
        today = datetime.now().strftime("%Y-%m-%d")
        last = self.data.get("last_checkin", "")
        if last == today: return False, "喵？今天已经按过爪印啦！"
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
            "既然上了贼船，就做个快乐的海盗猫",
            "与其仰望星空，不如去抓那只蝴蝶",
            "哪怕是流浪猫，也有看夕阳的权利",
            "保持好奇心，是猫咪长寿的秘诀",
            "没有什么烦恼，是一个罐头解决不了的",
            "只要步履不停，小鱼干终将抵达",
            "现在的努力，是为了以后能躺平晒太阳"
        ]
        return random.choice(quotes)

    def get_random_fact(self):
        return random.choice(self.cat_facts)

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

    # ✅ 修复3：周报数据兼容旧格式
    def get_weekly_data(self):
        stats = []
        today = datetime.now().date()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            raw_data = self.data.get("daily_stats", {}).get(day_str, 0)

            if isinstance(raw_data, dict):
                count = raw_data.get("count", 0)
                minutes = raw_data.get("minutes", 0)
            else:
                count = raw_data
                minutes = count * self.data.get("focus_min", 25)

            stats.append({
                "date": day.strftime("%m-%d"),
                "count": count,
                "minutes": minutes,
                "full_date": day_str
            })
        return stats


# ==========================================
# 2. 界面层 (UI与交互)
# ==========================================
def main(page: ft.Page):
    page.window_width = 390
    page.window_height = 844
    page.title = "猫猫专注助手"
    page.theme_mode = ft.ThemeMode.LIGHT

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
    timer_running = False
    is_break_mode = False
    end_timestamp = 0
    total_duration = logic.data["focus_min"] * 60
    bgm_ui_enabled = True

    # 🎵 播放列表：kanong.mp3 是背景音
    bgm_playlist = [
        {"name": "卡农(专注)", "src": "assets/kanong.mp3"},
    ]
    current_bgm_index = 0
    SILENCE_SRC = "assets/silent.mp3"

    emojis = {
        "idle": ["( =ω=)..zzZ", "(=^･ω･^=)", "ฅ(ﾐ・ﻌ・ﾐ)ฅ", "( -ω-)", "₍ ᐢ. ̫ .ᐢ ₎"],
        "work": ["( * >ω<)p", "q(>ω< * )", "φ(．．;)", "(ง •̀_•́)ง", "(=`ω´=)"],
        "break": ["( ~ o ~ )~", "旦_(^O^ )", "(=^ ◡ ^=)", "☕(・ω・)", "🧴(舔毛中)"],
        "happy": ["(≧◡≦) ♡", "(=^･^=)♪", "(/ =ω=)/", "o(>ω<)o", "⸜( ˙˘˙)⸝"],
        "touch": ["(///ω///)", "(=ﾟωﾟ)ﾉ", "(/ω＼)", "Meow~"]
    }

    # 🔊 音频初始化 (✅ 映射确认)
    # 1. 闹钟(时间到) -> purr.mp3
    audio_alarm = flet_audio.Audio(src="assets/purr.mp3", autoplay=False)
    # 2. 背景音乐 -> kanong.mp3
    audio_bg = flet_audio.Audio(src=bgm_playlist[0]["src"], autoplay=False, release_mode="loop")
    # 3. 撸猫叫声 -> alarm.mp3
    audio_meow = flet_audio.Audio(src="assets/alarm.mp3", autoplay=False)

    page.overlay.extend([audio_alarm, audio_bg, audio_meow])

    # ---------------------------------------------------
    # 🌙 伪黑屏组件 (✅ 修复：隐藏导航栏)
    # ---------------------------------------------------
    dim_overlay = ft.Container(
        visible=False,
        bgcolor="black",
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column([
            ft.Icon(ft.Icons.NIGHTLIGHT_ROUND, color="white", size=40, opacity=0.3),
            ft.Text("\n正在省电保活中...\n点击屏幕唤醒", color="white", opacity=0.3, text_align="center")
        ], alignment="center", horizontal_alignment="center"),
        on_click=lambda e: toggle_dim_mode(False)
    )
    page.overlay.append(dim_overlay)

    def toggle_dim_mode(enable):
        if enable:
            if not timer_running:
                page.snack_bar = ft.SnackBar(ft.Text("先开始专注再熄屏喵~"), open=True)
                page.update()
                return
            dim_overlay.visible = True
            try:
                nav_bar.visible = False
            except:
                pass
            page.snack_bar = ft.SnackBar(ft.Text("🌙 已进入伪黑屏，请勿按电源键！"), open=True)
        else:
            dim_overlay.visible = False
            try:
                nav_bar.visible = True
            except:
                pass
        page.update()

    # ---------------------------------------------------
    # 音频控制逻辑
    # ---------------------------------------------------
    def update_bgm_playback():
        audio_bg.pause()
        if bgm_ui_enabled:
            audio_bg.src = bgm_playlist[current_bgm_index]["src"]
        else:
            audio_bg.src = SILENCE_SRC
        audio_bg.update()
        if timer_running:
            audio_bg.play()

    def trigger_vibration():
        try:
            vibrator.vibrate(2)
        except:
            pass

    def send_notification(title, message):
        try:
            notification.notify(title=title, message=message, app_name="猫猫专注", timeout=10)
        except:
            pass

    def toggle_bgm(e):
        nonlocal bgm_ui_enabled
        bgm_ui_enabled = not bgm_ui_enabled
        if bgm_ui_enabled:
            btn_bgm.icon = ft.Icons.MUSIC_NOTE
            btn_bgm.tooltip = "白噪音: 开启"
        else:
            btn_bgm.icon = ft.Icons.MUSIC_OFF
            btn_bgm.tooltip = "白噪音: 关闭 (静音保活中)"
        btn_bgm.update()
        update_bgm_playback()
        page.update()

    def next_bgm(e):
        nonlocal current_bgm_index
        if not bgm_ui_enabled:
            page.snack_bar = ft.SnackBar(ft.Text("先打开音乐喵~"), open=True)
            page.update()
            return
        current_bgm_index = (current_bgm_index + 1) % len(bgm_playlist)
        new_song = bgm_playlist[current_bgm_index]
        update_bgm_playback()
        page.snack_bar = ft.SnackBar(ft.Text(f"🎵 切换至: {new_song['name']} 🐾"), open=True)
        page.update()

    # 🔔 结束逻辑
    def finish_cycle():
        nonlocal timer_running, is_break_mode, total_duration

        if dim_overlay.visible:
            dim_overlay.visible = False
            try:
                nav_bar.visible = True
            except:
                pass
            page.update()

        try:
            audio_bg.pause()
        except:
            pass

        # 播放闹钟 (purr.mp3)
        try:
            audio_alarm.seek(0)
            page.update()
            audio_alarm.play()
        except:
            pass

        trigger_vibration()

        if not is_break_mode:
            logic.increment_tomato()
            txt_tomato_stats.value = f"今日渔获: {get_tomato_str()}"
            is_break_mode = True
            next_min = logic.data["break_min"]
            total_duration = next_min * 60
            txt_timer_title.value = f"☕ {next_min}分钟 舔毛时间"
            txt_timer.color = THEME["green"]
            ring_timer.color = THEME["green"]
            btn_start.text = "开始舔毛"
            btn_start.bgcolor = THEME["green"]
            btn_start.color = "white"
            btn_skip.visible = True

            # 休息时显示冷知识
            fact = logic.get_random_fact()
            txt_cat.value = random.choice(emojis["break"])

            dlg_fact = ft.AlertDialog(
                title=ft.Text("🐱 猫猫冷知识"),
                content=ft.Text(fact, size=16),
                bgcolor=THEME["comp_bg"]
            )
            page.open(dlg_fact)

            msg = "喵！捕猎完成！休息一下吧~"
            send_notification("专注完成", msg)
        else:
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
            page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
            send_notification("休息结束", msg)

        txt_timer.value = f"{next_min:02}:00"
        ring_timer.value = 1.0
        timer_running = False
        page.update()

    def handle_lifecycle_change(e):
        if timer_running:
            nonlocal end_timestamp
            now = time.time()
            remaining = int(end_timestamp - now)
            if e.data == "resumed" and remaining <= 0:
                finish_cycle()
                return
            if remaining < 0: remaining = 0
            txt_timer.value = f"{remaining // 60:02}:{remaining % 60:02}"
            if total_duration > 0:
                progress = remaining / total_duration
                ring_timer.value = progress
            page.update()

    page.on_app_lifecycle_state_change = handle_lifecycle_change

    def get_watermark():
        return ft.Container(
            content=ft.Text("Created by lian · 陪你一同努力\n科技服务于人民 · 也不要忘了喂猫", size=10,
                            color=THEME["fg"], opacity=0.5, text_align="center"),
            padding=ft.padding.only(top=10, bottom=5),
            alignment=ft.alignment.center
        )

    # ------------------ UI 组件 ------------------
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
            page.update()
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

    btn_bgm = ft.IconButton(
        icon=ft.Icons.MUSIC_NOTE,
        icon_color=THEME["fg"],
        icon_size=20,
        tooltip="白噪音",
        on_click=toggle_bgm
    )

    btn_next_bgm = ft.IconButton(
        icon=ft.Icons.SKIP_NEXT,
        icon_color=THEME["fg"],
        icon_size=20,
        tooltip="切歌",
        on_click=next_bgm
    )

    btn_dim = ft.IconButton(
        icon=ft.Icons.NIGHTLIGHT_ROUND,
        icon_color=THEME["fg"],
        icon_size=20,
        tooltip="伪黑屏(省电)",
        on_click=lambda e: toggle_dim_mode(True)
    )

    music_bar = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.MUSIC_NOTE, size=14, color=THEME["fg"]),
            ft.Text("背景音:", size=12, color=THEME["fg"]),
            btn_bgm,
            btn_next_bgm,
            ft.Container(width=10),
            btn_dim
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
        if success: txt_cat.value = random.choice(emojis["happy"])
        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
        page.update()

    btn_checkin.on_click = checkin_click
    refresh_checkin_ui()

    txt_days_label = ft.Text(f"距离{logic.data['target_name']}还剩", size=13, color="grey")
    txt_days_num = ft.Text(f"{logic.get_main_days_left()}", size=36, weight="bold", color=THEME["fg"],
                           font_family="Impact")
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
    txt_timer = ft.Text(f"{logic.data['focus_min']}:00", size=50, weight="bold", color=THEME["fg"],
                        font_family="Impact")

    RING_SIZE = 230
    RING_RADIUS = 115

    ring_timer = ft.ProgressRing(
        width=RING_SIZE,
        height=RING_SIZE,
        stroke_width=12,
        value=1.0,
        color=THEME["fg"],
        bgcolor=THEME["ring_bg"]
    )

    stack_timer_display = ft.Stack(
        controls=[
            ft.Container(
                width=RING_SIZE, height=RING_SIZE, border_radius=RING_RADIUS,
                bgcolor=THEME["white"],
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="#1A000000")
            ),
            ring_timer,
            ft.Container(
                content=ft.Column([
                    ft.Container(height=10),
                    txt_cat,
                    txt_timer
                ], alignment="center", horizontal_alignment="center", spacing=5),
                alignment=ft.alignment.center,
                width=RING_SIZE, height=RING_SIZE,
                border_radius=RING_RADIUS,
            )
        ],
        width=RING_SIZE, height=RING_SIZE
    )

    btn_start = ft.ElevatedButton(
        text="开始捕猎", width=130, height=45,
        style=ft.ButtonStyle(
            bgcolor=THEME["white"],
            color=THEME["fg"],
            shape=ft.RoundedRectangleBorder(radius=25),
            elevation=3
        )
    )

    def skip_break_e(e):
        nonlocal timer_running, is_break_mode, total_duration
        timer_running = False
        is_break_mode = False
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
        if logic.data["tomatoes"] > 6: t += "..."
        if logic.data["tomatoes"] == 0: t = "(空空如也)"
        return t

    txt_tomato_stats = ft.Text(f"今日渔获: {get_tomato_str()}", color=THEME["fg"], size=13)
    txt_slogan = ft.Text(logic.get_random_quote(), italic=True, text_align="center", color=THEME["fg"], size=11,
                         opacity=0.8)

    # ✅ 修复4：撸猫逻辑 - 直接点击就有声音
    def pet_the_cat(e):
        txt_cat.value = random.choice(emojis["touch"])
        txt_cat.color = THEME["orange"]
        txt_cat.update()
        trigger_vibration()

        try:
            # 尝试倒带播放
            audio_meow.pause()
            audio_meow.seek(0)
            audio_meow.update()
            audio_meow.play()
        except:
            # 失败则直接播放 (First-play protection)
            try:
                audio_meow.play()
            except:
                pass

        page.snack_bar = ft.SnackBar(ft.Text("喵！(蹭蹭)"), open=True, duration=1000)
        page.update()
        time.sleep(0.5)
        txt_cat.color = THEME["fg"]
        if not timer_running:
            txt_cat.value = random.choice(emojis["idle"])
        txt_cat.update()

    stack_timer_display.controls[2].on_click = pet_the_cat

    # ✅ 修复5：分享卡片使用累加时长
    def open_share_card(e):
        today_date = datetime.now().strftime("%Y年%m月%d日")
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]
        tomato_count = logic.data["tomatoes"]

        # 优先读取今日累加，否则估算
        focus_minutes = logic.data.get("today_minutes", tomato_count * logic.data["focus_min"])

        poster_content = ft.Container(bgcolor=THEME["card_bg"], padding=30, border_radius=20, width=300, height=450,
                                      border=ft.border.all(4, THEME["fg"]), content=ft.Column([
                ft.Row([ft.Text(f"{today_date} {weekday}", color="grey", size=14)], alignment="center"),
                ft.Divider(color=THEME["fg"], thickness=1), ft.Container(height=20),
                ft.Text("今日战绩", size=16, color=THEME["fg"]),
                ft.Text(f"{tomato_count}", size=80, weight="bold", color=THEME["fg"], font_family="Impact"),
                ft.Text(f"条小鱼干 ({focus_minutes}分钟)", size=14, color="grey"),
                ft.Container(height=20), ft.Text(random.choice(emojis["happy"]), size=40, color=THEME["fg"]),
                ft.Container(height=20), ft.Container(
                    content=ft.Text(txt_slogan.value, italic=True, text_align="center", color=THEME["fg"], size=14),
                    padding=10),
                ft.Container(expand=True), ft.Divider(color=THEME["fg"], thickness=1),
                ft.Row([ft.Icon(ft.Icons.PETS, color=THEME["fg"], size=20),
                        ft.Text("猫猫专注助手", weight="bold", color=THEME["fg"])], alignment="center")
            ], horizontal_alignment="center"))
        dlg_share = ft.AlertDialog(content=ft.Column([poster_content, ft.Container(height=10),
                                                      ft.Text("✨ 截图炫耀一下战绩 ✨", color="white", size=12,
                                                              text_align="center"),
                                                      ft.IconButton(icon="close", icon_color="white",
                                                                    on_click=lambda e: page.close(dlg_share))],
                                                     tight=True, horizontal_alignment="center"), bgcolor="transparent",
                                   modal=True)
        page.open(dlg_share)

    btn_share = ft.IconButton(icon="share", icon_color=THEME["fg"], tooltip="生成海报", on_click=open_share_card)

    def format_time(seconds):
        if seconds < 0: seconds = 0
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def timer_loop():
        nonlocal timer_running, is_break_mode, end_timestamp, total_duration
        while timer_running:
            now = time.time()
            remaining = int(end_timestamp - now)
            if remaining <= 0:
                page.run_task(finish_cycle_wrapper)
                break
            txt_timer.value = format_time(remaining)
            if total_duration > 0:
                ratio = remaining / total_duration
                if ratio < 0: ratio = 0
                if ratio > 1: ratio = 1
                ring_timer.value = ratio
            page.update()
            time.sleep(0.1)

    async def finish_cycle_wrapper():
        finish_cycle()

    def toggle_timer(e):
        nonlocal timer_running, end_timestamp, total_duration
        if not timer_running:
            timer_running = True
            btn_start.text = "爪下留情(暂停)"
            txt_cat.value = random.choice(emojis["work"])
            update_bgm_playback()

            try:
                current_display = txt_timer.value.split(":")
                mins = int(current_display[0])
                secs = int(current_display[1])
                current_secs = mins * 60 + secs
            except:
                current_secs = logic.data["focus_min"] * 60

            if not is_break_mode and current_secs == logic.data["focus_min"] * 60:
                total_duration = current_secs
            elif is_break_mode and current_secs == logic.data["break_min"] * 60:
                total_duration = current_secs

            end_timestamp = time.time() + current_secs
            threading.Thread(target=timer_loop, daemon=True).start()
        else:
            timer_running = False
            btn_start.text = "继续捕猎"
            txt_cat.value = random.choice(emojis["idle"])
            try:
                audio_bg.pause()
            except:
                pass

        page.update()

    btn_start.on_click = toggle_timer

    # ✅ 修复6：UI遮挡修复 (Top Padding 60)
    view_home = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=60, bottom=160),
        content=ft.Column([
            ft.Row([
                weather_pill,
                ft.Container(expand=True),
                btn_checkin
            ], alignment="spaceBetween"),
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
                content=ft.Row([txt_tomato_stats, ft.Container(width=10), btn_share],
                               alignment="center", vertical_alignment="center"),
                bgcolor=THEME["comp_bg"],
                padding=5,
                border_radius=10
            ),
            ft.Container(height=10),
            txt_slogan,
            get_watermark(),
            ft.Container(height=30)
        ], horizontal_alignment="center", scroll="auto")
    )

    def show_history_e(e):
        hist_text = "\n".join(reversed(logic.data["history"][-20:]))
        if not hist_text: hist_text = "日记本被老鼠偷走了(空的)..."
        dlg = ft.AlertDialog(title=ft.Text("猫猫日记 🐾"),
                             content=ft.Container(content=ft.Text(hist_text, size=12, selectable=True), height=300,
                                                  width=300),
                             actions=[ft.TextButton("关上日记", on_click=lambda e: page.close(dlg))],
                             bgcolor=THEME["comp_bg"])
        page.open(dlg)

    lv_events = ft.Column(spacing=10)

    def render_events():
        lv_events.controls.clear()
        if not logic.data.get("countdowns"): return
        for i, item in enumerate(logic.data["countdowns"]):
            title = item["title"]
            date_str = item["date"]
            days = logic.calculate_days(date_str)
            day_color = THEME["red"] if days < 0 else THEME["fg"]
            day_text = f"{days} 天" if days >= 0 else f"过期 {-days} 天"
            card = ft.Container(
                bgcolor=THEME["white"],
                padding=15,
                border_radius=10,
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
        logic.remove_countdown_event(index);
        render_events()

    dlg_event_title = ft.TextField(label="猎物名称(目标)", color=THEME["fg"])
    dlg_event_date = ft.TextField(label="狩猎日期 (YYYY-MM-DD)", color=THEME["fg"])

    def save_new_event(e):
        if logic.add_countdown_event(dlg_event_title.value, dlg_event_date.value):
            page.close(dlg_add_event);
            render_events();
            dlg_event_title.value = "";
            dlg_event_date.value = "";
            page.snack_bar = ft.SnackBar(ft.Text("喵！新目标锁定！"), open=True)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("日期写错啦(挠头)"), open=True)
        page.update()

    dlg_add_event = ft.AlertDialog(title=ft.Text("添加倒计时"),
                                   content=ft.Column([dlg_event_title, dlg_event_date], height=150),
                                   actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg_add_event)),
                                            ft.TextButton("锁定目标", on_click=save_new_event)],
                                   bgcolor=THEME["comp_bg"])

    def open_add_event_dialog(e):
        if not dlg_event_date.value: dlg_event_date.value = datetime.now().strftime("%Y-%m-%d")
        page.open(dlg_add_event)

    priority_map = {"red": THEME["red"], "orange": THEME["orange"], "green": THEME["green"]}
    current_priority = "green"

    def set_priority(color):
        nonlocal current_priority
        current_priority = color
        for btn in priority_btns.controls:
            btn.icon = ft.Icons.CIRCLE_OUTLINED
            if btn.data == color:
                btn.icon = ft.Icons.CIRCLE
        page.update()

    priority_btns = ft.Row([
        ft.IconButton(icon=ft.Icons.CIRCLE_OUTLINED, icon_color=THEME["red"], data="red", tooltip="紧急",
                      on_click=lambda e: set_priority("red")),
        ft.IconButton(icon=ft.Icons.CIRCLE_OUTLINED, icon_color=THEME["orange"], data="orange", tooltip="重要",
                      on_click=lambda e: set_priority("orange")),
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color=THEME["green"], data="green", tooltip="日常",
                      on_click=lambda e: set_priority("green"))
    ], spacing=0)

    lv_tasks = ft.ListView(expand=True, spacing=5)
    txt_input_task = ft.TextField(
        hint_text="输入待办...",
        expand=True,
        bgcolor=THEME["white"],
        color=THEME["fg"],
        border_radius=10,
        border_color="transparent",
        text_size=14,
        content_padding=15
    )

    empty_state = ft.Container(content=ft.Column(
        [ft.Text("( =ω=)..zzZ", size=40, color="grey"), ft.Text("暂无任务，去晒太阳吧~ ☀️", color="grey")],
        horizontal_alignment="center", alignment=ft.MainAxisAlignment.CENTER), alignment=ft.alignment.center,
        padding=40)

    def render_tasks():
        lv_tasks.controls.clear()
        if not logic.data["tasks"]:
            lv_tasks.controls.append(empty_state)
        else:
            for i, task_item in enumerate(logic.data["tasks"]):
                if isinstance(task_item, dict):
                    text = task_item["text"]
                    prio = task_item.get("priority", "green")
                else:
                    text = task_item
                    prio = "green"

                p_icon = ft.Icon(ft.Icons.CIRCLE, size=12, color=priority_map.get(prio, THEME["green"]))
                display_content = [p_icon, ft.Text(text, size=14, color=THEME["fg"], expand=True)]
                if prio == "red":
                    display_content.insert(1, ft.Text("🔥", size=12))

                lv_tasks.controls.append(
                    ft.Container(
                        bgcolor=THEME["comp_bg"],
                        padding=12,
                        border_radius=8,
                        content=ft.Row([
                            ft.Row(display_content, expand=True, spacing=10),
                            ft.IconButton(icon="delete_outline", icon_color=THEME["fg"], icon_size=20,
                                          on_click=lambda e, idx=i: delete_task(idx))
                        ])
                    )
                )
        page.update()

    def add_task_e(e):
        if txt_input_task.value:
            logic.add_task(txt_input_task.value, current_priority)
            txt_input_task.value = ""
            render_tasks()

    def delete_task(idx):
        logic.remove_task(idx);
        render_tasks()

    render_events();
    render_tasks()

    # ✅ 修复7：容器 Padding 修正
    view_todo = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=60, bottom=160),
        content=ft.Column([
            ft.Row([
                ft.Text("鱼干清单 🐟", size=24, weight="bold", color=THEME["fg"]),
                ft.Row([
                    ft.IconButton(icon="history", icon_color=THEME["fg"], tooltip="查看历史", on_click=show_history_e),
                    ft.IconButton(icon="alarm_add", icon_color=THEME["fg"], tooltip="添加倒计时",
                                  on_click=open_add_event_dialog)
                ])
            ], alignment="space_between"),
            lv_events,
            ft.Divider(color=THEME["fg"], thickness=1, height=30),
            ft.Container(content=lv_tasks, expand=True, bgcolor=THEME["bg"]),
            ft.Container(content=ft.Row([ft.Text("重要程度:", size=12, color="grey"), priority_btns], alignment="end")),
            ft.Row(
                [txt_input_task,
                 ft.IconButton("add_circle", icon_color=THEME["fg"], icon_size=40, on_click=add_task_e)]),
            get_watermark(),
            ft.Container(height=30)
        ]))

    def create_input(label, val):
        return ft.TextField(
            label=label, value=val,
            label_style=ft.TextStyle(color=THEME["fg"]),
            color=THEME["fg"],
            bgcolor=THEME["white"],
            border_radius=10,
            border_color="transparent",
            cursor_color=THEME["fg"]
        )

    input_name = create_input("猎物名称", logic.data["target_name"])
    input_date = create_input("狩猎日期", logic.data["target_date"])
    input_city = create_input("地盘(城市)", logic.data.get("city", "郑州"))
    input_focus = create_input("捕猎时长(分)", str(logic.data["focus_min"]))
    input_break = create_input("舔毛时长(分)", str(logic.data["break_min"]))

    def clear_stats_e(e):
        logic.clear_daily_stats();
        txt_tomato_stats.value = "今日渔获: (空空如也)";
        page.snack_bar = ft.SnackBar(ft.Text("已清空，一切归零喵"), open=True);
        page.update()

    def save_settings(e):
        logic.update_settings(input_name.value, input_date.value, input_city.value, input_focus.value,
                              input_break.value)
        txt_days_label.value = f"距离{input_name.value}还剩"
        txt_days_num.value = f"{logic.get_main_days_left()}"
        if not timer_running and not is_break_mode:
            try:
                mins = int(logic.data["focus_min"])
            except:
                mins = 25
            txt_timer.value = f"{mins:02}:00"
            nonlocal total_duration
            total_duration = mins * 60
            ring_timer.value = 1.0
        txt_weather.value = "刷新中...";
        page.snack_bar = ft.SnackBar(ft.Text("喵！设置保存成功！"), open=True);
        page.update()

    # ✅ 修复8：周报显示时长 Tooltip
    def show_weekly_report(e):
        stats = logic.get_weekly_data()
        chart_groups = []
        for i, day in enumerate(stats):
            count = day["count"]
            minutes = day["minutes"]
            bar_color = THEME["fg"] if count > 0 else "grey"
            tooltip = f"{day['full_date']}: {count}条鱼 ({minutes}分钟)"
            chart_groups.append(
                ft.BarChartGroup(
                    x=i,
                    bar_rods=[ft.BarChartRod(from_y=0, to_y=count, width=16, color=bar_color, tooltip=tooltip,
                                             border_radius=4)]
                )
            )

        bottom_axis = ft.ChartAxis(
            labels=[ft.ChartAxisLabel(value=i, label=ft.Text(d["date"], size=10, color="grey")) for i, d in
                    enumerate(stats)]
        )

        chart = ft.BarChart(
            bar_groups=chart_groups,
            border=ft.border.all(1, "transparent"),
            left_axis=ft.ChartAxis(labels_size=0, show_labels=False),
            bottom_axis=bottom_axis,
            height=200,
            tooltip_bgcolor=THEME["comp_bg"],
            max_y=max([x["count"] for x in stats], default=5) + 2
        )

        content = ft.Column([
            ft.Text("📊 近7天狩猎周报", size=18, weight="bold", color=THEME["fg"]),
            ft.Container(height=20),
            chart,
            ft.Container(height=10),
            ft.Text("加油！多抓小鱼干！", size=12, color="grey", italic=True)
        ], horizontal_alignment="center")

        dlg_chart = ft.AlertDialog(content=ft.Container(content=content, height=300, width=350, padding=10),
                                   bgcolor="white")
        page.open(dlg_chart)

    btn_report = ft.ElevatedButton("📊 查看狩猎周报", on_click=show_weekly_report, bgcolor=THEME["comp_bg"],
                                   color=THEME["fg"], width=390, elevation=0)

    btn_history = ft.ElevatedButton("📜 翻看日记本", on_click=show_history_e, bgcolor=THEME["white"],
                                    color=THEME["fg"], width=390, elevation=2)
    btn_clear = ft.TextButton("🗑️ 倒掉今日猫粮(清空数据)", on_click=clear_stats_e,
                              style=ft.ButtonStyle(color=THEME["fg"]))

    view_settings = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=60, bottom=160),
        content=ft.Column([
            ft.Text("猫窝设置 ⚙️", size=24, weight="bold", color=THEME["fg"]),
            ft.Container(height=10), input_name, input_date, input_city, input_focus, input_break,
            ft.Container(height=10),
            ft.ElevatedButton("保存设置喵", on_click=save_settings, bgcolor=THEME["white"], color=THEME["fg"],
                              width=120,
                              elevation=2),
            ft.Divider(color=THEME["fg"]),
            btn_report,
            ft.Container(height=5),
            btn_history,
            ft.Container(height=20),
            ft.Container(content=btn_clear, alignment=ft.alignment.center),
            get_watermark(),
            ft.Container(height=30)
        ], scroll="auto"))

    def nav_change(e):
        idx = e.control.selected_index;
        page.controls.clear()
        if idx == 0:
            page.add(view_home)
        elif idx == 1:
            page.add(view_todo)
        elif idx == 2:
            page.add(view_settings)
        page.add(nav_bar);
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

    page.add(view_home);
    page.add(nav_bar);

    threading.Thread(target=weather_loop_thread, daemon=True).start()


ft.app(target=main)