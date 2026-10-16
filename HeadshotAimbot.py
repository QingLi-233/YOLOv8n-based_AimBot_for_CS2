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

class HeadshotAimbot:
    def __init__(self):
        # 屏幕区域设置
        self.screen_width = win32api.GetSystemMetrics(0)
        self.screen_height = win32api.GetSystemMetrics(1)

        # 显示缩放比例
        self.display_scale = 1

        # 颜色设置（头部和身体不同颜色）
        self.colors = {
            'CT': (255, 0, 0),  # 蓝色：CT身体
            'CT_HEAD': (0, 255, 0),  # 绿色：CT头部
            'T': (0, 255, 255),  # 黄色：T身体
            'T_HEAD': (0, 0, 255)  # 红色：T头部
        }

        # 鼠标控制
        self.mouse = Controller()

        # 加载模型
        self.model = YOLO('model/weights/CS2-AimBot.pt')

        # 状态控制
        self.aim_enabled = False
        self.running = True

        # FPS计算
        self.prev_time = 0

        # 截取区域选择
        self.capture_mode = self.select_capture_mode()

        # 根据选择设置截取区域
        if self.capture_mode == 1:
            self.capture_width =1280
            self.capture_height = 1024
            self.display_scale = 0.5  # 缩小显示
        else:  # 左边半屏
            self.capture_width = 1280
            self.capture_height = 960
            self.display_scale = 0.6  # 缩小更多以适应屏幕

        self.capture_rect = (0, 0, self.capture_width, self.capture_height)

    def select_capture_mode(self):
        #显示选择对话框让用户选择截取区域
        options = [
            "1. (1280x1024)",
            "2. (1280x960)"
        ]

        # 创建选择窗口
        cv2.namedWindow("Capture Area Selection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Capture Area Selection", 500, 200)

        # 创建黑色背景
        img = np.zeros((200, 500, 3), dtype=np.uint8)

        # 添加说明文字
        cv2.putText(img, "Please choose the scope of screen:", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # 添加选项
        y_offset = 80
        for i, option in enumerate(options):
            cv2.putText(img, option, (20, y_offset + i * 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # 添加提示
        cv2.putText(img, "input 1 or 2 to opt, input 3 exit", (20, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow("Capture Area Selection", img)

        # 等待用户选择
        while True:
            key = cv2.waitKey(0)
            if key == ord('1'):
                cv2.destroyWindow("Capture Area Selection")
                return 1
            elif key == ord('2'):
                cv2.destroyWindow("Capture Area Selection")
                return 2
            elif key == ord('3'):  # 退出
                cv2.destroyAllWindows()
                exit(0)

    def toggle_aim(self):
        """切换瞄准状态"""
        self.aim_enabled = not self.aim_enabled
        status = "ON" if self.aim_enabled else "OFF"
        print(f"头部瞄准 {status}")

    def run(self):
        print("CS2头部瞄准器启动 - 小键盘0键切换瞄准，*键退出")
        print(f"屏幕分辨率: {self.screen_width}x{self.screen_height}")
        print(f"截取区域: {self.capture_rect}")
        print(f"显示缩放比例: {self.display_scale}")

        while self.running:
            # 按键检测
            if win32api.GetAsyncKeyState(0x60) & 0x8000:  # 小键盘0
                self.toggle_aim()
                time.sleep(0.3)
            if win32api.GetAsyncKeyState(0x6A) & 0x8000:  # 小键盘*
                self.running = False
                break

            # 屏幕截图
            img0 = np.array(ImageGrab.grab(bbox=self.capture_rect))
            img0 = cv2.cvtColor(img0, cv2.COLOR_RGB2BGR)
            # img0 = cv2.GaussianBlur(img0, (3, 3), 0)#高斯降噪

            #直方图均衡化（增强对比度）
            # ycrcb = cv2.cvtColor(img0, cv2.COLOR_BGR2YCrCb)
            # channels = cv2.split(ycrcb)
            # cv2.equalizeHist(channels[0], channels[0])
            # ycrcb = cv2.merge(channels)
            # img0 = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

            # 创建显示画布
            display_img = img0.copy()

            # YOLOv8推理
            results = self.model.predict(
                source=img0,
                conf=0.4,#置信度
                iou=0.05,
                device='cuda' if torch.cuda.is_available() else 'cpu',
                verbose=False
            )

            head_targets = []
            body_targets = []

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)#获取识别出目标的类别码
                    conf = float(box.conf)
                    xyxy = box.xyxy[0].cpu().numpy()#获取目标边框坐标
                    cls_name = self.model.names[cls_id]#命名

                    # 绘制所有检测目标（头部和身体）
                    color = self.colors.get(cls_name, (255, 255, 255))
                    cv2.rectangle(
                        display_img,
                        (int(xyxy[0]), int(xyxy[1])),
                        (int(xyxy[2]), int(xyxy[3])),
                        color,
                        2
                    )

                    # 计算中心点
                    center = ((xyxy[0] + xyxy[2]) / 2, (xyxy[1] + xyxy[3]) / 2)

                    # 分类存储目标
                    if cls_name.endswith('_HEAD'):
                        head_targets.append(center)
                        cv2.circle(display_img, (int(center[0]), int(center[1])), 5, (0, 0, 255), -1)
                    else:
                        body_targets.append(center)
                        cv2.circle(display_img, (int(center[0]), int(center[1])), 3, color, -1)

            if self.aim_enabled and head_targets:
                # 获取截图区域中心（相对于截图）
                screen_center = (img0.shape[1] // 2, img0.shape[0] // 2)

                # 找到距离屏幕中心最近的头部
                closest_head = min(head_targets,
                                   key=lambda h: (h[0] - screen_center[0]) ** 2 + (h[1] - screen_center[1]) ** 2)

                # 转换为绝对屏幕坐标
                abs_x = int(closest_head[0] + self.capture_rect[0])
                abs_y = int(closest_head[1] + self.capture_rect[1])

                # 获取当前鼠标位置
                current_x, current_y = self.mouse.position

                # 调试输出
                print(f"Moving from ({current_x}, {current_y}) to ({abs_x}, {abs_y})")

                #计算移动后坐标
                new_x = current_x + (abs_x - current_x) * 0.7
                new_y = current_y + (abs_y - current_y) * 0.7
                self.mouse.position = (int(new_x), int(new_y))

                # 在显示图像上标记目标点
                # cv2.circle(display_img,
                #            (int(closest_head[0]), int(closest_head[1])),
                #            15, (0, 255, 255), 3)

            # 计算FPS
            curr_time = time.time()
            fps = 1 / (curr_time - self.prev_time)
            self.prev_time = curr_time

            # 显示信息
            status = "HEADSHOT MODE: ON" if self.aim_enabled else "HEADSHOT MODE: OFF"
            cv2.putText(display_img, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_img, f"FPS: {int(fps)}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_img, f"Heads: {len(head_targets)} Bodies: {len(body_targets)}",
                        (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_img, f"Capture: {'1/4' if self.capture_mode == 1 else '1/2'} Screen",
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # 缩小显示
            small_display = cv2.resize(display_img,
                                       (int(self.capture_width * self.display_scale),
                                        int(self.capture_height * self.display_scale)))

            cv2.imshow("CS2 Headshot Aimbot", small_display)
            if cv2.waitKey(1) == ord('*'):
                break

        cv2.destroyAllWindows()
        print("程序已安全退出")


if __name__ == "__main__":
    print(f"CUDA可用: {torch.cuda.is_available()}")
    aimbot = HeadshotAimbot()
    aimbot.run()