import flet as ft
import flet_audio
import json
import os
import time
import random
import requests
import threading
from datetime import datetime, timedelta
from plyer import vibrator


# ==========================================
# 1. 逻辑层 (保持不变)
# ==========================================
class StudyLogic:
    def __init__(self):
        self.data_file = 'station_data.json'
        self.data = {
            "target_name": "任务",
            "target_date": "2026-12-21",
            "city": "郑州",
            "focus_min": 25,
            "break_min": 5,
            "tomatoes": 0,
            "tasks": [],
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

    def add_task(self, text):
        if text:
            today_str = datetime.now().strftime("%Y-%m-%d")
            count = 1
            for t in self.data["tasks"]:
                if t.startswith(today_str): count += 1
            decor = random.choice(["✨", "🐾", "📌", "🐟", "⭐"])
            self.data["tasks"].append(f"{today_str} {decor} {count}. {text}")
            self.save_data()

    def remove_task(self, index):
        if 0 <= index < len(self.data["tasks"]):
            task_content = self.data["tasks"][index]
            self.data["tasks"].pop(index)
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.data["history"].append(f"[{time_str}] ✅ 完成任务: {task_content}")
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
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.data["history"].append(f"[{time_str}] 🗑️ 移除倒计时: {event['title']}")
            self.save_data()

    def increment_tomato(self):
        self.data["tomatoes"] += 1
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.data["history"].append(f"[{time_str}] 抓到一个番茄 🍅")
        self.save_data()
        return self.data["tomatoes"]

    def clear_daily_stats(self):
        self.data["tomatoes"] = 0
        self.save_data()

    def check_in(self):
        today = datetime.now().strftime("%Y-%m-%d")
        last = self.data.get("last_checkin", "")
        if last == today: return False, "今天已经按过爪印啦 🐾"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last == yesterday:
            self.data["streak_days"] = self.data.get("streak_days", 0) + 1
        else:
            self.data["streak_days"] = 1
        self.data["last_checkin"] = today
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.data["history"].append(f"[{time_str}] 📅 完成每日签到")
        self.save_data()
        return True, f"喵！签到成功！连签 {self.data['streak_days']} 天 🎉"

    def is_checked_in(self):
        return self.data.get("last_checkin") == datetime.now().strftime("%Y-%m-%d")

    def get_random_quote(self):
        quotes = [
            "山顶的风景\n只有爬上去的猫才能看见",
            "关关难过关关过\n小鱼干会有的",
            "乾坤未定\n你我皆是黑马(猫)",
            "耐得住寂寞\n才能守得住罐头",
            "星光不问赶路喵",
            "只要步履不停\n我们就终将抵达"
        ]
        return random.choice(quotes)

    def fetch_weather(self):
        city = self.data.get("city", "郑州")
        try:
            url = f"https://wttr.in/{city}?format=%C+%t&lang=zh"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, timeout=10, headers=headers)
            if res.status_code == 200:
                current_time = datetime.now().strftime("%H:%M")
                return f"{city} {res.text.strip()} ({current_time})"
            return f"{city}: 信号飞到火星去了"
        except:
            return "网络被猫咬断了..."


