from ultralytics import YOLO
import torch

DATA_YAML_PATH = '/path/to/data'
PRETRAINED_PATH = '/path/to/pretrained'

if __name__ == "__main__":
    # 检查 CUDA 是否可用（可选）
    print(f"CUDA 是否可用: {torch.cuda.is_available()}")  # 应该返回 True
    print(f"可用 GPU 数量: {torch.cuda.device_count()}")  # 应该返回 1

    # 加载模型
    model = YOLO(PRETRAINED_PATH)  # 加载预训练权重

    # 使用 GPU 训练
    model.train(
        data=DATA_YAML_PATH,  # 数据集配置文件
        epochs=15,  # 训练轮次
        imgsz=640,  # 输入图像尺寸
        batch=16,  # 批量大小（如果显存不足，可降低 batch）
        device=0 if torch.cuda.is_available() else 'cpu',  # 使用 GPU 0（单 GPU 训练）
        workers=0,  # 数据加载线程数（建议设为 CPU 核心数的 1/2）
        optimizer='auto',  # 自动选择优化器（推荐）
        lr0=0.005,  # 初始学习率（可根据需要调整）
        lrf=0.005, #最终学习率
        amp=True,  # 启用混合精度训练（节省显存，提高速度）

        # 正确参数名称
        momentum=0.937,
        weight_decay=0.0005,

        # 学习率调度
        cos_lr=True,  # 余弦退火
        warmup_epochs=3,  # 学习率预热

        # 正则化
        dropout=0.2,  # 注意参数名是'dropout'不是'dropout_rate'

        # 早停
        patience=30  # 早停机制
    )

    # yolo task=detect mode=train model=./runs/detect/train3/weights/last.pt data=D:/Python/test.v4i.yolov8/data.yaml epochs=30 workers=1 batch=16 device=0

    print("\n\n训练完成！\n\n")
