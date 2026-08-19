"""
leg_animation_preview.py
生成蟑螂行走时的多帧预览，用于验证腿部不规则高频摆动与转弯轨迹。
"""

import math
import os
import sys
from PIL import Image

# 适配 previews/ 子目录：把项目根目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cockroach_model import CockroachModel
from pil_preview import PILRenderer


def main():
    model = CockroachModel(body_size=80)
    dt = 0.016
    frames = []

    # 第一段：固定位置展示直行/左转/右转的不对称步态
    segments = [
        # (帧数, 速度, 转向速率)
        (12, 140, 0.0),    # 直行
        (12, 120, 2.8),    # 左转（外侧右腿摆幅更大）
        (12, 120, -2.8),   # 右转（外侧左腿摆幅更大）
    ]

    for count, speed, turn_rate in segments:
        for _ in range(count):
            data = model.compute(
                x=300, y=300, angle=-math.pi / 2,
                speed=speed, dt=dt, is_scared=False,
                turn_rate=turn_rate,
            )
            renderer = PILRenderer(600, 600)
            renderer._draw_cockroach(data)
            frames.append(renderer.img)

    # 第二段：模拟真实转弯轨迹（沿弧线行进）
    # 用简单运动学让蟑螂沿圆弧行走，验证身体与腿部的转弯耦合
    x, y = 300.0, 300.0
    angle = -math.pi / 2
    speed = 130.0
    turn_rate = 2.0  # 恒定左转
    for _ in range(24):
        angle += turn_rate * dt
        x += math.cos(angle) * speed * dt
        y += math.sin(angle) * speed * dt
        data = model.compute(
            x=x, y=y, angle=angle,
            speed=speed, dt=dt, is_scared=False,
            turn_rate=turn_rate,
        )
        renderer = PILRenderer(600, 600)
        renderer._draw_cockroach(data)
        frames.append(renderer.img)

    # 保存为 GIF 动画
    frames[0].save(
        "cockroach_legs.gif",
        save_all=True,
        append_images=frames[1:],
        duration=55,
        loop=0,
    )
    print("GIF 已保存: cockroach_legs.gif")


if __name__ == "__main__":
    main()
