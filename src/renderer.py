"""
renderer.py
蟑螂渲染器 - 把 CockroachRenderData 绘制到 tkinter Canvas

从 main.py 抽取的纯渲染逻辑，桌宠主窗口与设置界面预览共用，
保证两处绘制效果完全一致。
"""

import math
from dataclasses import fields, is_dataclass, replace


class CockroachRenderer:
    """
    蟑螂 Canvas 渲染器

    负责把 CockroachRenderData 绘制到指定的 tkinter Canvas。
    支持屏幕环绕时在边界处绘制幽灵副本，保证穿越边界视觉连续。

    Args:
        canvas: tkinter.Canvas 实例
    """

    def __init__(self, canvas):
        self.canvas = canvas

    # ==================== 主渲染入口 ====================

    def render(self, data, screen_w: float, screen_h: float):
        """
        渲染一帧：本体 + （开启环绕时）边界幽灵副本

        Args:
            data: CockroachRenderData
            screen_w, screen_h: 画布/屏幕尺寸，用于判断幽灵副本偏移
        """
        self.canvas.delete("all")

        # 本体
        self.draw_cockroach(data)

        # 屏幕环绕时，在相邻边界处绘制幽灵副本
        if getattr(data, "wrap_screen", False):
            for dx, dy in self._get_wrap_offsets(data, screen_w, screen_h):
                ghost = self._translate_render_data(data, dx, dy)
                self.draw_cockroach(ghost)

    def draw_cockroach(self, data):
        """精确主义风格绘制美洲大蠊（本体/幽灵副本复用）"""
        # 参考照片配色：背部为深红棕光泽，前胸背板浅橙，腿部偏黄褐
        color_body = "#6B3A25"
        color_body_dark = "#3D2216"
        color_pronotum = "#E8A650"
        color_pronotum_margin = "#F5D0A0"
        color_pronotum_dark = "#3D2618"
        color_tegmen = "#7A4228"
        color_tegmen_mid = "#8A4E32"
        color_tegmen_edge = "#B87A4E"
        color_tegmen_vein = "#4A2A18"
        color_suture = "#C9965E"
        color_antenna = "#8B4513"
        color_head = "#6B3E2E"
        color_head_patch = "#E8A650"
        color_eye = "#2A1812"
        color_cercus = "#8B5A3C"

        abdomen = data.abdomen

        # ---- 后翅（惊吓时展开）----
        if data.hindwing_left.span_angle > 0.1:
            self._draw_hindwing(data.hindwing_left, "#E8C69A")
            self._draw_hindwing(data.hindwing_right, "#E8C69A")

        # ---- 腿部 ----
        for leg in data.legs:
            self._draw_leg_realistic(leg)

        # ---- 身体底色（平滑椭圆轮廓）----
        outline = data.body_outline
        if len(outline) >= 3:
            self.canvas.create_polygon(
                outline, fill=color_body, outline=color_body_dark, width=1.5, smooth=True
            )

        # ---- 鞘翅 ----
        self._draw_tegmen_realistic(
            data.tegmen_left, color_tegmen, color_tegmen_mid,
            color_tegmen_edge, color_tegmen_vein, is_left=True
        )
        self._draw_tegmen_realistic(
            data.tegmen_right, color_tegmen, color_tegmen_mid,
            color_tegmen_edge, color_tegmen_vein, is_left=False
        )

        # ---- 翅缝 ----
        self._draw_suture(data, color_suture)

        # ---- 头部（先画，被前胸背板部分遮盖）----
        self._draw_head_realistic(data, color_head, color_head_patch, color_eye)

        # ---- 前胸背板 ----
        self._draw_pronotum_realistic(
            data, color_pronotum, color_pronotum_margin, color_pronotum_dark
        )

        # ---- 触角 ----
        self._draw_antenna_realistic(data.antenna_left, color_antenna)
        self._draw_antenna_realistic(data.antenna_right, color_antenna)

        # ---- 尾须 ----
        self.canvas.create_line(
            abdomen[0], abdomen[1],
            data.cercus_left[0], data.cercus_left[1],
            fill=color_cercus, width=2, smooth=True
        )
        self.canvas.create_line(
            abdomen[0], abdomen[1],
            data.cercus_right[0], data.cercus_right[1],
            fill=color_cercus, width=2, smooth=True
        )

    # ==================== 各部位绘制 ====================

    def _draw_ellipse(self, x, y, rx, ry, fill, outline="", width=1):
        """绘制椭圆"""
        self.canvas.create_oval(
            x - rx, y - ry, x + rx, y + ry,
            fill=fill, outline=outline, width=width
        )

    def _draw_leg_realistic(self, leg):
        """绘制参考照片中的腿：橙棕色、分段明显、刚毛浓密"""
        color_leg = "#E08E3E"
        color_leg_mid = "#D2691E"
        color_leg_dark = "#A0522D"
        color_spine = "#8B4513"

        coxa, femur, tibia, tarsus = leg.coxa, leg.femur, leg.tibia, leg.tarsus

        # 参考照片中腿较细长，布满尖刺状刚毛
        self._draw_tapered_segment(coxa, femur, 4.0, 2.8, color_leg)
        self._draw_tapered_segment(femur, tibia, 2.8, 2.0, color_leg_mid)
        self._draw_tapered_segment(tibia, tarsus, 2.0, 1.3, color_leg_dark)

        # 关节点
        for p, r in [(coxa, 1.8), (femur, 1.6), (tibia, 1.3), (tarsus, 1.0)]:
            self.canvas.create_oval(
                p[0] - r, p[1] - r, p[0] + r, p[1] + r,
                fill=color_leg_dark, outline=""
            )

        # 浓密刚毛
        self._draw_leg_spines(coxa, femur, color_spine, count=8, length=3.5)
        self._draw_leg_spines(femur, tibia, color_spine, count=10, length=3.5)
        self._draw_leg_spines(tibia, tarsus, color_spine, count=8, length=2.8)

    def _draw_tapered_segment(self, p1, p2, w1, w2, color):
        """绘制一端粗一端细的腿段（梯形多边形）"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 0.5:
            return
        ux, uy = dx / length, dy / length
        # 垂直单位向量
        nx, ny = -uy, ux

        hw1 = w1 * 0.5
        hw2 = w2 * 0.5
        points = [
            (p1[0] + nx * hw1, p1[1] + ny * hw1),
            (p1[0] - nx * hw1, p1[1] - ny * hw1),
            (p2[0] - nx * hw2, p2[1] - ny * hw2),
            (p2[0] + nx * hw2, p2[1] + ny * hw2),
        ]
        self.canvas.create_polygon(points, fill=color, outline="#5A3A22", width=0.6)

    def _draw_leg_spines(self, p1, p2, color, count, length):
        """沿腿段绘制向外伸出的刚毛"""
        for i in range(1, count + 1):
            t = i / (count + 1)
            x = p1[0] + (p2[0] - p1[0]) * t
            y = p1[1] + (p2[1] - p1[1]) * t
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 1:
                continue
            # 垂直方向朝外
            ux, uy = -dy / seg_len, dx / seg_len
            # 刚毛略向后倾斜
            bx, by = dx / seg_len * 0.3, dy / seg_len * 0.3
            self.canvas.create_line(
                x, y,
                x + ux * length + bx * length * 0.5,
                y + uy * length + by * length * 0.5,
                fill=color, width=0.7
            )

    def _draw_tegmen_realistic(self, wing, color, mid_color, edge_color, vein_color, is_left):
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

        self.canvas.create_polygon(
            wing_points, fill=color, outline="#6B3A25", width=1, smooth=True
        )

        # 外侧边缘高光带
        edge_points = []
        for i in range(n_arc // 2, n_arc + 1):
            t = math.pi * i / n_arc
            arc_x = cx + a * math.cos(t) * ux + sign * b * math.sin(t) * px
            arc_y = cy + a * math.cos(t) * uy + sign * b * math.sin(t) * py
            edge_points.append((arc_x, arc_y))
        self.canvas.create_line(edge_points, fill=edge_color, width=2, smooth=True)

        # 主翅脉：沿翅长偏外侧的 subtle 细线
        vein_t = 0.55
        vx = wing.base[0] + ux * length * vein_t
        vy = wing.base[1] + uy * length * vein_t
        vw = half_w * 0.55
        if is_left:
            v1 = (vx - px * vw, vy - py * vw)
            v2 = (vx + px * vw * 0.10, vy + py * vw * 0.10)
        else:
            v1 = (vx + px * vw, vy + py * vw)
            v2 = (vx - px * vw * 0.10, vy - py * vw * 0.10)
        self.canvas.create_line(v1, v2, fill=vein_color, width=0.6, smooth=True)

    def _draw_suture(self, data, color):
        """沿背部中线绘制左右鞘翅之间的浅色翅缝"""
        left_base = data.tegmen_left.base
        left_tip = data.tegmen_left.tip
        right_base = data.tegmen_right.base
        right_tip = data.tegmen_right.tip

        base = ((left_base[0] + right_base[0]) / 2, (left_base[1] + right_base[1]) / 2)
        tip = ((left_tip[0] + right_tip[0]) / 2, (left_tip[1] + right_tip[1]) / 2)

        self.canvas.create_line(
            base, tip, fill=color, width=1.5, smooth=True
        )

    def _draw_pronotum_realistic(self, data, color, margin_color, dark_color):
        """绘制参考照片中的前胸背板：浅橙盾形，中央深色斑块"""
        thorax = data.thorax
        size = data.body_size
        scale = data.body_scale
        angle = data.angle
        forward = (math.cos(angle), math.sin(angle))
        left = (-math.sin(angle), math.cos(angle))
        right = (math.sin(angle), -math.cos(angle))

        w = size * 0.32 * scale  # 与 THORAX_WIDTH_RATIO 保持一致
        h = size * 0.20 * scale

        # 盾形轮廓：参考照片中前胸背板呈圆润盾牌，前缘略凹
        points = [
            self._pt_offset(thorax, forward, h * 0.55, left, w * 0.25),
            self._pt_offset(thorax, forward, h * 0.40, left, w * 0.40),
            self._pt_offset(thorax, forward, h * 0.25),                       # 前缘凹刻底部
            self._pt_offset(thorax, forward, h * 0.40, right, w * 0.40),
            self._pt_offset(thorax, forward, h * 0.55, right, w * 0.25),
            self._pt_offset(thorax, forward, h * 0.05, right, w * 0.95),
            self._pt_offset(thorax, forward, -h * 0.55, right, w * 0.75),
            self._pt_offset(thorax, forward, -h * 0.75, right, w * 0.25),
            self._pt_offset(thorax, forward, -h * 0.75, left, w * 0.25),
            self._pt_offset(thorax, forward, -h * 0.55, left, w * 0.75),
            self._pt_offset(thorax, forward, h * 0.05, left, w * 0.95),
        ]

        self.canvas.create_polygon(
            points, fill=color, outline="#5C3A22", width=1, smooth=True
        )

        # 边缘浅色细边
        margin_points = [
            self._pt_offset(thorax, forward, h * 0.45, left, w * 0.18),
            self._pt_offset(thorax, forward, h * 0.32, left, w * 0.30),
            self._pt_offset(thorax, forward, h * 0.18),                       # 凹刻底部
            self._pt_offset(thorax, forward, h * 0.32, right, w * 0.30),
            self._pt_offset(thorax, forward, h * 0.45, right, w * 0.18),
            self._pt_offset(thorax, forward, -h * 0.05, right, w * 0.82),
            self._pt_offset(thorax, forward, -h * 0.62, right, w * 0.60),
            self._pt_offset(thorax, forward, -h * 0.68, right, w * 0.18),
            self._pt_offset(thorax, forward, -h * 0.68, left, w * 0.18),
            self._pt_offset(thorax, forward, -h * 0.62, left, w * 0.60),
            self._pt_offset(thorax, forward, -h * 0.05, left, w * 0.82),
        ]
        self.canvas.create_polygon(
            margin_points, fill="", outline=margin_color, width=1.5, smooth=True
        )

        # 中央深色圆盘（照片里前胸背板中部的深色"面具"）
        disk = self._pt_offset(thorax, forward, -h * 0.05)
        self._draw_ellipse(disk[0], disk[1], w * 0.32, h * 0.30,
                           fill=dark_color, outline="")

    def _draw_head_realistic(self, data, head_color, patch_color, eye_color):
        """绘制小头部，大部分被前胸背板遮盖"""
        head = data.head
        hr = data.head_radius * data.body_scale
        angle = data.angle
        forward = (math.cos(angle), math.sin(angle))
        left = (-math.sin(angle), math.cos(angle))
        right = (math.sin(angle), -math.cos(angle))

        # 头部主体（倒梯形/椭圆）
        self._draw_ellipse(head[0], head[1], hr * 0.9, hr * 0.75,
                           fill=head_color, outline="#2E1A12", width=1)

        # 前端黄色斑块
        patch = (
            head[0] + forward[0] * hr * 0.35,
            head[1] + forward[1] * hr * 0.35,
        )
        self._draw_ellipse(patch[0], patch[1], hr * 0.45, hr * 0.28,
                           fill=patch_color, outline="")

        # 小复眼
        eye_r = hr * 0.14
        eye_left = (
            head[0] + left[0] * hr * 0.55,
            head[1] + left[1] * hr * 0.55,
        )
        eye_right = (
            head[0] + right[0] * hr * 0.55,
            head[1] + right[1] * hr * 0.55,
        )
        self._draw_ellipse(eye_left[0], eye_left[1], eye_r, eye_r,
                           fill=eye_color, outline="")
        self._draw_ellipse(eye_right[0], eye_right[1], eye_r, eye_r,
                           fill=eye_color, outline="")

    def _draw_antenna_realistic(self, antenna, color):
        """绘制极细长丝状触角"""
        points = [antenna.base] + list(antenna.segments) + [antenna.tip]
        if len(points) >= 2:
            self.canvas.create_line(
                points, fill=color, width=0.8, smooth=True, splinesteps=16
            )
        self.canvas.create_oval(
            antenna.tip[0] - 0.8, antenna.tip[1] - 0.8,
            antenna.tip[0] + 0.8, antenna.tip[1] + 0.8,
            fill=color, outline=""
        )

    def _draw_hindwing(self, wing, color):
        """绘制后翅（膜质）"""
        dx = wing.tip[0] - wing.base[0]
        dy = wing.tip[1] - wing.base[1]
        length = math.hypot(dx, dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        half_w = wing.width * 0.5

        p1 = (wing.base[0] + px * half_w, wing.base[1] + py * half_w)
        p2 = (wing.base[0] - px * half_w * 0.3, wing.base[1] - py * half_w * 0.3)
        p3 = (wing.tip[0] - px * half_w * 0.5, wing.tip[1] - py * half_w * 0.5)
        p4 = (wing.tip[0], wing.tip[1])
        p5 = (wing.tip[0] + px * half_w * 0.5, wing.tip[1] + py * half_w * 0.5)

        self.canvas.create_polygon(
            [p1, p2, p3, p4, p5], fill=color, outline="#3D2618", width=1, smooth=True
        )

    # ==================== 工具方法 ====================

    def _pt_offset(self, origin, direction, distance, direction2=None, distance2=0.0):
        """从 origin 沿 direction 偏移，可选叠加第二方向"""
        x = origin[0] + direction[0] * distance
        y = origin[1] + direction[1] * distance
        if direction2 is not None:
            x += direction2[0] * distance2
            y += direction2[1] * distance2
        return (x, y)

    def _get_wrap_offsets(self, data, screen_w, screen_h):
        """
        根据蟑螂与屏幕边缘的距离，计算需要绘制的幽灵副本偏移量

        仅在蟑螂靠近某条边界时才生成对应偏移，避免画面中央时无效绘制。

        Returns:
            List[Tuple[float, float]]: 各幽灵副本相对本体的 (dx, dy) 列表
        """
        # 可视半径：覆盖身体、腿、触角的大致范围
        radius = data.head_radius * 7

        dx_list = []
        if data.x < radius:
            dx_list.append(screen_w)
        if data.x > screen_w - radius:
            dx_list.append(-screen_w)

        dy_list = []
        if data.y < radius:
            dy_list.append(screen_h)
        if data.y > screen_h - radius:
            dy_list.append(-screen_h)

        offsets = []
        for dx in dx_list:
            offsets.append((dx, 0.0))
        for dy in dy_list:
            offsets.append((0.0, dy))
        for dx in dx_list:
            for dy in dy_list:
                offsets.append((dx, dy))

        return offsets

    @staticmethod
    def _translate_render_data(data, dx, dy):
        """
        平移渲染数据所有坐标，生成屏幕环绕所需的幽灵副本

        通过递归遍历 dataclass 的字段，平移所有二维数值元组坐标，
        保留标量、字符串等其他字段不变。

        Args:
            data: CockroachRenderData 实例
            dx, dy: X/Y 方向偏移量

        Returns:
            平移后的 CockroachRenderData 新实例
        """
        def _translate(obj):
            if is_dataclass(obj):
                changes = {}
                for f in fields(obj):
                    changes[f.name] = _translate(getattr(obj, f.name))
                return replace(obj, **changes)
            if isinstance(obj, tuple):
                # 二维数值元组视为坐标点进行平移
                if len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj):
                    return (obj[0] + dx, obj[1] + dy)
                return tuple(_translate(v) for v in obj)
            if isinstance(obj, list):
                return [_translate(v) for v in obj]
            return obj

        return _translate(data)
