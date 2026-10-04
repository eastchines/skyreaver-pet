# -*- coding: utf-8 -*-
"""
====================================================
  SkyReaver 桌面宠物助手（互动加强版）
====================================================
新增互动：
  1. 闲置绕圈：一段时间没按键，自动切回兽态，离开键盘位置，
     在窗口内绕圈走动（“离开键盘绕圈圈”）
  2. 饥饿计时：吃饱后 60 分钟会饿；饿了会弹出文字气泡“我要吃饭！”
  3. 投喂：右键宠物 → “投喂文件夹…”，选中一个文件夹让它“吃掉”，
     饥饿立即重置（再管 60 分钟）
  4. 保留原有功能：手跟按键、空格、输入法切换形象

运行环境：Windows + Python 3.8+，依赖 pip install pynput pywin32
====================================================
"""
import sys
import os
import time
import ctypes
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pynput import keyboard


def resource_path(relative_path):
    """打包成 exe 后也能正确找到图片资源"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ====================== 可调配置区 ======================
IMG_BEAST_BODY = resource_path("beast_body.png")
IMG_BEAST_HAND = resource_path("beast_hand.png")
IMG_GIRL_BODY  = resource_path("girl_body.png")
IMG_GIRL_HAND  = resource_path("girl_hand.png")

CANVAS_W = 780          # 窗口宽度（加大，给绕圈留空间）
CANVAS_H = 520          # 窗口高度

# 身体在“工作态”时的位置（画布左上角锚点）
BODY_ACTIVE_X, BODY_ACTIVE_Y = 180, 60

# 手悬空 / 连接点 / 键位（工作态用，坐标相对身体位置）
IDLE_HAND   = {"beast": (300, 90), "girl": (300, 90)}
KEY_POS = {
    "q": (140, 250), "w": (168, 252), "e": (196, 256), "r": (220, 259),
    "t": (244, 261), "y": (266, 261), "u": (288, 262),
    "a": (142, 282), "s": (165, 284), "d": (188, 286), "f": (212, 289),
    "g": (236, 290), "h": (258, 291), "j": (280, 291),
    "z": (146, 300), "x": (167, 302), "c": (191, 304), "v": (214, 305),
    "b": (236, 306), "n": (258, 307), "m": (280, 307),
    "space": (170, 322),
}

# 闲置判定：超过多少秒没按键盘 → 进入绕圈
IDLE_SECONDS = 10
# 绕圈矩形路径（身体左上角可到达的范围，画布坐标）
WALK_MIN_X, WALK_MIN_Y = 20, 30
WALK_MAX_X = CANVAS_W - 360
WALK_MAX_Y = CANVAS_H - 360
# 绕圈速度（每帧移动的像素）
WALK_SPEED = 2.0

# 饥饿周期（秒）：吃饱后多久会饿
HUNGRY_MINUTES = 60
HUNGRY_SECONDS = HUNGRY_MINUTES * 60

CN_LAYOUT = 0x0804      # 简体中文输入法
SMOOTH = 0.35           # 手移动平滑度
FRAME_MS = 20           # 主循环帧间隔
# ======================================================


class DesktopPet:
    def __init__(self, root):
        self.root = root
        self.root.title("SkyReaver 桌面助手")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.geometry(f"{CANVAS_W}x{CANVAS_H}+120+150")

        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H,
                                bg="black", highlightthickness=0)
        self.canvas.pack()

        # ---------- 状态 ----------
        self.mode = "beast"            # beast / girl
        self.state = "active"          # active(工作) / idle(绕圈)
        self.hungry = False            # 是否饥饿
        self.hungry_banner = None      # 饥饿气泡的 canvas 对象

        self.body_x, self.body_y = BODY_ACTIVE_X, BODY_ACTIVE_Y
        self.hand_x, self.hand_y = IDLE_HAND["beast"]
        self.hand_tx, self.hand_ty = IDLE_HAND["beast"]

        # 闲置 / 饥饿计时
        self.last_input = time.time()
        self.fed_time = time.time()    # 吃饱时间点（启动即视为吃饱）

        # 绕圈参数
        self.walk_phase = 0.0

        # ---------- 素材 ----------
        self.images = {}
        self._load_images()

        # 身体层（绘制层级在底层）
        self.body_id = self.canvas.create_image(self.body_x, self.body_y,
                                                image=self.images["body"], anchor="nw")
        # 手层（绘制在上层）
        self.hand_id = self.canvas.create_image(self.hand_x, self.hand_y,
                                                image=self.images["hand"])

        # ---------- 右键菜单（投喂 / 退出） ----------
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="投喂文件夹…", command=self.feed_folder)
        self.menu.add_command(label="立即吃饱（测试）", command=self.feed_now)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=root.destroy)
        self.canvas.bind("<Button-3>", self._pop_menu)

        # ---------- 线程 ----------
        self.listener = keyboard.Listener(on_press=self.on_press,
                                          on_release=self.on_release)
        self.listener.start()
        threading.Thread(target=self.watch_input_method, daemon=True).start()

        # ---------- 主循环 ----------
        self._tick()

    # ================= 素材 =================
    def _load_images(self):
        if self.mode == "beast":
            self.images["body"] = tk.PhotoImage(file=IMG_BEAST_BODY)
            self.images["hand"] = tk.PhotoImage(file=IMG_BEAST_HAND)
        else:
            self.images["body"] = tk.PhotoImage(file=IMG_GIRL_BODY)
            self.images["hand"] = tk.PhotoImage(file=IMG_GIRL_HAND)

    def switch_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self._load_images()
        self.canvas.itemconfig(self.body_id, image=self.images["body"])
        self.canvas.itemconfig(self.hand_id, image=self.images["hand"])

    # ================= 键盘 =================
    def on_press(self, key):
        self.last_input = time.time()
        if self.state == "idle":
            return  # 绕圈中不响应按键定位
        try:
            ch = key.char.lower()
            if ch in KEY_POS:
                self.hand_tx, self.hand_ty = KEY_POS[ch]
        except AttributeError:
            if key == keyboard.Key.space:
                self.hand_tx, self.hand_ty = KEY_POS["space"]

    def on_release(self, key):
        self.last_input = time.time()
        if self.state == "active":
            self.hand_tx, self.hand_ty = IDLE_HAND[self.mode]

    # ================= 输入法 =================
    def get_layout(self):
        return ctypes.windll.user32.GetKeyboardLayout(0) & 0xFFFF

    def watch_input_method(self):
        while True:
            if ctypes.windll.user32.GetKeyboardLayout(0) & 0xFFFF == CN_LAYOUT:
                self.switch_mode("girl")
            else:
                self.switch_mode("beast")
            threading.Event().wait(0.3)

    # ================= 投喂 =================
    def _pop_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def feed_folder(self):
        folder = filedialog.askdirectory(title="选择一个文件夹，让宠物吃掉")
        if not folder:
            return
        self._eat(f"已吃掉：{os.path.basename(folder)}")

    def feed_now(self):
        self._eat("吃饱啦！")

    def _eat(self, msg):
        self.fed_time = time.time()
        self.hungry = False
        self._show_banner(msg, 2.0)

    # ================= 主循环 =================
    def _tick(self):
        now = time.time()

        # ---- 1. 状态切换：闲置 → 绕圈 ----
        idle_now = (now - self.last_input) > IDLE_SECONDS
        if idle_now and self.state == "active":
            self.state = "idle"
            self.switch_mode("beast")        # 绕圈时固定用兽态
        elif not idle_now and self.state == "idle":
            self.state = "active"
            self.body_x, self.body_y = BODY_ACTIVE_X, BODY_ACTIVE_Y
            self.hand_tx, self.hand_ty = IDLE_HAND[self.mode]

        # ---- 2. 绕圈运动 ----
        if self.state == "idle":
            self.walk_phase += WALK_SPEED * FRAME_MS / 1000.0
            self.body_x, self.body_y = self._walk_pos(self.walk_phase)

        # ---- 3. 饥饿判定 ----
        if not self.hungry and (now - self.fed_time) > HUNGRY_SECONDS:
            self.hungry = True
            self._show_banner("我要吃饭！", None)   # 常驻提示

        # ---- 4. 手跟随 ----
        if self.state == "active":
            self.hand_x += (self.hand_tx - self.hand_x) * SMOOTH
            self.hand_y += (self.hand_ty - self.hand_y) * SMOOTH
        else:
            # 绕圈时手跟着身体走，停在身体右侧
            self.hand_x = self.body_x + 300
            self.hand_y = self.body_y + 90

        # ---- 绘制 ----
        self.canvas.coords(self.body_id, self.body_x, self.body_y)
        self.canvas.coords(self.hand_id, self.hand_x, self.hand_y)

        self.root.after(FRAME_MS, self._tick)

    def _walk_pos(self, phase):
        """沿窗口内侧矩形路径绕圈，返回身体左上角坐标"""
        w = WALK_MAX_X - WALK_MIN_X
        h = WALK_MAX_Y - WALK_MIN_Y
        # 4 段：上边 → 右边 → 下边 → 左边
        seg = phase % 4.0
        if seg < 1:
            t = seg
            return (WALK_MIN_X + w * t, WALK_MIN_Y)
        elif seg < 2:
            t = seg - 1
            return (WALK_MAX_X, WALK_MIN_Y + h * t)
        elif seg < 3:
            t = seg - 2
            return (WALK_MAX_X - w * t, WALK_MAX_Y)
        else:
            t = seg - 3
            return (WALK_MIN_X, WALK_MAX_Y - h * t)

    def _show_banner(self, text, duration):
        """在窗口顶部显示一条文字气泡；duration=None 表示常驻"""
        if self.hungry_banner:
            self.canvas.delete(self.hungry_banner)
            self.hungry_banner = None
        self.hungry_banner = self.canvas.create_text(
            CANVAS_W // 2, 24, text=text, fill="#FF5A5A",
            font=("Microsoft YaHei", 20, "bold"))
        if duration is not None:
            self.root.after(int(duration * 1000),
                            lambda: self._clear_banner(self.hungry_banner))

    def _clear_banner(self, item):
        try:
            self.canvas.delete(item)
            if self.hungry_banner == item:
                self.hungry_banner = None
        except Exception:
            pass


if __name__ == "__main__":
    win = tk.Tk()
    pet = DesktopPet(win)
    win.mainloop()
