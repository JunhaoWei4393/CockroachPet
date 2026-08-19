"""
wrap_preview.py
验证并演示屏幕环绕：蟑螂跨边后从对侧出现。
"""

import math
import os
import sys
from dataclasses import fields, is_dataclass, replace

# 适配 previews/ 子目录：把项目根目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cockroach_model import CockroachModel
from pil_preview import PILRenderer


def translate_render_data(data, dx, dy):
    """平移渲染数据所有坐标，生成屏幕环绕幽灵副本（与 main.py 同逻辑）"""
    def _translate(obj):
        if is_dataclass(obj):
            changes = {}
            for f in fields(obj):
                changes[f.name] = _translate(getattr(obj, f.name))
            return replace(obj, **changes)
        if isinstance(obj, tuple):
            if len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj):
                return (obj[0] + dx, obj[1] + dy)
            return tuple(_translate(v) for v in obj)
        if isinstance(obj, list):
            return [_translate(v) for v in obj]
        return obj
    return _translate(data)


def main():
    model = CockroachModel(body_size=80)
    dt = 0.016
    frames = []

    # 模拟屏幕 600x450，蟑螂从底部附近向下穿出，应从上边缘进入
    x, y = 300.0, 370.0
    angle = math.pi / 2  # 向下
    speed = 260.0
    turn_rate = 0.0
    sw, sh = 600, 450

    for _ in range(55):
        y += speed * dt
        # 手动实现环绕，方便在固定小画布内预览
        wrapped = False
        if y > sh:
            y -= sh
            wrapped = True

        data = model.compute(
            x=x, y=y, angle=angle,
            speed=speed, dt=dt, is_scared=False,
            turn_rate=turn_rate,
        )
        data.wrap_screen = True

        renderer = PILRenderer(sw, sh)
        renderer._draw_cockroach(data)

        # 当靠近下边缘时，在顶部绘制幽灵副本，保证视觉连续
        radius = data.head_radius * 7
        offsets = []
        if data.y < radius:
            offsets.append((0.0, sh))
        if data.y > sh - radius:
            offsets.append((0.0, -sh))
        if data.x < radius:
            offsets.append((sw, 0.0))
        if data.x > sw - radius:
            offsets.append((-sw, 0.0))

        for dx, dy in offsets:
            ghost = translate_render_data(data, dx, dy)
            renderer._draw_cockroach(ghost)

        frames.append(renderer.img)

    frames[0].save(
        "wrap_demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=40,
        loop=0,
    )
    print("环绕演示已保存: wrap_demo.gif")


if __name__ == "__main__":
    main()
