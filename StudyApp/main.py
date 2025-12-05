import flet as ft
import flet_audio  # <--- 新增：引入音频库
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

    def get_days_left(self):
        try:
            target_str = self.data.get("target_date", "2025-12-20")
            target = datetime.strptime(target_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            days = (target - today).days
            return days
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
            self.data["tasks"].append(f"{today_str} // {count} // {text}")
            self.save_data()

    def remove_task(self, index):
        if 0 <= index < len(self.data["tasks"]):
            self.data["tasks"].pop(index)
            self.save_data()

    def increment_tomato(self):
        self.data["tomatoes"] += 1
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.data["history"].append(f"[{time_str}] 完成专注 🍅")
        self.save_data()
        return self.data["tomatoes"]

    def clear_daily_stats(self):
        self.data["tomatoes"] = 0
        self.save_data()

    def check_in(self):
        today = datetime.now().strftime("%Y-%m-%d")
        last = self.data.get("last_checkin", "")
        if last == today: return False, "今天已签到"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last == yesterday:
            self.data["streak_days"] = self.data.get("streak_days", 0) + 1
        else:
            self.data["streak_days"] = 1
        self.data["last_checkin"] = today
        self.save_data()
        return True, f"签到成功！连签 {self.data['streak_days']} 天"

    def is_checked_in(self):
        return self.data.get("last_checkin") == datetime.now().strftime("%Y-%m-%d")

    def get_random_quote(self):
        quotes = ["山顶的风景\n只有爬上去的人才能看见", "关关难过关关过\n前路漫漫亦灿灿", "乾坤未定\n你我皆是黑马",
                  "耐得住寂寞\n才能守得住繁华", "星光不问赶路人\n时光不负有心人",
                  "种一棵树最好的时间\n是十年前，其次是现在"]
        return random.choice(quotes)

    def fetch_weather(self):
        city = self.data.get("city", "郑州")
        try:
            url = f"http://wttr.in/{city}?format=%C+%t&lang=zh"
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                current_time = datetime.now().strftime("%H:%M")
                return f"{city}: {res.text.strip()} ({current_time})"
            return f"{city}: 获取失败"
        except:
            return "网络异常"


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
        "green": "#4CAF50", "white": "#FFFFFF"
    }
    page.bgcolor = THEME["bg"]
    page.padding = 0

    logic = StudyLogic()
    timer_running = False
    is_break_mode = False
    time_left = logic.data["focus_min"] * 60

    emojis = {
        "idle": ["( =ω=)..zzZ", "( -ω-)..zzZ"],
        "work": ["( * >ω<)p", "q(>ω< * )"],
        "break": ["( ~ o ~ )~", "旦_(^O^ )"],
    }

    # ==========================
    # 🎵 音频组件 (已修复警告)
    # ==========================
    # 使用 flet_audio.Audio 替代 ft.Audio
    audio_alarm = flet_audio.Audio(
        src="https://luan.xyz/files/audio/player_complete_01.mp3",
        autoplay=False
    )
    page.overlay.append(audio_alarm)

    # ==========================
    # 组件定义
    # ==========================

    txt_weather = ft.Text(value="定位中...", size=14, weight="bold", color=THEME["fg"])

    def update_weather_thread():
        w_str = logic.fetch_weather()
        txt_weather.value = w_str
        page.update()

    btn_checkin = ft.ElevatedButton(text="📅 每日签到", bgcolor=THEME["comp_bg"], color=THEME["fg"], width=160,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)))

    def refresh_checkin_ui():
        if logic.is_checked_in():
            btn_checkin.text = f"✅ 已签到 (连{logic.data['streak_days']}天)"
            btn_checkin.bgcolor = THEME["green"]
            btn_checkin.color = "white"
        else:
            btn_checkin.text = "📅 每日签到"
            btn_checkin.bgcolor = THEME["comp_bg"]
            btn_checkin.color = THEME["fg"]
        page.update()

    def checkin_click(e):
        success, msg = logic.check_in()
        refresh_checkin_ui()
        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
        page.update()

    btn_checkin.on_click = checkin_click
    refresh_checkin_ui()

    txt_days_label = ft.Text(f"距离{logic.data['target_name']}仅剩", size=16, color=THEME["fg"], weight="bold")
    txt_days_num = ft.Text(f"{logic.get_days_left()} 天", size=32, weight="bold", color=THEME["fg"],
                           font_family="Impact")
    container_countdown = ft.Column(
        [txt_days_label, txt_days_num, ft.Container(height=2, bgcolor=THEME["fg"], width=150)],
        horizontal_alignment="center", spacing=5)

    txt_timer_title = ft.Text("专注计时", size=20, weight="bold", color=THEME["fg"])
    txt_timer = ft.Text(f"{logic.data['focus_min']}:00", size=60, weight="bold", color=THEME["fg"],
                        font_family="Impact")
    btn_start = ft.ElevatedButton(text="开始计时", width=140, height=45,
                                  style=ft.ButtonStyle(bgcolor=THEME["comp_bg"], color=THEME["fg"],
                                                       shape=ft.RoundedRectangleBorder(radius=5), elevation=5))

    def get_tomato_str():
        t = "🍅 " * min(logic.data["tomatoes"], 8)
        if logic.data["tomatoes"] > 8: t += "..."
        if logic.data["tomatoes"] == 0: t = "(空)"
        return t

    txt_tomato_stats = ft.Text(f"今日专注: {get_tomato_str()}", color=THEME["fg"], size=14)
    txt_slogan = ft.Text(logic.get_random_quote(), italic=True, text_align="center", color=THEME["fg"], size=14)
    txt_cat = ft.Text(random.choice(emojis["idle"]), size=28, weight="bold", color=THEME["fg"])

    def format_time(seconds):
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def timer_loop():
        nonlocal time_left, timer_running, is_break_mode
        while timer_running and time_left > 0:
            time.sleep(1)
            time_left -= 1
            txt_timer.value = format_time(time_left)
            page.update()

        if time_left == 0 and timer_running:
            timer_running = False

            # 尝试播放声音
            try:
                audio_alarm.play()
            except:
                pass

            if not is_break_mode:
                logic.increment_tomato()
                txt_tomato_stats.value = f"今日专注: {get_tomato_str()}"
                is_break_mode = True
                time_left = logic.data["break_min"] * 60
                txt_timer_title.value = f"☕ 休息 {logic.data['break_min']} 分钟"
                txt_timer.color = THEME["green"]
                btn_start.text = "开始休息"
                txt_cat.value = random.choice(emojis["break"])
                page.snack_bar = ft.SnackBar(ft.Text("专注完成！休息一下"), open=True)
            else:
                is_break_mode = False
                time_left = logic.data["focus_min"] * 60
                txt_timer_title.value = "专注计时"
                txt_timer.color = THEME["fg"]
                btn_start.text = "开始计时"
                txt_cat.value = random.choice(emojis["idle"])
                page.snack_bar = ft.SnackBar(ft.Text("充电完毕，继续！"), open=True)
            txt_timer.value = format_time(time_left)
            page.update()

    def toggle_timer(e):
        nonlocal timer_running
        if not timer_running:
            timer_running = True
            btn_start.text = "暂停"
            txt_cat.value = random.choice(emojis["work"])
            threading.Thread(target=timer_loop, daemon=True).start()
        else:
            timer_running = False
            btn_start.text = "继续"
            txt_cat.value = random.choice(emojis["idle"])
        page.update()

    btn_start.on_click = toggle_timer

    view_home = ft.Container(padding=20, content=ft.Column([
        ft.Container(height=10), txt_weather, ft.Container(height=10), btn_checkin,
        ft.Container(height=20), container_countdown, ft.Container(height=20),
        txt_timer_title, txt_timer, btn_start, ft.Container(height=10),
        txt_tomato_stats, ft.Container(height=20), txt_slogan,
        ft.Container(height=30), txt_cat
    ], horizontal_alignment="center", scroll="auto"))

    lv_tasks = ft.ListView(expand=True, spacing=5)
    txt_input_task = ft.TextField(hint_text="输入任务(回车自动生成序号)...", expand=True, bgcolor=THEME["comp_bg"],
                                  color=THEME["fg"], border_color=THEME["fg"], text_size=14, content_padding=10)

    def render_tasks():
        lv_tasks.controls.clear()
        for i, task_str in enumerate(logic.data["tasks"]):
            lv_tasks.controls.append(ft.Container(bgcolor=THEME["comp_bg"], padding=10, content=ft.Row([
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

    render_tasks()

    view_todo = ft.Container(padding=20, content=ft.Column([
        ft.Text("待办清单", size=24, weight="bold", color=THEME["fg"]),
        ft.Container(content=lv_tasks, expand=True, bgcolor=THEME["bg"]),
        ft.Row([txt_input_task, ft.IconButton("add", icon_color=THEME["fg"], on_click=add_task_e)])
    ]))

    def create_input(label, val):
        return ft.TextField(label=label, value=val, label_style=ft.TextStyle(color=THEME["fg"]), color=THEME["fg"],
                            border_color=THEME["fg"], cursor_color=THEME["fg"])

    input_name = create_input("目标名称", logic.data["target_name"])
    input_date = create_input("目标日期 (YYYY-MM-DD)", logic.data["target_date"])
    input_city = create_input("城市", logic.data.get("city", "郑州"))
    input_focus = create_input("专注(分)", str(logic.data["focus_min"]))
    input_break = create_input("休息(分)", str(logic.data["break_min"]))

    def show_history_e(e):
        hist_text = "\n".join(reversed(logic.data["history"][-15:]))
        if not hist_text: hist_text = "暂无记录"
        dlg = ft.AlertDialog(title=ft.Text("最近记录"), content=ft.Text(hist_text, size=12, selectable=True),
                             actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))],
                             bgcolor=THEME["comp_bg"])
        page.open(dlg)

    def clear_stats_e(e):
        logic.clear_daily_stats()
        txt_tomato_stats.value = "今日专注: (空)"
        page.snack_bar = ft.SnackBar(ft.Text("今日统计已清空"), open=True)
        page.update()

    def save_settings(e):
        nonlocal time_left, is_break_mode
        logic.update_settings(input_name.value, input_date.value, input_city.value, input_focus.value,
                              input_break.value)
        txt_days_label.value = f"距离{input_name.value}仅剩"
        txt_days_num.value = f"{logic.get_days_left()} 天"

        if not timer_running and not is_break_mode:
            new_time = logic.data["focus_min"] * 60
            time_left = new_time
            txt_timer.value = format_time(new_time)

        txt_weather.value = "刷新中..."
        threading.Thread(target=update_weather_thread, daemon=True).start()
        page.snack_bar = ft.SnackBar(ft.Text("设置已保存并生效"), open=True)
        page.update()

    btn_history = ft.ElevatedButton("📜 查看历史记录", on_click=show_history_e, bgcolor=THEME["comp_bg"],
                                    color=THEME["fg"], width=390)
    btn_clear = ft.TextButton("🗑️ 清空今日统计", on_click=clear_stats_e, style=ft.ButtonStyle(color=THEME["fg"]))

    view_settings = ft.Container(padding=20, content=ft.Column([
        ft.Text("设置", size=24, weight="bold", color=THEME["fg"]),
        ft.Container(height=10), input_name, input_date, input_city, input_focus, input_break,
        ft.Container(height=10),
        ft.ElevatedButton("保存", on_click=save_settings, bgcolor=THEME["comp_bg"], color=THEME["fg"], width=100),
        ft.Divider(color=THEME["fg"]), btn_history, ft.Container(height=20),
        ft.Container(content=btn_clear, alignment=ft.alignment.center)
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