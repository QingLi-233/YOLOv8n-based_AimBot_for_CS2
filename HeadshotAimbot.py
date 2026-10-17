from pynput.mouse import Controller
import win32api
import win32con
import time
from PIL import ImageGrab
import numpy as np
import cv2
from ultralytics import YOLO
import torch

"""
python HeadshotAimbot.py
"""


# ============================================================
# 全局参数配置 | Global Configuration
# ============================================================
class CONFIG:
    # ---------- 模型 ----------
    MODEL_PATH = 'model/weights/CS2-AimBot.pt'
    CONF       = 0.4      # 置信度阈值
    IOU        = 0.05     # NMS IoU 阈值
    IMGSZ      = 640      # 推理输入尺寸
    VERBOSE    = False

    # ---------- 设备 ----------
    DEVICE = '0' if torch.cuda.is_available() else 'cpu'

    # ---------- 截取区域 ----------
    CAPTURE_MODES = {
        1: {'width': 1280, 'height': 1024, 'display_scale': 0.5, 'label': '1/4 Screen'},
        2: {'width': 1280, 'height': 960,  'display_scale': 0.6, 'label': '1/2 Screen'},
    }

    # ---------- 瞄准 ----------
    AIM_ENABLED_DEFAULT = False
    AIM_SMOOTHING       = 0.7   # 0.0 ~ 1.0，越接近 1 越"瞬移"

    # ---------- 按键 ----------
    KEY_TOGGLE_AIM = 0x60   # 小键盘 0
    KEY_EXIT       = 0x6A   # 小键盘 *

    # ---------- 窗口 ----------
    MAIN_WINDOW      = "CS2 Headshot Aimbot"
    SELECTION_WINDOW = "Capture Area Selection"
    SELECTION_SIZE   = (500, 200)

    # ---------- 颜色 ----------
    COLORS = {
        'CT':      (255, 0, 0),
        'CT_HEAD': (0, 255, 0),
        'T':       (0, 255, 255),
        'T_HEAD':  (0, 0, 255),
    }
    DEFAULT_COLOR = (255, 255, 255)


