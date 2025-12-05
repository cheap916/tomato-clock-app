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
# 1. 逻辑层
# ==========================================
class StudyLogic:
    def __init__(self):
        self.data_file = 'station_data.json'
        self.data = {
            "target_name": "考研",
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
            self.data["tasks"].pop(index)
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
                return f"{city}: {res.text.strip()} ({current_time})"
            return f"{city}: 信号飞到火星去啦"
        except:
            return "网络被猫咬断了..."


# ==========================================
# 2. 界面层
# ==========================================
def main(page: ft.Page):
    page.window_width = 390
    page.window_height = 844
    page.title = "上岸助手"
    page.theme_mode = ft.ThemeMode.LIGHT

    THEME = {
        "bg": "#FFCCCC", "fg": "#D24D57", "comp_bg": "#FAEBD7",
        "green": "#4CAF50", "white": "#FFFFFF", "red": "#FF5252",
        "card_bg": "#FFF8F0"
    }
    page.bgcolor = THEME["bg"]
    page.padding = 0
    page.keep_screen_on = True

    logic = StudyLogic()
    timer_running = False
    is_break_mode = False
    end_timestamp = 0

    emojis = {
        "idle": ["( =ω=)..zzZ", "(=^･ω･^=)", "ฅ(ﾐ・ﻌ・ﾐ)ฅ", "( -ω-)..zzZ", "(=ﾟωﾟ)ﾉ"],
        "work": ["( * >ω<)p", "q(>ω< * )", "φ(．．;)", "(ง •̀_•́)ง"],
        "break": ["( ~ o ~ )~", "旦_(^O^ )", "(=^ ◡ ^=)", "☕(・ω・)"],
        "happy": ["(≧◡≦) ♡", "(=^･^=)♪", "(/ =ω=)/", "o(>ω<)o"]
    }

    # 🎵 音频
    audio_alarm = flet_audio.Audio(src="alarm.mp3", autoplay=False)
    page.overlay.append(audio_alarm)

    # ==========================
    # 🌟 统一水印组件生成器 (新)
    # ==========================
    def get_watermark():
        return ft.Container(
            content=ft.Text(
                "Created by lian  陪你一同完成\n"
                "科技不是高高在上 \n而是服务于人民",  # <--- 在这里修改你的名字
                size=10,
                color=THEME["fg"],
                opacity=0.5,  # 半透明
                text_align="center"
            ),
            padding=ft.padding.only(top=20, bottom=10),
            alignment=ft.alignment.center
        )

    # ==========================
    # 辅助函数
    # ==========================
    def update_weather_thread():
        w_str = logic.fetch_weather()
        txt_weather.value = w_str
        page.update()

    # ==========================
    # 1. 首页组件
    # ==========================
    txt_weather = ft.Text(value="正在召唤气象喵...", size=14, weight="bold", color=THEME["fg"])

    btn_checkin = ft.ElevatedButton(text="📅 每日按爪", bgcolor=THEME["comp_bg"], color=THEME["fg"], width=160,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)))

    def refresh_checkin_ui():
        if logic.is_checked_in():
            btn_checkin.text = f"✅ 已按爪 (连{logic.data['streak_days']}天)"
            btn_checkin.bgcolor = THEME["green"]
            btn_checkin.color = "white"
        else:
            btn_checkin.text = "📅 每日按爪"
            btn_checkin.bgcolor = THEME["comp_bg"]
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

    txt_days_label = ft.Text(f"距离{logic.data['target_name']}仅剩", size=16, color=THEME["fg"], weight="bold")
    txt_days_num = ft.Text(f"{logic.get_main_days_left()} 天", size=32, weight="bold", color=THEME["fg"],
                           font_family="Impact")
    container_countdown = ft.Column(
        [txt_days_label, txt_days_num, ft.Container(height=2, bgcolor=THEME["fg"], width=150)],
        horizontal_alignment="center", spacing=5)

    txt_timer_title = ft.Text("专注计时", size=20, weight="bold", color=THEME["fg"])
    txt_timer = ft.Text(f"{logic.data['focus_min']}:00", size=60, weight="bold", color=THEME["fg"],
                        font_family="Impact")
    btn_start = ft.ElevatedButton(text="开始专注", width=140, height=45,
                                  style=ft.ButtonStyle(bgcolor=THEME["comp_bg"], color=THEME["fg"],
                                                       shape=ft.RoundedRectangleBorder(radius=15), elevation=5))

    def get_tomato_str():
        t = "🍅 " * min(logic.data["tomatoes"], 6)
        if logic.data["tomatoes"] > 6: t += "..."
        if logic.data["tomatoes"] == 0: t = "(饿)"
        return t

    txt_tomato_stats = ft.Text(f"今日投喂: {get_tomato_str()}", color=THEME["fg"], size=14)
    txt_slogan = ft.Text(logic.get_random_quote(), italic=True, text_align="center", color=THEME["fg"], size=14)

    txt_cat = ft.Text(random.choice(emojis["idle"]), size=32, weight="bold", color=THEME["fg"])

    def pet_the_cat(e):
        txt_cat.value = random.choice(emojis["happy"])
        txt_cat.update()
        page.snack_bar = ft.SnackBar(ft.Text("呼噜噜... (被摸得很舒服) 🐾"), open=True)
        page.update()

    container_cat = ft.Container(content=txt_cat, on_click=pet_the_cat, padding=10, border_radius=10, ink=True,
                                 tooltip="摸摸头")

    # ==========================
    # ✨ 分享卡片
    # ==========================
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
                ft.Text("今日专注", size=16, color=THEME["fg"]),
                ft.Text(f"{tomato_count}", size=80, weight="bold", color=THEME["fg"], font_family="Impact"),
                ft.Text(f"个番茄 ({focus_minutes}分钟)", size=14, color="grey"),
                ft.Container(height=20),
                ft.Text(random.choice(emojis["happy"]), size=40, color=THEME["fg"]),
                ft.Container(height=20),
                ft.Container(
                    content=ft.Text(txt_slogan.value, italic=True, text_align="center", color=THEME["fg"], size=14),
                    padding=10),
                ft.Container(expand=True),
                ft.Divider(color=THEME["fg"], thickness=1),
                ft.Row([ft.Icon("school", color=THEME["fg"], size=20),
                        ft.Text("上岸助手 APP", weight="bold", color=THEME["fg"])], alignment="center")
            ], horizontal_alignment="center")
        )

        dlg_share = ft.AlertDialog(
            content=ft.Column([
                poster_content,
                ft.Container(height=10),
                ft.Text("✨ 截图分享给研友 ✨", color="white", size=12, text_align="center"),
                ft.IconButton(icon="close", icon_color="white", on_click=lambda e: page.close(dlg_share))
            ], tight=True, horizontal_alignment="center"),
            bgcolor="transparent", modal=True,
        )
        page.open(dlg_share)

    btn_share = ft.IconButton(icon="share", icon_color=THEME["fg"], tooltip="生成打卡海报", on_click=open_share_card)

    # ==========================
    # 计时器逻辑
    # ==========================
    def format_time(seconds):
        if seconds < 0: seconds = 0
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def timer_loop():
        nonlocal timer_running, is_break_mode, end_timestamp
        while timer_running:
            now = time.time()
            remaining = int(end_timestamp - now)
            if remaining <= 0:
                remaining = 0
                txt_timer.value = format_time(remaining)
                page.update()
                break
            txt_timer.value = format_time(remaining)
            page.update()
            time.sleep(0.5)

        if timer_running and remaining <= 0:
            timer_running = False
            try:
                audio_alarm.seek(0)
                page.update()
                audio_alarm.play()
            except:
                pass

            if not is_break_mode:
                logic.increment_tomato()
                txt_tomato_stats.value = f"今日投喂: {get_tomato_str()}"
                is_break_mode = True
                next_min = logic.data["break_min"]
                txt_timer_title.value = f"☕ 喝茶时间 {next_min} 分钟"
                txt_timer.color = THEME["green"]
                txt_timer.value = f"{next_min:02}:00"
                btn_start.text = "开始休息"
                txt_cat.value = random.choice(emojis["break"])
                page.snack_bar = ft.SnackBar(ft.Text("喵！专注完成！奖励小鱼干 🐟"), open=True)
            else:
                is_break_mode = False
                next_min = logic.data["focus_min"]
                txt_timer_title.value = "专注计时"
                txt_timer.color = THEME["fg"]
                txt_timer.value = f"{next_min:02}:00"
                btn_start.text = "开始专注"
                txt_cat.value = random.choice(emojis["idle"])
                page.snack_bar = ft.SnackBar(ft.Text("睡醒了，继续干活！"), open=True)
            page.update()

    def toggle_timer(e):
        nonlocal timer_running, end_timestamp
        if not timer_running:
            timer_running = True
            btn_start.text = "放弃/暂停"
            txt_cat.value = random.choice(emojis["work"])
            try:
                current_display = txt_timer.value.split(":")
                mins = int(current_display[0])
                secs = int(current_display[1])
                total_secs = mins * 60 + secs
            except:
                total_secs = logic.data["focus_min"] * 60
            end_timestamp = time.time() + total_secs
            threading.Thread(target=timer_loop, daemon=True).start()
        else:
            timer_running = False
            btn_start.text = "继续"
            txt_cat.value = random.choice(emojis["idle"])
        page.update()

    btn_start.on_click = toggle_timer

    # 首页布局
    view_home = ft.Container(padding=20, content=ft.Column([
        ft.Container(height=10), txt_weather, ft.Container(height=10), btn_checkin,
        ft.Container(height=20), container_countdown, ft.Container(height=20),
        txt_timer_title, txt_timer, btn_start, ft.Container(height=10),
        ft.Row([txt_tomato_stats, btn_share], alignment="center"),
        ft.Container(height=20), txt_slogan,
        ft.Container(height=30), container_cat,
        get_watermark()  # <--- 首页水印
    ], horizontal_alignment="center", scroll="auto"))

    # ==========================
    # 2. 清单页
    # ==========================
    lv_events = ft.Column(spacing=5)

    def render_events():
        lv_events.controls.clear()
        if not logic.data.get("countdowns"): return
        for i, item in enumerate(logic.data["countdowns"]):
            title = item["title"]
            date_str = item["date"]
            days = logic.calculate_days(date_str)
            day_color = THEME["red"] if days < 0 else THEME["fg"]
            day_text = f"{days} 天" if days >= 0 else f"过期 {-days} 天"
            card = ft.Container(bgcolor=THEME["comp_bg"], padding=10, border_radius=10, content=ft.Row([
                ft.Column([ft.Text(title, size=16, weight="bold", color=THEME["fg"]),
                           ft.Text(date_str, size=12, color="grey")], expand=True),
                ft.Column([ft.Text("剩余", size=10, color="grey"),
                           ft.Text(day_text, size=20, weight="bold", color=day_color)], horizontal_alignment="center"),
                ft.IconButton(icon="close", icon_size=16, icon_color="grey",
                              on_click=lambda e, idx=i: delete_event(idx))
            ], alignment="space_between"))
            lv_events.controls.append(card)
        page.update()

    def delete_event(index):
        logic.remove_countdown_event(index)
        render_events()

    dlg_event_title = ft.TextField(label="事项名称 (如: 抓老鼠比赛)", color=THEME["fg"])
    dlg_event_date = ft.TextField(label="日期 (YYYY-MM-DD)", color=THEME["fg"])

    def save_new_event(e):
        if logic.add_countdown_event(dlg_event_title.value, dlg_event_date.value):
            page.close(dlg_add_event)
            render_events()
            dlg_event_title.value = ""
            dlg_event_date.value = ""
            page.snack_bar = ft.SnackBar(ft.Text("喵！新目标设定完毕！"), open=True)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("日期格式错啦，猫猫看不懂"), open=True)
        page.update()

    dlg_add_event = ft.AlertDialog(title=ft.Text("添加倒计时"),
                                   content=ft.Column([dlg_event_title, dlg_event_date], height=150),
                                   actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg_add_event)),
                                            ft.TextButton("保存", on_click=save_new_event)], bgcolor=THEME["comp_bg"])

    def open_add_event_dialog(e):
        if not dlg_event_date.value: dlg_event_date.value = datetime.now().strftime("%Y-%m-%d")
        page.open(dlg_add_event)

    lv_tasks = ft.ListView(expand=True, spacing=5)
    txt_input_task = ft.TextField(hint_text="输入任务...", expand=True, bgcolor=THEME["comp_bg"], color=THEME["fg"],
                                  border_color=THEME["fg"], text_size=14, content_padding=10)

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
                    ft.Container(bgcolor=THEME["comp_bg"], padding=10, border_radius=5, content=ft.Row([
                        ft.Text(task_str, size=14, color=THEME["fg"], expand=True),
                        ft.IconButton(icon="delete_outline", icon_color=THEME["fg"], icon_size=20,
                                      on_click=lambda e, idx=i: delete_task(idx))
                    ])))
        page.update()

    def add_task_e(e):
        if txt_input_task.value:
            logic.add_task(txt_input_task.value)
            txt_input_task.value = ""
            render_tasks()

    def delete_task(idx):
        logic.remove_task(idx)
        render_tasks()

    render_events()
    render_tasks()

    # 清单页布局
    view_todo = ft.Container(padding=20, content=ft.Column([
        ft.Row([ft.Text("待办清单 🐾", size=24, weight="bold", color=THEME["fg"]),
                ft.IconButton(icon="alarm_add", icon_color=THEME["fg"], tooltip="添加倒计时",
                              on_click=open_add_event_dialog)], alignment="space_between"),
        lv_events, ft.Divider(color=THEME["fg"], thickness=1),
        ft.Container(content=lv_tasks, expand=True, bgcolor=THEME["bg"]),
        ft.Row([txt_input_task, ft.IconButton("add", icon_color=THEME["fg"], on_click=add_task_e)]),
        get_watermark()  # <--- 清单页水印
    ]))

    # ==========================
    # 3. 设置页
    # ==========================
    def create_input(label, val):
        return ft.TextField(label=label, value=val, label_style=ft.TextStyle(color=THEME["fg"]), color=THEME["fg"],
                            border_color=THEME["fg"], cursor_color=THEME["fg"])

    input_name = create_input("目标名称", logic.data["target_name"])
    input_date = create_input("目标日期", logic.data["target_date"])
    input_city = create_input("城市", logic.data.get("city", "郑州"))
    input_focus = create_input("专注(分)", str(logic.data["focus_min"]))
    input_break = create_input("休息(分)", str(logic.data["break_min"]))

    def show_history_e(e):
        hist_text = "\n".join(reversed(logic.data["history"][-15:]))
        if not hist_text: hist_text = "猫猫日记本是空的..."
        dlg = ft.AlertDialog(title=ft.Text("猫猫日记"), content=ft.Text(hist_text, size=12, selectable=True),
                             actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))],
                             bgcolor=THEME["comp_bg"])
        page.open(dlg)

    def clear_stats_e(e):
        logic.clear_daily_stats()
        txt_tomato_stats.value = "今日投喂: (饿)"
        page.snack_bar = ft.SnackBar(ft.Text("今日数据已清空，重头再来！"), open=True)
        page.update()

    def save_settings(e):
        logic.update_settings(input_name.value, input_date.value, input_city.value, input_focus.value,
                              input_break.value)
        txt_days_label.value = f"距离{input_name.value}仅剩"
        txt_days_num.value = f"{logic.get_main_days_left()} 天"
        if not timer_running and not is_break_mode:
            try:
                mins = int(logic.data["focus_min"])
            except:
                mins = 25
            txt_timer.value = f"{mins:02}:00"
        txt_weather.value = "刷新中..."
        threading.Thread(target=update_weather_thread, daemon=True).start()
        page.snack_bar = ft.SnackBar(ft.Text("喵！设置保存成功！"), open=True)
        page.update()

    btn_history = ft.ElevatedButton("📜 查看猫猫日记", on_click=show_history_e, bgcolor=THEME["comp_bg"],
                                    color=THEME["fg"], width=390)
    btn_clear = ft.TextButton("🗑️ 清空今日投喂", on_click=clear_stats_e, style=ft.ButtonStyle(color=THEME["fg"]))

    # 设置页布局
    view_settings = ft.Container(padding=20, content=ft.Column([
        ft.Text("设置 ⚙️", size=24, weight="bold", color=THEME["fg"]),
        ft.Container(height=10), input_name, input_date, input_city, input_focus, input_break,
        ft.Container(height=10),
        ft.ElevatedButton("保存喵", on_click=save_settings, bgcolor=THEME["comp_bg"], color=THEME["fg"], width=100),
        ft.Divider(color=THEME["fg"]), btn_history, ft.Container(height=20),
        ft.Container(content=btn_clear, alignment=ft.alignment.center),
        get_watermark()  # <--- 设置页水印
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

    nav_bar = ft.NavigationBar(destinations=[
        ft.NavigationBarDestination(icon="timer", label="专注"),
        ft.NavigationBarDestination(icon="list", label="清单"),
        ft.NavigationBarDestination(icon="settings", label="设置"),
    ], on_change=nav_change, bgcolor=THEME["comp_bg"], indicator_color=THEME["bg"], selected_index=0)

    page.add(view_home)
    page.add(nav_bar)
    threading.Thread(target=update_weather_thread, daemon=True).start()


ft.app(target=main)