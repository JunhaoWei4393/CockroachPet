"""
pil_preview.py
使用 Pillow 直接渲染蟑螂几何模型，生成 PNG 预览。
绕开 tkinter 在沙盒/远程桌面中无法截屏的问题。
"""

import math
import os
import sys
from PIL import Image, ImageDraw

# 适配 previews/ 子目录：把项目根目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cockroach_model import CockroachModel


class PILRenderer:
    """用 Pillow 绘制蟑螂，接口与 tkinter Canvas 绘制方法对应。"""

    def __init__(self, width: int, height: int, bg: str = "#E8EDF2"):
        self.width = width
        self.height = height
        self.img = Image.new("RGBA", (width, height), bg)
        self.draw = ImageDraw.Draw(self.img)

    def _draw_ellipse(self, x, y, rx, ry, fill, outline="", width=1):
        self.draw.ellipse(
            [x - rx, y - ry, x + rx, y + ry],
            fill=fill, outline=outline if outline else None, width=width
        )

    def _draw_tapered_segment(self, p1, p2, w1, w2, color):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 0.5:
            return
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        hw1, hw2 = w1 * 0.5, w2 * 0.5
        points = [
            (p1[0] + nx * hw1, p1[1] + ny * hw1),
            (p1[0] - nx * hw1, p1[1] - ny * hw1),
            (p2[0] - nx * hw2, p2[1] - ny * hw2),
            (p2[0] + nx * hw2, p2[1] + ny * hw2),
        ]
        self.draw.polygon(points, fill=color, outline="#8B4513")

    def _draw_leg_spines(self, p1, p2, color, count, length):
        for i in range(1, count + 1):
            t = i / (count + 1)
            x = p1[0] + (p2[0] - p1[0]) * t
            y = p1[1] + (p2[1] - p1[1]) * t
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 1:
                continue
            ux, uy = -dy / seg_len, dx / seg_len
            bx, by = dx / seg_len * 0.3, dy / seg_len * 0.3
            self.draw.line(
                [(x, y), (x + ux * length + bx * length * 0.5, y + uy * length + by * length * 0.5)],
                fill=color, width=1
            )

    def _draw_leg_realistic(self, leg):
        color_leg = "#E08E3E"
        color_leg_mid = "#D2691E"
        color_leg_dark = "#A0522D"
        color_spine = "#8B4513"
        coxa, femur, tibia, tarsus = leg.coxa, leg.femur, leg.tibia, leg.tarsus
        self._draw_tapered_segment(coxa, femur, 4.0, 2.8, color_leg)
        self._draw_tapered_segment(femur, tibia, 2.8, 2.0, color_leg_mid)
        self._draw_tapered_segment(tibia, tarsus, 2.0, 1.3, color_leg_dark)
        for p, r in [(coxa, 1.8), (femur, 1.6), (tibia, 1.3), (tarsus, 1.0)]:
            self._draw_ellipse(p[0], p[1], r, r, fill=color_leg_dark)
        self._draw_leg_spines(coxa, femur, color_spine, count=8, length=3.5)
        self._draw_leg_spines(femur, tibia, color_spine, count=10, length=3.5)
        self._draw_leg_spines(tibia, tarsus, color_spine, count=8, length=2.8)

    def _draw_tegmen_realistic(self, wing, color, edge_color, vein_color, is_left):
        """绘制写实鞘翅：以半椭圆弧线形成流畅长椭圆，贴合饱满背部"""
        dx = wing.tip[0] - wing.base[0]
        dy = wing.tip[1] - wing.base[1]
        length = math.hypot(dx, dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        px, py = -uy, ux  # 侧向（左）
        half_w = wing.width * 0.5

        # 椭圆中心与半轴
        cx = (wing.base[0] + wing.tip[0]) * 0.5
        cy = (wing.base[1] + wing.tip[1]) * 0.5
        a = length * 0.5
        b = half_w
        sign = 1 if is_left else -1

        # 生成半椭圆轮廓：base -> 外侧弧 -> tip -> base（闭合）
        arc_points = []
        n_arc = 14
        for i in range(n_arc, -1, -1):
            t = math.pi * i / n_arc  # π -> 0
            arc_x = cx + a * math.cos(t) * ux + sign * b * math.sin(t) * px
            arc_y = cy + a * math.cos(t) * uy + sign * b * math.sin(t) * py
            arc_points.append((arc_x, arc_y))
        wing_points = [wing.base] + arc_points + [wing.tip]
        self.draw.polygon(wing_points, fill=color, outline="#6B3A25", width=1)

        # 外侧边缘高光带
        edge_points = []
        for i in range(n_arc // 2, n_arc + 1):
            t = math.pi * i / n_arc
            arc_x = cx + a * math.cos(t) * ux + sign * b * math.sin(t) * px
            arc_y = cy + a * math.cos(t) * uy + sign * b * math.sin(t) * py
            edge_points.append((arc_x, arc_y))
        self.draw.line(edge_points, fill=edge_color, width=2)

        # 主翅脉
        vein_t = 0.55
        vx = wing.base[0] + ux * length * vein_t
        vy = wing.base[1] + uy * length * vein_t
        vw = half_w * 0.55
        if is_left:
            v1, v2 = (vx - px * vw, vy - py * vw), (vx + px * vw * 0.10, vy + py * vw * 0.10)
        else:
            v1, v2 = (vx + px * vw, vy + py * vw), (vx - px * vw * 0.10, vy - py * vw * 0.10)
        self.draw.line([v1, v2], fill=vein_color, width=1)



    def _draw_suture(self, data, color):
        left_base, left_tip = data.tegmen_left.base, data.tegmen_left.tip
        right_base, right_tip = data.tegmen_right.base, data.tegmen_right.tip
        base = ((left_base[0] + right_base[0]) / 2, (left_base[1] + right_base[1]) / 2)
        tip = ((left_tip[0] + right_tip[0]) / 2, (left_tip[1] + right_tip[1]) / 2)
        self.draw.line([base, tip], fill=color, width=1)

    def _draw_pronotum_realistic(self, data, color, margin_color, dark_color):
        thorax = data.thorax
        size = data.body_size
        scale = data.body_scale
        angle = data.angle
        forward = (math.cos(angle), math.sin(angle))
        left = (-math.sin(angle), math.cos(angle))
        right = (math.sin(angle), -math.cos(angle))

        w = size * 0.32 * scale  # 与 THORAX_WIDTH_RATIO 保持一致
        h = size * 0.20 * scale

        def pt_offset(origin, direction, distance, direction2=None, distance2=0.0):
            x = origin[0] + direction[0] * distance
            y = origin[1] + direction[1] * distance
            if direction2 is not None:
                x += direction2[0] * distance2
                y += direction2[1] * distance2
            return (x, y)

        points = [
            pt_offset(thorax, forward, h * 0.55, left, w * 0.25),
            pt_offset(thorax, forward, h * 0.40, left, w * 0.40),
            pt_offset(thorax, forward, h * 0.25),
            pt_offset(thorax, forward, h * 0.40, right, w * 0.40),
            pt_offset(thorax, forward, h * 0.55, right, w * 0.25),
            pt_offset(thorax, forward, h * 0.05, right, w * 0.95),
            pt_offset(thorax, forward, -h * 0.55, right, w * 0.75),
            pt_offset(thorax, forward, -h * 0.75, right, w * 0.25),
            pt_offset(thorax, forward, -h * 0.75, left, w * 0.25),
            pt_offset(thorax, forward, -h * 0.55, left, w * 0.75),
            pt_offset(thorax, forward, h * 0.05, left, w * 0.95),
        ]
        self.draw.polygon(points, fill=color, outline="#5C3A22")

        margin_points = [
            pt_offset(thorax, forward, h * 0.45, left, w * 0.18),
            pt_offset(thorax, forward, h * 0.32, left, w * 0.30),
            pt_offset(thorax, forward, h * 0.18),
            pt_offset(thorax, forward, h * 0.32, right, w * 0.30),
            pt_offset(thorax, forward, h * 0.45, right, w * 0.18),
            pt_offset(thorax, forward, -h * 0.05, right, w * 0.82),
            pt_offset(thorax, forward, -h * 0.62, right, w * 0.60),
            pt_offset(thorax, forward, -h * 0.68, right, w * 0.18),
            pt_offset(thorax, forward, -h * 0.68, left, w * 0.18),
            pt_offset(thorax, forward, -h * 0.62, left, w * 0.60),
            pt_offset(thorax, forward, -h * 0.05, left, w * 0.82),
        ]
        self.draw.polygon(margin_points, outline=margin_color, width=2)

        disk = pt_offset(thorax, forward, -h * 0.05)
        self._draw_ellipse(disk[0], disk[1], w * 0.32, h * 0.30, fill=dark_color)

    def _draw_head_realistic(self, data, head_color, patch_color, eye_color):
        head = data.head
        hr = data.head_radius * data.body_scale
        angle = data.angle
        forward = (math.cos(angle), math.sin(angle))
        left = (-math.sin(angle), math.cos(angle))
        right = (math.sin(angle), -math.cos(angle))

        self._draw_ellipse(head[0], head[1], hr * 0.9, hr * 0.75, fill=head_color, outline="#2E1A12")
        patch = (head[0] + forward[0] * hr * 0.35, head[1] + forward[1] * hr * 0.35)
        self._draw_ellipse(patch[0], patch[1], hr * 0.45, hr * 0.28, fill=patch_color)
        eye_r = hr * 0.14
        eye_left = (head[0] + left[0] * hr * 0.55, head[1] + left[1] * hr * 0.55)
        eye_right = (head[0] + right[0] * hr * 0.55, head[1] + right[1] * hr * 0.55)
        self._draw_ellipse(eye_left[0], eye_left[1], eye_r, eye_r, fill=eye_color)
        self._draw_ellipse(eye_right[0], eye_right[1], eye_r, eye_r, fill=eye_color)

    def _draw_antenna_realistic(self, antenna, color):
        points = [antenna.base] + list(antenna.segments) + [antenna.tip]
        if len(points) >= 2:
            self.draw.line(points, fill=color, width=1)
        self._draw_ellipse(antenna.tip[0], antenna.tip[1], 0.8, 0.8, fill=color)

    def _draw_cockroach(self, data):
        color_body = "#6B3A25"
        color_body_dark = "#3D2216"
        color_pronotum = "#E8A650"
        color_pronotum_margin = "#F5D0A0"
        color_pronotum_dark = "#3D2618"
        color_tegmen = "#7A4228"
        color_tegmen_edge = "#B87A4E"
        color_tegmen_vein = "#4A2A18"
        color_suture = "#C9965E"
        color_antenna = "#8B4513"
        color_head = "#6B3E2E"
        color_head_patch = "#E8A650"
        color_eye = "#2A1812"
        color_cercus = "#8B5A3C"

        size = data.body_size
        abdomen = data.abdomen

        for leg in data.legs:
            self._draw_leg_realistic(leg)

        outline = data.body_outline
        if len(outline) >= 3:
            self.draw.polygon(outline, fill=color_body, outline=color_body_dark, width=2)

        self._draw_tegmen_realistic(data.tegmen_left, color_tegmen, color_tegmen_edge, color_tegmen_vein, is_left=True)
        self._draw_tegmen_realistic(data.tegmen_right, color_tegmen, color_tegmen_edge, color_tegmen_vein, is_left=False)
        self._draw_suture(data, color_suture)
        self._draw_head_realistic(data, color_head, color_head_patch, color_eye)
        self._draw_pronotum_realistic(data, color_pronotum, color_pronotum_margin, color_pronotum_dark)
        self._draw_antenna_realistic(data.antenna_left, color_antenna)
        self._draw_antenna_realistic(data.antenna_right, color_antenna)
        self.draw.line([abdomen, data.cercus_left], fill=color_cercus, width=2)
        self.draw.line([abdomen, data.cercus_right], fill=color_cercus, width=2)

    def save(self, path: str):
        self.img.save(path)
        print(f"PIL 预览已保存: {os.path.abspath(path)}")


def main():
    model = CockroachModel(body_size=80)
    # 与参考照片一致：头部朝下（angle = -π/2）
    data = model.compute(
        x=300, y=300, angle=-math.pi / 2, speed=120,
        dt=0.016, is_scared=False, turn_rate=0.0
    )
    renderer = PILRenderer(600, 600)
    renderer._draw_cockroach(data)
    renderer.save("cockroach_preview.png")


if __name__ == "__main__":
    main()
