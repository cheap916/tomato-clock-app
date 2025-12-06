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
# 1. 逻辑层 (保持不变)
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
            self.data["countdowns"].pop(index)
            self.save_data()

    def increment_tomato(self):
        self.data["tomatoes"] += 1
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data.get("daily_stats", {}):
            self.data["daily_stats"][today] = 0
        self.data["daily_stats"][today] += 1
        time_str = datetime.now().strftime("%H:%M")
        self.data["history"].append(f"[{time_str}] 捕获一只番茄 🍅")
        self.save_data()
        return self.data["tomatoes"]

    def clear_daily_stats(self):
        self.data["tomatoes"] = 0
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
            "没有什么烦恼\n是一个罐头解决不了的", "只要步履不停\n小鱼干终将抵达",
            "现在的努力\n是为了以后能躺平晒太阳", "关关难过关关过\n前路漫漫亦灿灿",
            "山顶的风景\n只有爬上去的人才能看见", "既然上了贼船\n就做个快乐的海盗猫"
        ]
        return random.choice(quotes)

    def fetch_weather(self):
        city = self.data.get("city", "郑州")
        try:
            url = f"https://wttr.in/{city}?format=%C+%t&lang=zh&_={int(time.time())}"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, timeout=5, headers=headers)
            if res.status_code == 200:
                return f"{city} {res.text.strip()}"
            return f"{city} 天气未知"
        except:
            return "气象喵正在赶路..."

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
# 2. 界面层 (双播放器稳健版)
# ==========================================
def main(page: ft.Page):
    page.window_width = 390
    page.window_height = 844
    page.title = "猫猫专注"
    page.theme_mode = ft.ThemeMode.LIGHT

    # 🎨 配色
    THEME = {
        "bg": "#FFCCCC", "fg": "#D24D57", "comp_bg": "#FFF0E6",
        "green": "#4CAF50", "white": "#FFFFFF", "red": "#FF5252",
        "orange": "#FF9800", "ring_bg": "#FFEEEE", "card_bg": "#FFFFFF"
    }
    page.bgcolor = THEME["bg"]
    page.padding = 0
    page.keep_screen_on = True

    logic = StudyLogic()
    timer_running = False
    is_break_mode = False
    end_timestamp = 0
    total_duration = logic.data["focus_min"] * 60
    bgm_enabled = False

    # 🎵 播放列表 (只留你有的)
    bgm_playlist = [{"name": "卡农", "src": "kanong.mp3"}]
    current_bgm_index = 0

    emojis = {
        "idle": ["( =ω=)..zzZ", "( -ω-)", "₍ ᐢ. ̫ .ᐢ ₎"],
        "work": ["(ง •̀_•́)ง", "φ(．．;)", "(=`ω´=)"],
        "break": ["( ~ o ~ )~", "旦_(^O^ )", "☕(・ω・)"],
        "happy": ["(≧◡≦) ♡", "(=^･^=)♪", "(/ =ω=)/"],
        "touch": ["(///ω///)", "(=ﾟωﾟ)ﾉ", "(/ω＼)"]
    }

    # ==========================
    # 🔊 核心音频组件 (双播放器策略)
    # ==========================

    # 1. 保活播放器 (背景音/静音)
    # 必须 loop 循环，一旦开始就不停止，直到时间到
    audio_bg = flet_audio.Audio(
        src="silent.mp3",
        autoplay=False,
        release_mode="loop"
    )

    # 2. 闹钟播放器 (独立)
    audio_alarm = flet_audio.Audio(
        src="alarm.mp3",
        autoplay=False
    )

    page.overlay.append(audio_bg)
    page.overlay.append(audio_alarm)

    # 系统功能
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

    # ==========================
    # 组件定义
    # ==========================
    txt_weather = ft.Text(value="...", size=12, color=THEME["fg"])
    weather_icon = ft.Icon(name=ft.Icons.PETS, size=14, color=THEME["fg"])

    def weather_loop_thread():
        while True:
            w_str = logic.fetch_weather()
            txt_weather.value = w_str
            page.update()
            time.sleep(300)

    weather_pill = ft.Container(
        content=ft.Row([weather_icon, txt_weather], spacing=3),
        bgcolor="#80FFF0E6", padding=ft.padding.symmetric(horizontal=10, vertical=5), border_radius=15
    )

    btn_bgm = ft.IconButton(
        icon=ft.Icons.MUSIC_OFF, icon_color="grey", icon_size=24,
        tooltip="点击切换: 静音保活 / 播放音乐"
    )

    btn_checkin = ft.ElevatedButton(
        text="按爪", bgcolor=THEME["white"], color=THEME["fg"], height=30,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=10)
    )

    txt_timer = ft.Text(f"{logic.data['focus_min']}:00", size=60, weight="bold", color=THEME["fg"],
                        font_family="Impact")
    txt_cat = ft.Text(random.choice(emojis["idle"]), size=24, color=THEME["fg"])
    ring_timer = ft.ProgressRing(width=260, height=260, stroke_width=18, value=1.0, color=THEME["fg"],
                                 bgcolor=THEME["ring_bg"])
    btn_start = ft.ElevatedButton(
        text="开始捕猎", width=160, height=50,
        style=ft.ButtonStyle(bgcolor=THEME["white"], color=THEME["fg"], elevation=2)
    )
    btn_skip = ft.ElevatedButton(
        text="不舔毛了", width=130, height=45, visible=False,
        style=ft.ButtonStyle(bgcolor=THEME["orange"], color="white", elevation=2)
    )
    txt_tomato_stats = ft.Text("今日渔获: (加载中)", color=THEME["fg"], size=14)
    txt_slogan = ft.Text(logic.get_random_quote(), italic=True, text_align="center", color=THEME["fg"], size=12,
                         opacity=0.7)

    # ==========================
    # 核心逻辑
    # ==========================

    def toggle_bgm(e):
        nonlocal bgm_enabled
        bgm_enabled = not bgm_enabled
        try:
            audio_bg.pause()
        except:
            pass

        if bgm_enabled:
            audio_bg.src = bgm_playlist[current_bgm_index]["src"]
            btn_bgm.icon = ft.Icons.MUSIC_NOTE
            btn_bgm.icon_color = THEME["fg"]
            page.snack_bar = ft.SnackBar(ft.Text(f"🎵 播放: {bgm_playlist[current_bgm_index]['name']}"), open=True)
        else:
            audio_bg.src = "silent.mp3"
            btn_bgm.icon = ft.Icons.MUSIC_OFF
            btn_bgm.icon_color = "grey"
            page.snack_bar = ft.SnackBar(ft.Text("🔇 静音保活中"), open=True)

        audio_bg.update()
        btn_bgm.update()

        # 计时中则恢复播放
        if timer_running:
            time.sleep(0.1)
            try:
                audio_bg.play()
            except:
                pass
        page.update()

    btn_bgm.on_click = toggle_bgm

    def refresh_checkin_ui():
        if logic.is_checked_in():
            btn_checkin.text = f"✅ ({logic.data['streak_days']})"
            btn_checkin.bgcolor = THEME["green"]
            btn_checkin.color = "white"
        else:
            btn_checkin.text = "🐾 按爪"
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

    def get_tomato_str():
        t = "🐟 " * min(logic.data["tomatoes"], 5)
        if logic.data["tomatoes"] > 5: t += "..."
        if logic.data["tomatoes"] == 0: t = "(空)"
        return t

    # ⏱️ 倒计时结束逻辑 (最稳版)
    def finish_cycle():
        nonlocal timer_running, is_break_mode, total_duration

        # 1. 暂停保活背景音
        try:
            audio_bg.pause()
        except:
            pass

        # 2. 播放独立闹钟
        try:
            audio_alarm.seek(0)
            audio_alarm.update()
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
            txt_cat.value = random.choice(emojis["break"])
            txt_timer.value = f"{next_min:02}:00"
            ring_timer.color = THEME["green"]
            ring_timer.value = 1.0
            btn_start.text = "开始休息"
            btn_start.bgcolor = THEME["green"]
            btn_start.color = "white"
            btn_skip.visible = True
            msg = "喵！捕猎完成！"
            send_notification("专注完成", msg)
        else:
            is_break_mode = False
            next_min = logic.data["focus_min"]
            total_duration = next_min * 60
            txt_cat.value = random.choice(emojis["idle"])
            txt_timer.value = f"{next_min:02}:00"
            ring_timer.color = THEME["fg"]
            ring_timer.value = 1.0
            btn_start.text = "开始捕猎"
            btn_start.bgcolor = THEME["white"]
            btn_start.color = THEME["fg"]
            btn_skip.visible = False
            msg = "休息结束！"
            send_notification("休息结束", msg)

        timer_running = False
        page.update()

    def timer_loop():
        nonlocal timer_running, is_break_mode, end_timestamp, total_duration
        while timer_running:
            now = time.time()
            remaining = int(end_timestamp - now)
            if remaining <= 0:
                finish_cycle()
                break
            mins = remaining // 60
            secs = remaining % 60
            txt_timer.value = f"{mins:02}:{secs:02}"
            if total_duration > 0:
                ratio = remaining / total_duration
                ring_timer.value = max(0, min(1, ratio))
            page.update()
            time.sleep(0.2)

    def toggle_timer(e):
        nonlocal timer_running, end_timestamp, total_duration
        if not timer_running:
            timer_running = True
            btn_start.text = "爪下留情(暂停)"
            txt_cat.value = random.choice(emojis["work"])

            # 【开始计时】启动保活播放器
            try:
                if bgm_enabled:
                    audio_bg.src = bgm_playlist[current_bgm_index]["src"]
                else:
                    audio_bg.src = "silent.mp3"
                audio_bg.update()
                time.sleep(0.1)
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

            end_timestamp = time.time() + current_secs
            threading.Thread(target=timer_loop, daemon=True).start()
        else:
            timer_running = False
            btn_start.text = "继续" if not is_break_mode else "继续休息"
            txt_cat.value = random.choice(emojis["idle"])
            # 【暂停计时】暂停保活播放器
            try:
                audio_bg.pause()
            except:
                pass
        page.update()

    btn_start.on_click = toggle_timer

    def skip_break(e):
        nonlocal timer_running, is_break_mode, total_duration
        timer_running = False
        is_break_mode = False
        next_min = logic.data["focus_min"]
        total_duration = next_min * 60
        txt_timer.value = f"{next_min:02}:00"
        ring_timer.color = THEME["fg"]
        ring_timer.value = 1.0
        btn_start.text = "开始捕猎"
        btn_start.bgcolor = THEME["white"]
        btn_start.color = THEME["fg"]
        btn_skip.visible = False
        txt_cat.value = random.choice(emojis["idle"])
        try:
            audio_bg.pause()
        except:
            pass
        page.update()

    btn_skip.on_click = skip_break

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

    # ==========================
    # 首页布局
    # ==========================
    top_bar = ft.Row([
        weather_pill,
        ft.Row([btn_bgm, ft.IconButton(icon=ft.Icons.SKIP_NEXT, icon_size=16, icon_color=THEME["fg"],
                                       on_click=lambda e: page.snack_bar.open(
                                           ft.SnackBar(ft.Text("切歌喵~"), open=True)) and page.update())], spacing=0),
        btn_checkin
    ], alignment="spaceBetween")

    txt_days_num = ft.Text(f"{logic.get_main_days_left()}", size=48, weight="bold", color=THEME["fg"],
                           font_family="Impact")
    countdown_card = ft.Container(
        content=ft.Column([
            ft.Text(f"距离{logic.data['target_name']}还剩", size=14, color="grey"),
            ft.Row(
                [txt_days_num, ft.Text("个罐头", size=14, color=THEME["fg"], weight="bold", offset=ft.Offset(0, 0.5))],
                alignment="center")
        ], horizontal_alignment="center", spacing=0),
        bgcolor=THEME["white"], padding=15, border_radius=15, width=320,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#1A000000")
    )

    timer_display = ft.Stack([
        ft.Container(width=260, height=260, bgcolor=THEME["white"], border_radius=130),
        ring_timer,
        ft.Container(
            content=ft.Column([ft.Container(height=10), txt_cat, txt_timer], alignment="center",
                              horizontal_alignment="center", spacing=10),
            width=260, height=260, alignment=ft.alignment.center
        )
    ], width=260, height=260)

    txt_tomato_stats.value = f"今日渔获: {get_tomato_str()}"
    bottom_card = ft.Container(
        content=ft.Row([txt_tomato_stats, ft.IconButton(icon=ft.Icons.SHARE, icon_color=THEME["fg"])],
                       alignment="spaceAround"),
        bgcolor=THEME["comp_bg"], padding=10, border_radius=12, width=320
    )

    def pet_cat(e):
        txt_cat.value = random.choice(emojis["touch"])
        trigger_vibration()
        page.update()
        time.sleep(0.5)
        txt_cat.value = random.choice(emojis["idle"] if not timer_running else emojis["work"])
        page.update()

    timer_display.controls[2].on_click = pet_cat

    view_home = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=10, bottom=50),
        content=ft.Column([
            top_bar, ft.Container(height=20), countdown_card, ft.Container(height=30),
            timer_display, ft.Container(height=30),
            ft.Column([btn_start, ft.Container(height=5), btn_skip], horizontal_alignment="center"),
            ft.Container(height=20), bottom_card, ft.Container(height=20),
            txt_slogan, ft.Container(height=10),
            ft.Text("Created by lian · 陪你一同努力", size=10, color=THEME["fg"], opacity=0.4)
        ], horizontal_alignment="center", scroll="auto")
    )

    # ==========================
    # 鱼干清单页
    # ==========================
    lv_events = ft.Column(spacing=10)

    def render_events():
        lv_events.controls.clear()
        if not logic.data.get("countdowns"): return
        for i, item in enumerate(logic.data["countdowns"]):
            days = logic.calculate_days(item["date"])
            day_color = THEME["red"] if days < 0 else THEME["fg"]
            day_text = f"{days} 天" if days >= 0 else f"过期 {-days} 天"
            card = ft.Container(
                bgcolor=THEME["white"], padding=15, border_radius=10,
                content=ft.Row([
                    ft.Column([ft.Text(item["title"], size=16, weight="bold", color=THEME["fg"]),
                               ft.Text(item["date"], size=12, color="grey")]),
                    ft.Column([ft.Text("剩余", size=10, color="grey"),
                               ft.Text(day_text, size=20, weight="bold", color=day_color)],
                              horizontal_alignment="center"),
                    ft.IconButton(icon="close", icon_size=18, icon_color="grey",
                                  on_click=lambda e, idx=i: (logic.remove_countdown_event(idx), render_events()))
                ], alignment="space_between")
            )
            lv_events.controls.append(card)
        page.update()

    dlg_event_title = ft.TextField(label="目标名称", color=THEME["fg"])
    dlg_event_date = ft.TextField(label="日期 (YYYY-MM-DD)", color=THEME["fg"])

    def save_new_event(e):
        if logic.add_countdown_event(dlg_event_title.value, dlg_event_date.value):
            page.close(dlg_add_event);
            render_events();
            dlg_event_title.value = "";
            dlg_event_date.value = ""
        else:
            page.snack_bar = ft.SnackBar(ft.Text("日期格式错啦"), open=True); page.update()

    dlg_add_event = ft.AlertDialog(title=ft.Text("添加倒计时"),
                                   content=ft.Column([dlg_event_title, dlg_event_date], height=150),
                                   actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg_add_event)),
                                            ft.TextButton("确定", on_click=save_new_event)])

    priority_map = {"red": THEME["red"], "orange": THEME["orange"], "green": THEME["green"]}
    current_priority = "green"

    def set_priority(color):
        nonlocal current_priority;
        current_priority = color
        for btn in priority_btns.controls:
            btn.icon = ft.Icons.CIRCLE_OUTLINED if btn.data != color else ft.Icons.CIRCLE
        page.update()

    priority_btns = ft.Row([
        ft.IconButton(icon=ft.Icons.CIRCLE_OUTLINED, icon_color=THEME["red"], data="red",
                      on_click=lambda e: set_priority("red")),
        ft.IconButton(icon=ft.Icons.CIRCLE_OUTLINED, icon_color=THEME["orange"], data="orange",
                      on_click=lambda e: set_priority("orange")),
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color=THEME["green"], data="green",
                      on_click=lambda e: set_priority("green"))
    ])

    lv_tasks = ft.ListView(expand=True, spacing=5)
    txt_input_task = ft.TextField(hint_text="输入待办...", expand=True, bgcolor=THEME["white"], border_radius=10,
                                  border_color="transparent")

    def render_tasks():
        lv_tasks.controls.clear()
        if not logic.data["tasks"]:
            lv_tasks.controls.append(
                ft.Container(content=ft.Text("暂无任务，去晒太阳吧~", color="grey"), alignment=ft.alignment.center,
                             padding=40))
        else:
            for i, task_item in enumerate(logic.data["tasks"]):
                text = task_item["text"] if isinstance(task_item, dict) else task_item
                prio = task_item.get("priority", "green") if isinstance(task_item, dict) else "green"
                lv_tasks.controls.append(ft.Container(
                    bgcolor=THEME["comp_bg"], padding=12, border_radius=8,
                    content=ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, size=12, color=priority_map.get(prio, THEME["green"])),
                        ft.Text(text, size=14, color=THEME["fg"], expand=True),
                        ft.IconButton(icon="delete_outline", icon_color=THEME["fg"], icon_size=20,
                                      on_click=lambda e, idx=i: (logic.remove_task(idx), render_tasks()))
                    ])
                ))
        page.update()

    render_events();
    render_tasks()

    view_todo = ft.Container(padding=ft.padding.only(left=20, right=20, top=20, bottom=160), content=ft.Column([
        ft.Row([ft.Text("鱼干清单", size=24, weight="bold", color=THEME["fg"]),
                ft.Row([ft.IconButton(icon="history", icon_color=THEME["fg"], on_click=lambda e: show_history()),
                        ft.IconButton(icon="alarm_add", icon_color=THEME["fg"],
                                      on_click=lambda e: page.open(dlg_add_event))])], alignment="space_between"),
        lv_events, ft.Divider(color=THEME["fg"], height=30),
        ft.Container(content=lv_tasks, expand=True, bgcolor=THEME["bg"]),
        ft.Container(content=ft.Row([ft.Text("优先级:", size=12, color="grey"), priority_btns], alignment="end")),
        ft.Row([txt_input_task, ft.IconButton("add_circle", icon_color=THEME["fg"], icon_size=40, on_click=lambda e: (
            logic.add_task(txt_input_task.value, current_priority), render_tasks(), txt_input_task.update()))])
    ]))

    # ==========================
    # 设置页
    # ==========================
    input_name = ft.TextField(label="猎物名称", value=logic.data["target_name"], color=THEME["fg"])
    input_date = ft.TextField(label="日期", value=logic.data["target_date"], color=THEME["fg"])
    input_city = ft.TextField(label="城市", value=logic.data.get("city", "郑州"), color=THEME["fg"])
    input_focus = ft.TextField(label="捕猎(分)", value=str(logic.data["focus_min"]), color=THEME["fg"])
    input_break = ft.TextField(label="舔毛(分)", value=str(logic.data["break_min"]), color=THEME["fg"])

    def show_history():
        hist = "\n".join(reversed(logic.data["history"][-20:])) or "日记本是空的..."
        dlg = ft.AlertDialog(title=ft.Text("猫猫日记"),
                             content=ft.Container(content=ft.Text(hist, size=12, selectable=True), height=300),
                             actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
        page.open(dlg)

    def show_chart(e):
        stats = logic.get_weekly_data()
        chart_groups = [ft.BarChartGroup(x=i, bar_rods=[
            ft.BarChartRod(from_y=0, to_y=d["count"], color=THEME["fg"], width=16, border_radius=4)]) for i, d in
                        enumerate(stats)]
        bottom_axis = ft.ChartAxis(
            labels=[ft.ChartAxisLabel(value=i, label=ft.Text(d["date"], size=10, color="grey")) for i, d in
                    enumerate(stats)])
        chart = ft.BarChart(bar_groups=chart_groups, border=ft.border.all(1, "transparent"),
                            left_axis=ft.ChartAxis(show_labels=False), bottom_axis=bottom_axis, height=200,
                            max_y=max([x["count"] for x in stats], default=5) + 2)
        dlg = ft.AlertDialog(content=ft.Container(content=ft.Column(
            [ft.Text("近7天周报", size=18, weight="bold", color=THEME["fg"]), ft.Container(height=20), chart],
            horizontal_alignment="center"), height=300, width=350, padding=10), bgcolor="white")
        page.open(dlg)

    def save_settings(e):
        logic.update_settings(input_name.value, input_date.value, input_city.value, input_focus.value,
                              input_break.value)
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
        txt_weather.value = "刷新中..."
        page.snack_bar = ft.SnackBar(ft.Text("设置已保存！"), open=True)
        page.update()

    view_settings = ft.Container(padding=ft.padding.only(left=20, right=20, top=20, bottom=160), content=ft.Column([
        ft.Text("猫窝设置", size=24, weight="bold", color=THEME["fg"]),
        ft.Container(height=10), input_name, input_date, input_city, input_focus, input_break,
        ft.Container(height=10),
        ft.ElevatedButton("保存设置", on_click=save_settings, bgcolor=THEME["white"], color=THEME["fg"]),
        ft.Divider(color=THEME["fg"]),
        ft.ElevatedButton("📊 查看周报", on_click=show_chart, bgcolor=THEME["comp_bg"], color=THEME["fg"], width=390),
        ft.Container(height=5),
        ft.ElevatedButton("📜 翻看日记", on_click=lambda e: show_history(), bgcolor=THEME["white"], color=THEME["fg"],
                          width=390),
        ft.Container(height=20),
        ft.TextButton("🗑️ 清空今日数据", on_click=lambda e: (logic.clear_daily_stats(), page.snack_bar.open(
            ft.SnackBar(ft.Text("已清空"), open=True)) or page.update()), style=ft.ButtonStyle(color=THEME["fg"]))
    ], scroll="auto"))

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
        on_change=nav_change, bgcolor=THEME["white"], indicator_color=THEME["bg"], selected_index=0, elevation=10
    )

    page.add(view_home)
    page.add(nav_bar)
    threading.Thread(target=weather_loop_thread, daemon=True).start()


ft.app(target=main)