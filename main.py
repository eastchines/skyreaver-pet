import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pynput.keyboard
import threading
import time
import ctypes
import os

# ========== 配置参数 ==========
HUNGER_TIME = 3600  # 饥饿时间 3600秒 = 1小时
IDLE_TIME = 30  # 闲置多少秒变兽态
PET_SPEED = 2  # 绕圈移动速度
# 图片文件
IMG_NORMAL_BODY = "girl_body.png"
IMG_NORMAL_HAND = "girl_hand.png"
IMG_BEAST_BODY = "beast_body.png"
IMG_BEAST_HAND = "beast_hand.png"

# 读取Windows当前输入法
def get_current_input_method():
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    threadid = user32.GetWindowThreadProcessId(hwnd, 0)
    klid = ctypes.windll.kernel32.GetKeyboardLayout(threadid)
    return klid

class DesktopPet:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True) #无边框
        self.root.attributes("-topmost", True) #置顶
        self.root.attributes("-transparentcolor", "white") #透明底色

        # 拖拽变量
        self.drag_x = 0
        self.drag_y = 0
        # 状态
        self.is_beast = False
        self.last_input = get_current_input_method()
        self.last_active_time = time.time()
        self.start_hunger_time = time.time()
        self.hungry = False

        # 加载图片
        self.img_girl_body = ImageTk.PhotoImage(Image.open(IMG_NORMAL_BODY))
        self.img_girl_hand = ImageTk.PhotoImage(Image.open(IMG_NORMAL_HAND))
        self.img_beast_body = ImageTk.PhotoImage(Image.open(IMG_BEAST_BODY))
        self.img_beast_hand = ImageTk.PhotoImage(Image.open(IMG_BEAST_HAND))

        self.label = tk.Label(root, image=self.img_girl_body, bg="white")
        self.label.pack()

        # ========== 绑定拖拽事件【解决无法拖动】 ==========
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.stop_drag)

        # 启动后台线程
        threading.Thread(target=self.input_monitor, daemon=True).start()
        threading.Thread(target=self.idle_loop, daemon=True).start()
        threading.Thread(target=self.hunger_check, daemon=True).start()
        threading.Thread(target=self.key_listen, daemon=True).start()

    # =====拖拽函数=====
    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y
    def on_drag(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self.last_active_time = time.time() #拖动视为活跃，重置闲置计时
    def stop_drag(self, event):
        self.drag_x, self.drag_y = None, None

    # =====输入法轮询，切换图片=====
    def input_monitor(self):
        while True:
            now_input = get_current_input_method()
            if now_input != self.last_input:
                self.last_input = now_input
                self.switch_image()
                self.last_active_time = time.time()
            time.sleep(0.8)

    def switch_image(self):
        if self.is_beast:
            self.label.config(image=self.img_beast_body)
        else:
            self.label.config(image=self.img_girl_body)

    # =====闲置检测，闲置超时变兽态，自动绕圈=====
    def idle_loop(self):
        direction = 1
        while True:
            idle_sec = time.time() - self.last_active_time
            if idle_sec > IDLE_TIME:
                if not self.is_beast:
                    self.is_beast = True
                    self.switch_image()
                # 兽态绕圈移动
                x = self.root.winfo_x()
                x += PET_SPEED * direction
                if x > 1600 or x < 0:
                    direction *= -1
                self.root.geometry(f"+{x}+{self.root.winfo_y()}")
            else:
                if self.is_beast:
                    self.is_beast = False
                    self.switch_image()
            time.sleep(0.05)

    # =====饥饿检测=====
    def hunger_check(self):
        while True:
            if time.time() - self.start_hunger_time > HUNGER_TIME and not self.hungry:
                self.hungry = True
                messagebox.showinfo("提示", "我要吃饭！请投喂文件夹")
            time.sleep(10)
    def feed(self):
        self.start_hunger_time = time.time()
        self.hungry = False

    # =====键盘监听，按键切换手部图片=====
    def key_listen(self):
        def on_press(key):
            self.last_active_time = time.time()
            try:
                if key == pynput.keyboard.Key.space:
                    self.label.config(image=self.img_girl_hand) #空格悬空手
                else:
                    self.label.config(image=self.img_girl_hand)
            except:
                pass
        listener = pynput.keyboard.Listener(on_press=on_press)
        listener.start()

if __name__ == "__main__":
    root = tk.Tk()
    pet = DesktopPet(root)
    root.mainloop()