class HeadshotAimbot:
    def __init__(self):
        # 屏幕分辨率
        self.screen_width  = win32api.GetSystemMetrics(0)
        self.screen_height = win32api.GetSystemMetrics(1)

        # 选择截取模式
        self.capture_mode = self.select_capture_mode()
        mode_cfg = CONFIG.CAPTURE_MODES[self.capture_mode]

        self.capture_width  = mode_cfg['width']
        self.capture_height = mode_cfg['height']
        self.display_scale  = mode_cfg['display_scale']
        self.capture_rect   = (0, 0, self.capture_width, self.capture_height)

        # 组件
        self.colors = CONFIG.COLORS
        self.mouse  = Controller()
        self.model  = YOLO(CONFIG.MODEL_PATH)

        # 状态
        self.aim_enabled = CONFIG.AIM_ENABLED_DEFAULT
        self.running     = True
        self.prev_time   = time.time()

    # --------------------------------------------------------
    def select_capture_mode(self):
        w, h = CONFIG.SELECTION_SIZE
        cv2.namedWindow(CONFIG.SELECTION_WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(CONFIG.SELECTION_WINDOW, w, h)

        img = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(img, "Please choose the scope of screen:", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        for i, (k, v) in enumerate(CONFIG.CAPTURE_MODES.items()):
            cv2.putText(img, f"{k}. ({v['width']}x{v['height']})",
                        (20, 80 + i * 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.putText(img, "input 1 or 2 to opt, input 3 exit", (20, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow(CONFIG.SELECTION_WINDOW, img)

        while True:
            key = cv2.waitKey(0)
            if key in (ord('1'), ord('2')):
                mode = int(chr(key))
                if mode in CONFIG.CAPTURE_MODES:
                    cv2.destroyWindow(CONFIG.SELECTION_WINDOW)
                    return mode
            elif key == ord('3'):
                cv2.destroyAllWindows()
                exit(0)

    # --------------------------------------------------------
    def toggle_aim(self):
        self.aim_enabled = not self.aim_enabled
        print(f"头部瞄准 {'ON' if self.aim_enabled else 'OFF'}")

    # --------------------------------------------------------
    def run(self):
        print("CS2头部瞄准器启动 - 小键盘0键切换瞄准，*键退出")
        print(f"屏幕分辨率: {self.screen_width}x{self.screen_height}")
        print(f"截取区域: {self.capture_rect}")
        print(f"显示缩放比例: {self.display_scale}")

        while self.running:
            # 按键检测
            if win32api.GetAsyncKeyState(CONFIG.KEY_TOGGLE_AIM) & 0x8000:
                self.toggle_aim()
                time.sleep(0.3)
            if win32api.GetAsyncKeyState(CONFIG.KEY_EXIT) & 0x8000:
                self.running = False
                break

            # 屏幕截图
            img0 = np.array(ImageGrab.grab(bbox=self.capture_rect))
            img0 = cv2.cvtColor(img0, cv2.COLOR_RGB2BGR)

            display_img = img0.copy()

            # YOLO 推理
            results = self.model.predict(
                source=img0,
                conf=CONFIG.CONF,
                iou=CONFIG.IOU,
                imgsz=CONFIG.IMGSZ,
                device=CONFIG.DEVICE,
                verbose=CONFIG.VERBOSE,
            )

            head_targets = []
            body_targets = []

            for result in results:
                for box in result.boxes:
                    cls_id   = int(box.cls)
                    cls_name = self.model.names[cls_id]
                    xyxy     = box.xyxy[0].cpu().numpy()
                    color    = self.colors.get(cls_name, CONFIG.DEFAULT_COLOR)

                    cv2.rectangle(display_img,
                                  (int(xyxy[0]), int(xyxy[1])),
                                  (int(xyxy[2]), int(xyxy[3])),
                                  color, 2)

                    center = ((xyxy[0] + xyxy[2]) / 2,
                              (xyxy[1] + xyxy[3]) / 2)

                    if cls_name.endswith('_HEAD'):
                        head_targets.append(center)
                        cv2.circle(display_img,
                                   (int(center[0]), int(center[1])),
                                   5, (0, 0, 255), -1)
                    else:
                        body_targets.append(center)
                        cv2.circle(display_img,
                                   (int(center[0]), int(center[1])),
                                   3, color, -1)

            # 瞄准
            if self.aim_enabled and head_targets:
                screen_center = (img0.shape[1] // 2, img0.shape[0] // 2)
                closest_head  = min(
                    head_targets,
                    key=lambda h: (h[0] - screen_center[0]) ** 2
                                + (h[1] - screen_center[1]) ** 2
                )

                abs_x = int(closest_head[0] + self.capture_rect[0])
                abs_y = int(closest_head[1] + self.capture_rect[1])

                current_x, current_y = self.mouse.position
                new_x = current_x + (abs_x - current_x) * CONFIG.AIM_SMOOTHING
                new_y = current_y + (abs_y - current_y) * CONFIG.AIM_SMOOTHING
                self.mouse.position = (int(new_x), int(new_y))

            # FPS
            curr_time = time.time()
            dt = curr_time - self.prev_time
            fps = 1 / dt if dt > 0 else 0
            self.prev_time = curr_time

            # OSD 信息
            status = "HEADSHOT MODE: ON" if self.aim_enabled else "HEADSHOT MODE: OFF"
            cv2.putText(display_img, status, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_img, f"FPS: {int(fps)}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_img,
                        f"Heads: {len(head_targets)} Bodies: {len(body_targets)}",
                        (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_img,
                        f"Capture: {CONFIG.CAPTURE_MODES[self.capture_mode]['label']}",
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # 缩放显示
            small_display = cv2.resize(
                display_img,
                (int(self.capture_width * self.display_scale),
                 int(self.capture_height * self.display_scale))
            )
            cv2.imshow(CONFIG.MAIN_WINDOW, small_display)
            if cv2.waitKey(1) == ord('*'):
                break

        cv2.destroyAllWindows()
        print("程序已安全退出")


if __name__ == "__main__":
    print(f"CUDA可用: {torch.cuda.is_available()}")
    aimbot = HeadshotAimbot()
    aimbot.run()