# ==========================================
# 2. 界面层 (修复 colors 报错)
# ==========================================
def main(page: ft.Page):
    page.window_width = 390
    page.window_height = 844
    page.title = "任务助手"
    page.theme_mode = ft.ThemeMode.LIGHT

    # 🎨 配色方案
    THEME = {
        "bg": "#FFCCCC",  # 主背景粉色
        "fg": "#D24D57",  # 字体深红
        "comp_bg": "#FFF0E6",  # 组件背景(更浅的米色)
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

    emojis = {
        "idle": ["( =ω=)..zzZ", "(=^･ω･^=)", "ฅ(ﾐ・ﻌ・ﾐ)ฅ", "( -ω-)..zzZ"],
        "work": ["( * >ω<)p", "q(>ω< * )", "φ(．．;)", "(ง •̀_•́)ง"],
        "break": ["( ~ o ~ )~", "旦_(^O^ )", "(=^ ◡ ^=)", "☕(・ω・)"],
        "happy": ["(≧◡≦) ♡", "(=^･^=)♪", "(/ =ω=)/", "o(>ω<)o"]
    }

    audio_alarm = flet_audio.Audio(src="alarm.mp3", autoplay=False)
    page.overlay.append(audio_alarm)

    def trigger_vibration():
        try:
            vibrator.vibrate(1)
        except:
            pass

    def handle_lifecycle_change(e):
        if e.data == "resumed" and timer_running:
            nonlocal end_timestamp
            now = time.time()
            remaining = int(end_timestamp - now)
            if remaining < 0: remaining = 0
            txt_timer.value = f"{remaining // 60:02}:{remaining % 60:02}"
            if total_duration > 0:
                progress = remaining / total_duration
                ring_timer.value = progress
            page.update()

    page.on_app_lifecycle_state_change = handle_lifecycle_change

    def get_watermark():
        return ft.Container(
            content=ft.Text("Created by lian · 陪你一同努力\n科技不是高高在上 \n而是服务于人民", size=10,
                            color=THEME["fg"], opacity=0.5, text_align="center"),
            padding=ft.padding.only(top=20, bottom=10),
            alignment=ft.alignment.center
        )

    # ==========================
    # 首页组件
    # ==========================

    # 1. 天气胶囊
    txt_weather = ft.Text(value="正在召唤气象喵...", size=12, color=THEME["fg"])

    weather_pill = ft.Container(
        content=ft.Row([
            ft.Icon(name="cloud_queue", size=16, color=THEME["fg"]),
            txt_weather
        ], alignment="center", spacing=5),
        bgcolor="#80FFF0E6",  # 🟢 修复：直接使用带透明度的 Hex 颜色 (50% opacity of #FFF0E6)
        padding=ft.padding.symmetric(horizontal=15, vertical=5),
        border_radius=20,
    )

    def update_weather_thread():
        w_str = logic.fetch_weather()
        txt_weather.value = w_str
        page.update()

    # 2. 签到按钮
    btn_checkin = ft.ElevatedButton(
        text="📅 每日按爪",
        bgcolor=THEME["white"],
        color=THEME["fg"],
        elevation=2,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20))
    )

    def refresh_checkin_ui():
        if logic.is_checked_in():
            btn_checkin.text = f"✅ 已按爪 (连{logic.data['streak_days']}天)"
            btn_checkin.bgcolor = THEME["green"]
            btn_checkin.color = "white"
        else:
            btn_checkin.text = "📅 每日按爪"
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

    # 3. 倒计时卡片
    txt_days_label = ft.Text(f"距离{logic.data['target_name']}仅剩", size=14, color="grey")
    txt_days_num = ft.Text(f"{logic.get_main_days_left()}", size=40, weight="bold", color=THEME["fg"],
                           font_family="Impact")
    txt_days_unit = ft.Text("天", size=14, color=THEME["fg"], weight="bold", offset=ft.Offset(0, 0.6))

    countdown_card = ft.Container(
        content=ft.Column([
            txt_days_label,
            ft.Row([txt_days_num, txt_days_unit], alignment="center", vertical_alignment="end")
        ], horizontal_alignment="center", spacing=0),
        bgcolor=THEME["white"],
        padding=15,
        border_radius=15,
        width=300,
        # 🟢 修复：shadow color 使用 Hex 带透明度
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#1A000000")
    )

    # 4. 圆环时钟
    txt_timer_title = ft.Text("专注计时", size=18, weight="bold", color=THEME["fg"])
    txt_cat = ft.Text(random.choice(emojis["idle"]), size=20, color=THEME["fg"])
    txt_timer = ft.Text(f"{logic.data['focus_min']}:00", size=56, weight="bold", color=THEME["fg"],
                        font_family="Impact")

    ring_timer = ft.ProgressRing(
        width=260,
        height=260,
        stroke_width=12,
        value=1.0,
        color=THEME["fg"],
        bgcolor=THEME["ring_bg"]
    )

    stack_timer_display = ft.Stack(
        controls=[
            ft.Container(
                width=260, height=260, border_radius=130,
                bgcolor=THEME["white"],
                # 🟢 修复：shadow color 使用 Hex 带透明度
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
                width=260, height=260,
                border_radius=130,
            )
        ],
        width=260, height=260
    )

    # 5. 控制按钮
    btn_start = ft.ElevatedButton(
        text="开始专注", width=140, height=50,
        style=ft.ButtonStyle(
            bgcolor=THEME["white"],
            color=THEME["fg"],
            shape=ft.RoundedRectangleBorder(radius=25),
            elevation=4
        )
    )

    def skip_break_e(e):
        nonlocal timer_running, is_break_mode, total_duration
        timer_running = False
        is_break_mode = False
        next_min = logic.data["focus_min"]
        total_duration = next_min * 60
        txt_timer_title.value = "专注计时"
        txt_timer.color = THEME["fg"]
        ring_timer.color = THEME["fg"]
        ring_timer.value = 1.0
        txt_timer.value = f"{next_min:02}:00"
        btn_start.text = "开始专注"
        btn_start.bgcolor = THEME["white"]
        btn_skip.visible = False
        txt_cat.value = random.choice(emojis["idle"])
        page.snack_bar = ft.SnackBar(ft.Text("休息结束，准备开始专注！"), open=True)
        page.update()

    btn_skip = ft.ElevatedButton(
        text="跳过休息", width=140, height=50, visible=False, on_click=skip_break_e,
        style=ft.ButtonStyle(bgcolor=THEME["orange"], color="white", shape=ft.RoundedRectangleBorder(radius=25),
                             elevation=4)
    )

    # 6. 底部统计栏
    def get_tomato_str():
        t = "🍅 " * min(logic.data["tomatoes"], 6)
        if logic.data["tomatoes"] > 6: t += "..."
        if logic.data["tomatoes"] == 0: t = "(饿)"
        return t

    txt_tomato_stats = ft.Text(f"今日投喂: {get_tomato_str()}", color=THEME["fg"], size=14)
    txt_slogan = ft.Text(logic.get_random_quote(), italic=True, text_align="center", color=THEME["fg"], size=12,
                         opacity=0.8)

    def pet_the_cat(e):
        txt_cat.value = random.choice(emojis["happy"])
        txt_cat.update()
        page.snack_bar = ft.SnackBar(ft.Text("呼噜噜... 🐾"), open=True)
        page.update()

    stack_timer_display.controls[2].on_click = pet_the_cat

    # 分享卡片
    def open_share_card(e):
        today_date = datetime.now().strftime("%Y年%m月%d日")
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]
        tomato_count = logic.data["tomatoes"]
        focus_minutes = tomato_count * logic.data["focus_min"]
        poster_content = ft.Container(bgcolor=THEME["card_bg"], padding=30, border_radius=20, width=300, height=450,
                                      border=ft.border.all(4, THEME["fg"]), content=ft.Column([
                ft.Row([ft.Text(f"{today_date} {weekday}", color="grey", size=14)], alignment="center"),
                ft.Divider(color=THEME["fg"], thickness=1), ft.Container(height=20),
                ft.Text("今日专注", size=16, color=THEME["fg"]),
                ft.Text(f"{tomato_count}", size=80, weight="bold", color=THEME["fg"], font_family="Impact"),
                ft.Text(f"个番茄 ({focus_minutes}分钟)", size=14, color="grey"),
                ft.Container(height=20), ft.Text(random.choice(emojis["happy"]), size=40, color=THEME["fg"]),
                ft.Container(height=20), ft.Container(
                    content=ft.Text(txt_slogan.value, italic=True, text_align="center", color=THEME["fg"], size=14),
                    padding=10),
                ft.Container(expand=True), ft.Divider(color=THEME["fg"], thickness=1),
                ft.Row([ft.Icon("school", color=THEME["fg"], size=20),
                        ft.Text("上岸助手 APP", weight="bold", color=THEME["fg"])], alignment="center")
            ], horizontal_alignment="center"))
        dlg_share = ft.AlertDialog(content=ft.Column([poster_content, ft.Container(height=10),
                                                      ft.Text("✨ 截图分享给研友 ✨", color="white", size=12,
                                                              text_align="center"),
                                                      ft.IconButton(icon="close", icon_color="white",
                                                                    on_click=lambda e: page.close(dlg_share))],
                                                     tight=True, horizontal_alignment="center"), bgcolor="transparent",
                                   modal=True)
        page.open(dlg_share)

    btn_share = ft.IconButton(icon="share", icon_color=THEME["fg"], tooltip="生成打卡海报", on_click=open_share_card)

    def format_time(seconds):
        if seconds < 0: seconds = 0
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def timer_loop():
        nonlocal timer_running, is_break_mode, end_timestamp, total_duration
        while timer_running:
            now = time.time()
            remaining = int(end_timestamp - now)
            if remaining <= 0:
                remaining = 0
                txt_timer.value = format_time(remaining)
                ring_timer.value = 0.0
                page.update()
                break
            txt_timer.value = format_time(remaining)
            if total_duration > 0:
                ratio = remaining / total_duration
                if ratio < 0: ratio = 0
                if ratio > 1: ratio = 1
                ring_timer.value = ratio
            page.update()
            time.sleep(0.1)

        if remaining <= 0 and timer_running:
            timer_running = False
            try:
                audio_alarm.seek(0)
                page.update()
                audio_alarm.play()
            except:
                pass
            trigger_vibration()

            if not is_break_mode:
                logic.increment_tomato()
                txt_tomato_stats.value = f"今日投喂: {get_tomato_str()}"
                is_break_mode = True
                next_min = logic.data["break_min"]
                total_duration = next_min * 60
                txt_timer_title.value = f"☕ 喝茶时间 {next_min} 分钟"
                txt_timer.color = THEME["green"]
                txt_timer.value = f"{next_min:02}:00"
                ring_timer.color = THEME["green"]
                ring_timer.value = 1.0
                btn_start.text = "开始休息"
                btn_start.bgcolor = THEME["green"]
                btn_start.color = "white"
                btn_skip.visible = True
                txt_cat.value = random.choice(emojis["break"])
                page.snack_bar = ft.SnackBar(ft.Text("喵！专注完成！(嗡嗡嗡~)"), open=True)
            else:
                is_break_mode = False
                next_min = logic.data["focus_min"]
                total_duration = next_min * 60
                txt_timer_title.value = "专注计时"
                txt_timer.color = THEME["fg"]
                txt_timer.value = f"{next_min:02}:00"
                ring_timer.color = THEME["fg"]
                ring_timer.value = 1.0
                btn_start.text = "开始专注"
                btn_start.bgcolor = THEME["white"]
                btn_start.color = THEME["fg"]
                btn_skip.visible = False
                txt_cat.value = random.choice(emojis["idle"])
                page.snack_bar = ft.SnackBar(ft.Text("睡醒了，继续干活！(嗡嗡嗡~)"), open=True)
            page.update()

    def toggle_timer(e):
        nonlocal timer_running, end_timestamp, total_duration
        if not timer_running:
            timer_running = True
            btn_start.text = "暂停"
            txt_cat.value = random.choice(emojis["work"])
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
            btn_start.text = "继续"
            txt_cat.value = random.choice(emojis["idle"])
        page.update()

    btn_start.on_click = toggle_timer

    # === 布局组装 ===
    view_home = ft.Container(padding=20, content=ft.Column([
        ft.Container(height=20),
        weather_pill,
        ft.Container(height=15),
        btn_checkin,
        ft.Container(height=25),
        countdown_card,
        ft.Container(height=25),
        stack_timer_display,
        ft.Container(height=25),
        ft.Column([btn_start, ft.Container(height=5), btn_skip], horizontal_alignment="center"),
        ft.Container(height=10),
        ft.Row([txt_tomato_stats, btn_share], alignment="center"),
        ft.Container(height=20),
        txt_slogan,
        get_watermark()
    ], horizontal_alignment="center", scroll="auto"))

    # ==========================
    # 2. 清单页
    # ==========================
    def show_history_e(e):
        hist_text = "\n".join(reversed(logic.data["history"][-20:]))
        if not hist_text: hist_text = "猫猫日记本是空的..."
        dlg = ft.AlertDialog(title=ft.Text("猫猫日记 📝"),
                             content=ft.Container(content=ft.Text(hist_text, size=12, selectable=True), height=300,
                                                  width=300),
                             actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))],
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
            # 🟢 修复：shadow color 使用 Hex 带透明度
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
        logic.remove_countdown_event(index); render_events()

    dlg_event_title = ft.TextField(label="事项名称", color=THEME["fg"])
    dlg_event_date = ft.TextField(label="日期 (YYYY-MM-DD)", color=THEME["fg"])

    def save_new_event(e):
        if logic.add_countdown_event(dlg_event_title.value, dlg_event_date.value):
            page.close(dlg_add_event);
            render_events();
            dlg_event_title.value = "";
            dlg_event_date.value = "";
            page.snack_bar = ft.SnackBar(ft.Text("喵！新目标设定完毕！"), open=True)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("日期格式错啦"), open=True)
        page.update()

    dlg_add_event = ft.AlertDialog(title=ft.Text("添加倒计时"),
                                   content=ft.Column([dlg_event_title, dlg_event_date], height=150),
                                   actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg_add_event)),
                                            ft.TextButton("保存", on_click=save_new_event)], bgcolor=THEME["comp_bg"])

    def open_add_event_dialog(e):
        if not dlg_event_date.value: dlg_event_date.value = datetime.now().strftime("%Y-%m-%d")
        page.open(dlg_add_event)

    lv_tasks = ft.ListView(expand=True, spacing=5)
    txt_input_task = ft.TextField(
        hint_text="输入任务...",
        expand=True,
        bgcolor=THEME["white"],
        color=THEME["fg"],
        border_radius=10,
        border_color="transparent",
        text_size=14,
        content_padding=15
    )

    empty_state = ft.Container(content=ft.Column(
        [ft.Text("( =ω=)..zzZ", size=40, color="grey"), ft.Text("暂无任务，捉只蝴蝶吧~ 🦋", color="grey")],
        horizontal_alignment="center", alignment=ft.MainAxisAlignment.CENTER), alignment=ft.alignment.center,
                               padding=40)

    def render_tasks():
        lv_tasks.controls.clear()
        if not logic.data["tasks"]:
            lv_tasks.controls.append(empty_state)
        else:
            for i, task_str in enumerate(logic.data["tasks"]):
                lv_tasks.controls.append(
                    ft.Container(
                        bgcolor=THEME["comp_bg"],
                        padding=12,
                        border_radius=8,
                        content=ft.Row([
                            ft.Text(task_str, size=14, color=THEME["fg"], expand=True),
                            ft.IconButton(icon="delete_outline", icon_color=THEME["fg"], icon_size=20,
                                          on_click=lambda e, idx=i: delete_task(idx))
                        ])
                    )
                )
        page.update()

    def add_task_e(e):
        if txt_input_task.value: logic.add_task(txt_input_task.value); txt_input_task.value = ""; render_tasks()

    def delete_task(idx):
        logic.remove_task(idx); render_tasks()

    render_events();
    render_tasks()

    view_todo = ft.Container(padding=20, content=ft.Column([
        ft.Row([
            ft.Text("待办清单 🐾", size=24, weight="bold", color=THEME["fg"]),
            ft.Row([
                ft.IconButton(icon="history", icon_color=THEME["fg"], tooltip="查看历史", on_click=show_history_e),
                ft.IconButton(icon="alarm_add", icon_color=THEME["fg"], tooltip="添加倒计时",
                              on_click=open_add_event_dialog)
            ])
        ], alignment="space_between"),
        lv_events,
        ft.Divider(color=THEME["fg"], thickness=1, height=30),
        ft.Container(content=lv_tasks, expand=True, bgcolor=THEME["bg"]),
        ft.Row(
            [txt_input_task, ft.IconButton("add_circle", icon_color=THEME["fg"], icon_size=40, on_click=add_task_e)]),
        get_watermark()
    ]))

    # ==========================
    # 3. 设置页
    # ==========================
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

    input_name = create_input("目标名称", logic.data["target_name"])
    input_date = create_input("目标日期", logic.data["target_date"])
    input_city = create_input("城市", logic.data.get("city", "郑州"))
    input_focus = create_input("专注(分)", str(logic.data["focus_min"]))
    input_break = create_input("休息(分)", str(logic.data["break_min"]))

    def clear_stats_e(e):
        logic.clear_daily_stats(); txt_tomato_stats.value = "今日投喂: (饿)"; page.snack_bar = ft.SnackBar(
            ft.Text("已清空"), open=True); page.update()

    def save_settings(e):
        logic.update_settings(input_name.value, input_date.value, input_city.value, input_focus.value,
                              input_break.value)
        txt_days_label.value = f"距离{input_name.value}仅剩"
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
        threading.Thread(target=update_weather_thread, daemon=True).start()
        page.snack_bar = ft.SnackBar(ft.Text("喵！设置保存成功！"), open=True);
        page.update()

    btn_history = ft.ElevatedButton("📜 查看猫猫日记", on_click=show_history_e, bgcolor=THEME["white"],
                                    color=THEME["fg"], width=390, elevation=2)
    btn_clear = ft.TextButton("🗑️ 清空今日投喂", on_click=clear_stats_e, style=ft.ButtonStyle(color=THEME["fg"]))

    view_settings = ft.Container(padding=20, content=ft.Column([
        ft.Text("设置 ⚙️", size=24, weight="bold", color=THEME["fg"]),
        ft.Container(height=10), input_name, input_date, input_city, input_focus, input_break,
        ft.Container(height=10),
        ft.ElevatedButton("保存喵", on_click=save_settings, bgcolor=THEME["white"], color=THEME["fg"], width=120,
                          elevation=2),
        ft.Divider(color=THEME["fg"]), btn_history, ft.Container(height=20),
        ft.Container(content=btn_clear, alignment=ft.alignment.center),
        get_watermark()
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
            ft.NavigationBarDestination(icon="timer", label="专注"),
            ft.NavigationBarDestination(icon="list", label="清单"),
            ft.NavigationBarDestination(icon="settings", label="设置"),
        ],
        on_change=nav_change,
        bgcolor=THEME["white"],
        indicator_color=THEME["bg"],
        selected_index=0,
        elevation=10
    )

    page.add(view_home);
    page.add(nav_bar);
    threading.Thread(target=update_weather_thread, daemon=True).start()


ft.app(target=main)