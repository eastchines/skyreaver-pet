# 桌面宠物 DesktopPet

## 功能
- 鼠标拖拽宠物窗口
- 按键时手部移动并切换按压/悬空姿势，身体保持不动
- 切换输入法时自动切换常态/兽态
- 闲置30秒自动变兽态，屏幕左右游动
- 1小时未操作弹出饥饿提示

## 本地运行
```bash
pip install pillow pynput
python main.py
```

## 打包成exe（Windows）
```bash
pip install pyinstaller pillow pynput
pyinstaller -w main.py --add-data "*.png;."
```
生成的文件在 `dist/main/` 文件夹中。

## 项目文件说明
- `main.py` — 主程序
- `girl_body.png` — 常态身体
- `girl_hand_press.png` — 常态按压手
- `girl_hand_empty.png` — 常态悬空手
- `beast_body.png` — 兽态身体
- `beast_hand_press.png` — 兽态按压手
- `beast_hand_empty.png` — 兽态悬空手
- `.github/workflows/build.yml` — GitHub Action 自动打包配置

## 调整参数
在 `main.py` 顶部修改：
- `HUNGER_TIME` — 饥饿时间（秒）
- `IDLE_TIME` — 闲置变兽态时间（秒）
- `PET_SPEED` — 游动速度
- `HAND_BASE_X / HAND_BASE_Y` — 手的初始位置
- `KEY_POSITION` — 不同按键对应的手左右偏移
