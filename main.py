import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pynput.keyboard
import threading
import time
import ctypes

# ========== 配置参数 ==========
HUNGER_TIME = 3600
IDLE_TIME = 30
PET_SPEED = 2

IMG_NORMAL_BODY = "girl_body.png"
IMG_NORMAL_HAND_PRESS = "girl_hand_press.png"
IMG_NORMAL_HAND_EMPTY = "girl_hand_empty.png"
IMG_BEAST_BODY = "beast_body.png"
IMG_BEAST_HAND_PRESS = "beast_hand_press.png"
IMG_BEAST_HAND_EMPTY = "beast_hand_empty.png"

# 手图层基准位置，根据图片微调
HAND_BASE_X = 110
HAND_BASE_Y = 90

# 按键左右偏移
KEY_POSITION = {
    'a': -45, 'A': -45,
    's': -35, 'S': -35,
    'd': -25, 'D': -25,
    'f': -15, 'F': -15,
    'g': -5,  'G': -5,
    'h': 5,   'H': 5,
    'j': 15,  'J': 15,
    'k': 25,  'K': 25,
    'l': 35,  'L': 35,
    ' ': 0,
}

def get_current_input_method():
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    threadid = user32.GetWindowThreadProcessId(hwnd, 0)
    # 修复：GetKeyboardLayout 在 user32 中
    klid = user32.GetKeyboardLayout(threadid)
    return klid

class DesktopPet:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")

        self.drag_x = 0
        self.drag_y = 0

        self.is_beast = False
        self.last_input = get_current_input_method()
        self.last_active_time = time.time()
        self.start_hunger_time = time.time()
        self.hungry = False

        self.img_girl_body = ImageTk.PhotoImage(Image.open(IMG_NORMAL_BODY))
        self.img_girl_hand_press = ImageTk.PhotoImage(Image.open(IMG_NORMAL_HAND_PRESS))
        self.img_girl_hand_empty = ImageTk.PhotoImage(Image.open(IMG_NORMAL_HAND_EMPTY))

        self.img_beast_body = ImageTk.PhotoImage(Image.open(IMG_BEAST_BODY))
        self.img_beast_hand_press = ImageTk.PhotoImage(Image.open(IMG_BEAST_HAND_PRESS))
        self.img_beast_hand_empty = ImageTk.PhotoImage(Image.open(IMG_BEAST_HAND_EMPTY))

        self.canvas = tk.Canvas(root, width=300, height=300, bg="white", highlightthickness=0)
        self.canvas.pack()

        self.body_id = self.canvas.create_image(0, 0, anchor="nw", image=self.img_girl_body)
        self.hand_id = self.canvas.create_image(
            HAND_BASE_X,
            HAND_BASE_Y,
            anchor="nw",
            image=self.img_girl_hand_empty
        )

        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)

        threading.Thread(target=self.input_monitor, daemon=True).start()
        threading.Thread(target=self.idle_loop, daemon=True).start()
        threading.Thread(target=self.hunger_check, daemon=True).start()
        threading.Thread(target=self.key_listen, daemon=True).start()

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def on_drag(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self.last_active_time = time.time()

    def stop_drag(self, event):
        self.drag_x, self.drag_y = None, None

    def input_monitor(self):
        while True:
            try:
                now_input = get_current_input_method()
                if now_input != self.last_input:
                    self.last_input = now_input
                    self.switch_body()
                    self.last_active_time = time.time()
            except:
                pass
            time.sleep(0.8)

    def switch_body(self):
        if self.is_beast:
            self.canvas.itemconfig(self.body_id, image=self.img_beast_body)
            self.canvas.itemconfig(self.hand_id, image=self.img_beast_hand_empty)
        else:
            self.canvas.itemconfig(self.body_id, image=self.img_girl_body)
            self.canvas.itemconfig(self.hand_id, image=self.img_girl_hand_empty)
        self.canvas.coords(self.hand_id, HAND_BASE_X, HAND_BASE_Y)

    def set_hand_image(self, hand_img):
        self.canvas.itemconfig(self.hand_id, image=hand_img)

    def move_hand_layer(self, offset_x):
        new_x = HAND_BASE_X + offset_x
        self.canvas.coords(self.hand_id, new_x, HAND_BASE_Y)

    def idle_loop(self):
        direction = 1
        while True:
            idle_sec = time.time() - self.last_active_time
            if idle_sec > IDLE_TIME:
                if not self.is_beast:
                    self.is_beast = True
                    self.switch_body()
                # 兽态时窗口整体左右移动
                x = self.root.winfo_x()
                x += PET_SPEED * direction
                if x > 1600 or x < 0:
                    direction *= -1
                self.root.geometry(f"+{x}+{self.root.winfo_y()}")
            else:
                if self.is_beast:
                    self.is_beast = False
                    self.switch_body()
            time.sleep(0.05)

    def hunger_check(self):
        while True:
            if time.time() - self.start_hunger_time > HUNGER_TIME and not self.hungry:
                self.hungry = True
                messagebox.showinfo("提示", "我要吃饭！请投喂文件夹")
            time.sleep(10)

    def feed(self):
        self.start_hunger_time = time.time()
        self.hungry = False

    def key_listen(self):
        def on_press(key):
            self.last_active_time = time.time()
            offset_x = 0
            try:
                char = key.char
                offset_x = KEY_POSITION.get(char, 0)
            except AttributeError:
                if key == pynput.keyboard.Key.space:
                    offset_x = 0
            self.move_hand_layer(offset_x)
            if self.is_beast:
                self.set_hand_image(self.img_beast_hand_press)
            else:
                self.set_hand_image(self.img_girl_hand_press)

        def on_release(key):
            if self.is_beast:
                self.set_hand_image(self.img_beast_hand_empty)
            else:
                self.set_hand_image(self.img_girl_hand_empty)
            self.canvas.coords(self.hand_id, HAND_BASE_X, HAND_BASE_Y)

        listener = pynput.keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

if __name__ == "__main__":
    root = tk.Tk()
    pet = DesktopPet(root)
    root.mainloop()
