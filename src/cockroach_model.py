"""
cockroach_model.py
蟑螂几何模型 - 根据位置、朝向、状态计算所有身体部位的渲染坐标
包含完整的解剖结构：头、胸、腹、触角、六条腿、鞘翅、后翅、尾须
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ---------- 渲染数据结构 ----------

@dataclass
class AntennaData:
    """单根触角的渲染数据"""
    base: Tuple[float, float]  # 触角基部
    segments: List[Tuple[float, float]]  # 各节坐标（从基部到末端）
    tip: Tuple[float, float]  # 末端


@dataclass
class LegData:
    """单条腿的渲染数据"""
    coxa: Tuple[float, float]  # 基节（连接身体）
    femur: Tuple[float, float]  # 腿节
    tibia: Tuple[float, float]  # 胫节
    tarsus: Tuple[float, float]  # 跗节（足尖）
    side: str  # "left" 或 "right"


@dataclass
class WingData:
    """翅膀的渲染数据"""
    base: Tuple[float, float]  # 翅基
    tip: Tuple[float, float]  # 翅尖
    width: float  # 翅宽
    span_angle: float  # 展开角度（0=折叠，>0=展开）


@dataclass
class CockroachRenderData:
    """每帧给前端的完整渲染数据"""
    # 基础位置
    x: float  # 身体中心 X
    y: float  # 身体中心 Y
    angle: float  # 身体朝向（弧度，0=右，顺时针）

    # 身体三段
    head: Tuple[float, float]  # 头部中心
    thorax: Tuple[float, float]  # 胸部中心（前胸背板）
    abdomen: Tuple[float, float]  # 腹部中心

    # 身体轮廓关键点（供绘制椭圆/形状用）
    body_outline: List[Tuple[float, float]]  # 身体轮廓多边形

    # 头部细节
    head_radius: float  # 头部半径
    body_size: float  # 身体基准长度（供前端按比例绘制）
    eye_left: Tuple[float, float]  # 左复眼
    eye_right: Tuple[float, float]  # 右复眼

    # 触角
    antenna_left: AntennaData
    antenna_right: AntennaData

    # 六条腿
    legs: List[LegData]  # [左前, 右前, 左中, 右中, 左后, 右后]

    # 翅膀
    tegmen_left: WingData  # 左鞘翅（前翅，硬化）
    tegmen_right: WingData  # 右鞘翅
    hindwing_left: WingData  # 左后翅（膜质）
    hindwing_right: WingData  # 右后翅

    # 尾须
    cercus_left: Tuple[float, float]  # 左尾须末端
    cercus_right: Tuple[float, float]  # 右尾须末端

    # 动画参数
    legs_phase: float  # 腿摆动相位 0~2π
    antenna_phase: float  # 触角摆动相位 0~2π
    body_scale: float  # 身体缩放系数
    abdomen_wave: float  # 腹部波动相位

    # 状态
    is_scared: bool  # 是否惊吓
    wing_flutter: float  # 翅膀颤动强度 0~1

    # 空间设置
    wrap_screen: bool = False  # 是否开启屏幕环绕


# ---------- 蟑螂模型类 ----------

class CockroachModel:
    """
    蟑螂几何模型

    根据物理状态（位置、朝向、速度）计算所有身体部位的渲染坐标。
    包含完整的蟑螂解剖结构：

    - 头部：头壳 + 复眼 + 口器方向
    - 胸部：前胸背板（盾状）
    - 腹部：分节，有波动动画
    - 触角：丝状，多节，独立摆动
    - 六条腿：前/中/后足，各有基节-腿节-胫节-跗节
    - 鞘翅：硬化前翅，覆盖腹部背面
    - 后翅：膜质，折叠于鞘翅下，惊吓时展开
    - 尾须：腹部末端一对感觉附肢
    """

    # 身体比例常量（以 body_size 为基准）
    # body_size = 胸部到腹部末端的长度
    # 参照美洲大蠊形态：修长身体、小头、宽大前胸背板、长尾须
    HEAD_RATIO = 0.12  # 头部半径比例（更小，符合真实蟑螂头小腹大）
    THORAX_LENGTH_RATIO = 0.20  # 胸部（前胸背板）长度
    ABDOMEN_LENGTH_RATIO = 0.80  # 腹部长度（写实修长）
    ABDOMEN_WIDTH_RATIO = 0.34  # 腹部最宽处（位于腹部前端）
    ABDOMEN_REAR_WIDTH_RATIO = 0.22  # 腹部末端宽度（向后明显收细）
    THORAX_WIDTH_RATIO = 0.32  # 胸部宽度（收窄）
    JUNCTION_WIDTH_RATIO = 0.36  # 胸腹交界宽度（略窄，但仍大于胸部）

    # 触角比例
    ANTENNA_LENGTH_RATIO = 3.8  # 触角总长（参考照片中触角极长，远超身体）
    ANTENNA_SEGMENTS = 14  # 触角节数（更细腻）
    ANTENNA_SPREAD_ANGLE = 0.35  # 两根触角间夹角（弧度，更平行）

    # 腿部比例
    LEG_COXA_RATIO = 0.08  # 基节
    LEG_FEMUR_RATIO = 0.32  # 腿节（参考照片中腿较长）
    LEG_TIBIA_RATIO = 0.30  # 胫节
    LEG_TARSUS_RATIO = 0.22  # 跗节

    # 翅膀比例
    TEGMEN_LENGTH_RATIO = 0.92  # 鞘翅长度（参考照片中几乎覆盖整个腹部）
    TEGMEN_WIDTH_RATIO = 0.58  # 鞘翅宽度（覆盖加宽后的背部两侧）
    HINDWING_LENGTH_RATIO = 0.70  # 后翅长度（展开时）
    HINDWING_WIDTH_RATIO = 0.30  # 后翅宽度

    # 尾须
    CERCUS_LENGTH_RATIO = 0.22
    CERCUS_SPREAD = 0.30  # 尾须间夹角（弧度，略收拢）

    def __init__(self, body_size: float = 40):
        """
        Args:
            body_size: 身体总长（头到腹部末端，像素）
        """
        self.body_size = body_size
        self._legs_phase = 0.0
        self._antenna_phase = 0.0
        self._abdomen_wave = 0.0
        self._wing_flutter_target = 0.0
        self._wing_flutter_current = 0.0
        self._activity = 1.0

        # 随机种子（让每只蟑螂的微小差异）
        self._seed_offset = random.uniform(0, 2 * math.pi)

        # 每条腿独立的随机相位扰动，模拟真实昆虫不规则高频率摆腿
        self._leg_noise_phase = [random.uniform(0, 2 * math.pi) for _ in range(6)]
        self._leg_noise_rate = [random.uniform(2.0, 5.0) for _ in range(6)]

        # 打破左右对称：每条腿独立的基础相位偏移、频率系数、振幅系数
        # 数值范围较大，确保左右足摆动差异肉眼可见
        self._leg_base_phase_offset = [random.uniform(-0.65, 0.65) for _ in range(6)]
        self._leg_freq_noise = [random.uniform(0.78, 1.22) for _ in range(6)]
        self._leg_amp_noise = [random.uniform(0.70, 1.35) for _ in range(6)]

        # 上帧朝向，用于内部估算转向速率；None 表示尚未记录
        self._last_angle = None

    def compute(
            self,
            x: float,
            y: float,
            angle: float,
            speed: float,
            dt: float,
            is_scared: bool,
            turn_rate: float = 0.0,
            is_observing: bool = False,
    ) -> CockroachRenderData:
        """
        根据物理状态计算所有渲染坐标

        Args:
            x, y: 身体中心坐标
            angle: 身体朝向（弧度，0=右）
            speed: 当前速率（像素/秒）
            dt: 帧间隔
            is_scared: 是否处于惊吓状态
            turn_rate: 转向速率（弧度/秒），正值为逆时针；用于让内外侧足摆动不对称
            is_observing: 是否处于观察状态（原地休息探测，触角更活跃）

        Returns:
            完整的 CockroachRenderData
        """
        size = self.body_size
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # 方向向量
        forward = (cos_a, sin_a)  # 头朝向
        backward = (-cos_a, -sin_a)  # 尾朝向
        left = (-sin_a, cos_a)  # 左侧
        right = (sin_a, -cos_a)  # 右侧

        # ---- 更新动画相位 ----
        # 整体活跃度：速度越低动作越轻微，静止时仍有微小感知动作
        activity = 0.25 + 0.75 * min(speed / 80.0, 1.0)
        # 观察状：身体静止但触角活跃探测（相当于中速移动的活跃度）
        if is_observing:
            activity = max(activity, 0.75)
        self._activity = activity

        # 若调用方未提供转向速率，内部用朝向差分估算
        if abs(turn_rate) < 1e-6 and dt > 1e-6 and self._last_angle is not None:
            raw_turn = angle - self._last_angle
            while raw_turn > math.pi:
                raw_turn -= 2 * math.pi
            while raw_turn < -math.pi:
                raw_turn += 2 * math.pi
            turn_rate = raw_turn / dt
        self._last_angle = angle

        # 腿摆动：速率越快摆动越快，基础频率更高；静止时基本不动
        leg_speed_factor = min(speed / 120.0, 3.5)
        self._legs_phase += leg_speed_factor * 14.0 * dt
        self._legs_phase %= 2 * math.pi

        # 更新每条腿独立的随机扰动相位
        for i in range(6):
            self._leg_noise_phase[i] += self._leg_noise_rate[i] * dt
            self._leg_noise_phase[i] %= 2 * math.pi

        # 触角摆动：与活跃度挂钩，静止时缓慢轻摆；移动时更活跃
        self._antenna_phase += activity * (3.5 + random.uniform(-0.5, 0.5)) * dt
        self._antenna_phase %= 2 * math.pi

        # 腹部波动
        self._abdomen_wave += (0.4 + leg_speed_factor * 2.0) * dt
        self._abdomen_wave %= 2 * math.pi

        # 翅膀颤动（惊吓时快速颤动）
        self._wing_flutter_target = 1.0 if is_scared else 0.0
        flutter_speed = 15.0 if is_scared else 5.0
        self._wing_flutter_current += (
                (self._wing_flutter_target - self._wing_flutter_current) * flutter_speed * dt
        )

        # ---- 身体三段中心点 ----
        thorax_length = size * self.THORAX_LENGTH_RATIO
        abdomen_length = size * self.ABDOMEN_LENGTH_RATIO

        # 身体中心在胸部和腹部交界处偏前
        thorax_center = self._offset((x, y), forward, thorax_length * 0.6)
        abdomen_center = self._offset((x, y), backward, abdomen_length * 0.5)
        head_center = self._offset((x, y), forward, thorax_length * 0.6 + size * self.HEAD_RATIO * 0.7)

        head_radius = size * self.HEAD_RATIO

        # ---- 身体轮廓 ----
        body_outline = self._compute_body_outline(
            x, y, angle, size, thorax_center, abdomen_center, head_center, head_radius
        )

        # ---- 眼睛 ----
        eye_offset_forward = head_radius * 0.4
        eye_offset_side = head_radius * 0.6
        eye_left = self._offset(
            self._offset(head_center, forward, eye_offset_forward),
            left, eye_offset_side
        )
        eye_right = self._offset(
            self._offset(head_center, forward, eye_offset_forward),
            right, eye_offset_side
        )

        # ---- 触角 ----
        antenna_left = self._compute_antenna(
            head_center, angle, left, head_radius, self._antenna_phase, is_scared, self._activity
        )
        antenna_right = self._compute_antenna(
            head_center, angle, right, head_radius,
            self._antenna_phase + math.pi * 0.3, is_scared, self._activity  # 左右不同步
        )

        # ---- 六条腿 ----
        legs = self._compute_legs(
            thorax_center, abdomen_center, x, y,
            angle, left, right, size, speed, is_scared, turn_rate
        )

        # ---- 翅膀 ----
        tegmen_left, tegmen_right = self._compute_tegmina(
            thorax_center, abdomen_center, angle, left, right, size
        )
        hindwing_left, hindwing_right = self._compute_hindwings(
            thorax_center, abdomen_center, angle, left, right, size, is_scared
        )

        # ---- 尾须 ----
        abdomen_tip = self._offset(abdomen_center, backward, abdomen_length * 0.5)
        cercus_base = self._offset(abdomen_tip, backward, size * 0.05)
        # 尾须指向后方略向外
        cercus_left = self._offset(cercus_base,
                                   (-cos_a * 0.7 - sin_a * 0.3, -sin_a * 0.7 + cos_a * 0.3),
                                   size * self.CERCUS_LENGTH_RATIO)
        cercus_right = self._offset(cercus_base,
                                    (-cos_a * 0.7 + sin_a * 0.3, -sin_a * 0.7 - cos_a * 0.3),
                                    size * self.CERCUS_LENGTH_RATIO)

        # ---- 身体缩放 ----
        body_scale = 1.0
        if is_scared:
            # 惊吓时身体微微膨胀
            body_scale = 1.08 + math.sin(self._abdomen_wave * 3) * 0.03

        return CockroachRenderData(
            x=x, y=y, angle=angle,
            head=head_center,
            thorax=thorax_center,
            abdomen=abdomen_center,
            body_outline=body_outline,
            head_radius=head_radius,
            body_size=size,
            eye_left=eye_left, eye_right=eye_right,
            antenna_left=antenna_left,
            antenna_right=antenna_right,
            legs=legs,
            tegmen_left=tegmen_left,
            tegmen_right=tegmen_right,
            hindwing_left=hindwing_left,
            hindwing_right=hindwing_right,
            cercus_left=cercus_left,
            cercus_right=cercus_right,
            legs_phase=self._legs_phase,
            antenna_phase=self._antenna_phase,
            body_scale=body_scale,
            abdomen_wave=self._abdomen_wave,
            is_scared=is_scared,
            wing_flutter=self._wing_flutter_current,
        )

    def _offset(
            self, origin: Tuple[float, float],
            direction: Tuple[float, float],
            distance: float,
            direction2: Optional[Tuple[float, float]] = None,
            distance2: float = 0.0
    ) -> Tuple[float, float]:
        """从 origin 沿 direction 偏移 distance，可选叠加第二方向偏移"""
        x = origin[0] + direction[0] * distance
        y = origin[1] + direction[1] * distance
        if direction2 is not None:
            x += direction2[0] * distance2
            y += direction2[1] * distance2
        return (x, y)

    def _compute_body_outline(
            self, x, y, angle, size,
            thorax_center, abdomen_center, head_center, head_radius
    ) -> List[Tuple[float, float]]:
        """
        计算圆滑饱满的身体轮廓（胶囊状椭圆背部）。

        参考真实美洲大蠊俯视形态：背部是一个从前胸背板向后延伸的饱满长椭圆，
        侧面线条连续无棱角，类似把棕色椭圆阴影绑定到躯干骨骼上。
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        forward = (cos_a, sin_a)
        left = (-sin_a, cos_a)
        right = (sin_a, -cos_a)
        backward = (-cos_a, -sin_a)

        thorax_width = size * self.THORAX_WIDTH_RATIO
        junction_width = size * self.JUNCTION_WIDTH_RATIO
        abdomen_width = size * self.ABDOMEN_WIDTH_RATIO
        abdomen_rear_width = size * self.ABDOMEN_REAR_WIDTH_RATIO
        abdomen_length = size * self.ABDOMEN_LENGTH_RATIO
        thorax_length = size * self.THORAX_LENGTH_RATIO

        # 躯干中轴：从头部前端到腹部末端
        head_front = self._offset(head_center, forward, head_radius * 0.85)
        abdomen_tip = self._offset(abdomen_center, backward, abdomen_length * 0.52)
        axis_dx = abdomen_tip[0] - head_front[0]
        axis_dy = abdomen_tip[1] - head_front[1]
        axis_len = math.hypot(axis_dx, axis_dy)
        if axis_len < 1e-6:
            axis_len = 1e-6

        def axis_point(t: float) -> Tuple[float, float]:
            """沿躯干中轴参数 t=0（头部）到 t=1（腹部末端）取点"""
            return (head_front[0] + axis_dx * t, head_front[1] + axis_dy * t)

        def half_width(t: float) -> float:
            """沿中轴的半宽度轮廓：胸窄、交界略宽、腹前宽后窄"""
            if t < 0.08:
                # 头部前端：尖圆
                local = t / 0.08
                return head_radius * 0.50 * local
            elif t < 0.22:
                # 颈部：明显收细
                local = (t - 0.08) / 0.14
                return head_radius * 0.50 + (thorax_width * 0.45 - head_radius * 0.50) * math.sin(local * math.pi * 0.5)
            elif t < 0.35:
                # 前胸背板：迅速放宽到胸部宽度
                local = (t - 0.22) / 0.13
                return thorax_width * 0.45 + (thorax_width - thorax_width * 0.45) * math.sin(local * math.pi * 0.5)
            elif t < 0.45:
                # 胸腹交界：从胸部宽度过渡到略宽的交界
                local = (t - 0.35) / 0.10
                return thorax_width + (junction_width - thorax_width) * math.sin(local * math.pi * 0.5)
            elif t < 0.58:
                # 腹部前端：从交界略微放宽到腹部最大宽度
                local = (t - 0.45) / 0.13
                return junction_width + (abdomen_width - junction_width) * math.sin(local * math.pi * 0.5)
            elif t < 0.90:
                # 腹部主体：从前端最大宽度向尾部明显收细
                local = (t - 0.58) / 0.32
                return abdomen_width - (abdomen_width - abdomen_rear_width) * math.sin(local * math.pi * 0.5)
            else:
                # 腹部末端：尖圆收尾
                local = (t - 0.90) / 0.10
                return abdomen_rear_width * (1.0 - local * local * (3.0 - 2.0 * local))

        n_segments = 18
        points: List[Tuple[float, float]] = []

        # 左侧轮廓（从头到尾）
        for i in range(n_segments + 1):
            t = i / n_segments
            center = axis_point(t)
            w = half_width(t)
            points.append((center[0] + left[0] * w, center[1] + left[1] * w))

        # 右侧轮廓（从尾到头）
        for i in range(n_segments, -1, -1):
            t = i / n_segments
            center = axis_point(t)
            w = half_width(t)
            points.append((center[0] + right[0] * w, center[1] + right[1] * w))

        return points

    def _compute_antenna(
            self, head_center, body_angle, side_dir,
            head_radius, phase, is_scared, activity: float
    ) -> AntennaData:
        """
        计算单根触角

        采用双谐波叠加 + 鞭子效应（根部摆幅小、尖端大）+ 每节随机扰动 +
        速度感应后飘（活跃度高时触角尖端向后偏，模拟空气阻力），
        使触角运动自然灵活、不机械。
        """
        size = self.body_size
        antenna_length = size * self.ANTENNA_LENGTH_RATIO
        n_segments = self.ANTENNA_SEGMENTS
        segment_length = antenna_length / n_segments

        # 触角基部在头部前端偏侧
        forward = (math.cos(body_angle), math.sin(body_angle))
        base = (
            head_center[0] + forward[0] * head_radius * 0.7 + side_dir[0] * head_radius * 0.35,
            head_center[1] + forward[1] * head_radius * 0.7 + side_dir[1] * head_radius * 0.35,
        )

        # 触角初始方向：前方略偏侧
        spread_angle = self.ANTENNA_SPREAD_ANGLE
        if side_dir[0] * forward[0] + side_dir[1] * forward[1] < 0:
            # 右侧
            init_angle = body_angle - spread_angle / 2
        else:
            init_angle = body_angle + spread_angle / 2

        segments = []
        current = base

        for i in range(n_segments):
            t = i / n_segments
            # 第一谐波：基础传播波（沿触角根部→尖端传播）
            wave1 = math.sin(phase + t * 3.5) * 0.18
            # 第二谐波：不同频率与相位，增加运动不规律性
            wave2 = math.sin(phase * 1.4 + t * 2.2 + 0.7) * 0.12
            # 鞭子效应：根部摆幅小、尖端大（平方放大）
            tip_amp = 0.3 + t * t * 0.9
            wave = (wave1 + wave2) * tip_amp * activity
            # 每节微小随机扰动（模拟触角颤动）
            wave += random.uniform(-0.025, 0.025)
            # 速度感应后飘：越靠尖端越明显，模拟空气阻力
            speed_drag = -activity * t * 0.22

            if is_scared:
                # 惊吓时触角后贴
                wave *= 0.4
                seg_angle = init_angle + wave * 0.3 - spread_angle * 0.5 + speed_drag
            else:
                seg_angle = init_angle + wave + speed_drag

            next_pt = (
                current[0] + math.cos(seg_angle) * segment_length,
                current[1] + math.sin(seg_angle) * segment_length,
            )
            segments.append(next_pt)
            current = next_pt

        return AntennaData(
            base=base,
            segments=segments[:-1] if len(segments) > 1 else [],
            tip=segments[-1] if segments else base,
        )

    def _compute_legs(
            self, thorax_center, abdomen_center, body_center_x, body_center_y,
            body_angle, left_dir, right_dir, size, speed, is_scared, turn_rate
    ) -> List[LegData]:
        """计算全部六条腿"""
        legs = []

        # 腿的附着点：前足在胸部，中足在胸腹交界，后足在腹部前段
        forward = (math.cos(body_angle), math.sin(body_angle))
        backward = (-forward[0], -forward[1])

        # 三对足的附着点（身体坐标，左右对称）
        # 每个元素: (附着点坐标, 侧向宽度)
        # 侧向宽度决定腿基部离身体的距离：蟑螂腿基部紧贴身体，不像螃蟹外撇
        attachment_pairs = [
            (self._offset(thorax_center, forward, size * 0.08),
             size * self.THORAX_WIDTH_RATIO * 0.50),   # 前足
            ((body_center_x, body_center_y),
             size * self.ABDOMEN_WIDTH_RATIO * 0.55),  # 中足
            (self._offset(abdomen_center, forward, size * 0.05),
             size * self.ABDOMEN_WIDTH_RATIO * 0.48),   # 后足
        ]

        for pair_idx, (att_point, att_width) in enumerate(attachment_pairs):
            # 左腿基节
            left_coxa = (
                att_point[0] + left_dir[0] * att_width,
                att_point[1] + left_dir[1] * att_width,
            )
            legs.append(self._compute_single_leg(
                left_coxa, body_angle, left_dir, size,
                pair_idx, "left", speed, is_scared, turn_rate
            ))

            # 右腿基节
            right_coxa = (
                att_point[0] + right_dir[0] * att_width,
                att_point[1] + right_dir[1] * att_width,
            )
            legs.append(self._compute_single_leg(
                right_coxa, body_angle, right_dir, size,
                pair_idx, "right", speed, is_scared, turn_rate
            ))

        return legs

    def _compute_single_leg(
            self, coxa, body_angle, side_dir,
            size, pair_index, side, speed, is_scared, turn_rate
    ) -> LegData:
        """计算单条腿的关节坐标（前/中/后足形态差异，左右独立、转向相关）"""
        femur_len = size * self.LEG_FEMUR_RATIO
        tibia_len = size * self.LEG_TIBIA_RATIO
        tarsus_len = size * self.LEG_TARSUS_RATIO

        leg_index = pair_index * 2 + (0 if side == "left" else 1)
        noise_phase = self._leg_noise_phase[leg_index]
        base_phase_offset = self._leg_base_phase_offset[leg_index]
        freq_noise = self._leg_freq_noise[leg_index]
        amp_noise = self._leg_amp_noise[leg_index]

        # 侧向符号：left=+1, right=-1；转向符号
        sign = 1 if side == "left" else -1
        turn_sign = 1.0 if turn_rate > 0 else (-1.0 if turn_rate < 0 else 0.0)

        # 打破严格左右对称：同侧三足大致交替，对侧不再严格反相
        # 而是叠加独立随机基础相位偏移，使六条腿形成近似但不规则的步态
        phase_offset = pair_index * math.pi * 2 / 3 + base_phase_offset
        if side == "right":
            phase_offset += math.pi + sign * 0.18  # 右腿整体错开，并带微小偏置

        # 每条腿使用略有差异的有效频率，进一步消除机械同步感
        effective_phase = self._legs_phase * freq_noise + phase_offset

        # 基础摆动 + 每条腿独立的高频不规则扰动 + 随机振幅抖动
        base_swing = math.sin(effective_phase)
        # 高频扰动：叠加 2.7 倍频与 4.1 倍频的小幅正弦，模拟昆虫快速细碎步态
        irregular_swing = (
            0.18 * math.sin(effective_phase * 2.7 + noise_phase) +
            0.08 * math.sin(effective_phase * 4.1 + noise_phase * 1.3)
        )
        # 随机振幅：让每条腿每次摆动幅度略有差异
        amp_jitter = (0.92 + 0.16 * math.sin(noise_phase * 0.7)) * amp_noise
        swing = (base_swing + irregular_swing) * amp_jitter

        # 根据足对确定基准朝向（俯视平面）
        # 蟑螂腿呈辐射状但不像螃蟹纯侧向：前足偏前、中足略偏后、后足明显向后
        if pair_index == 0:          # 前足：向前外侧约 35°，贴近参考照片
            base_angle = body_angle + sign * math.pi / 5.1
        elif pair_index == 1:        # 中足：向后外侧约 80°，避免正侧向的螃蟹感
            base_angle = body_angle + sign * math.pi / 2.25
        else:                        # 后足：明显向后外侧约 130°
            base_angle = body_angle + sign * math.pi / 1.38

        # 速度越快摆幅越大；静止时保持自然微颤
        speed_amp = 0.25 + 0.24 * min(speed / 150.0, 1.0)

        # ---- 转向调制：让腿部摆动与身体姿态调整强相关 ----
        # 外侧足（转向方向同侧）承担主要推进，摆幅明显加大并向外伸展
        # 内侧足（转向方向对侧）作为支点，摆幅明显减小并略向内收
        turn_magnitude = min(abs(turn_rate) / 2.2, 1.0)  # 归一化转向强度
        is_outer = (sign == turn_sign)
        if is_outer:
            turn_amp_boost = 1.0 + turn_magnitude * 0.90
            turn_angle_push = sign * turn_magnitude * 0.32
        else:
            turn_amp_boost = 1.0 - turn_magnitude * 0.40
            turn_angle_push = -sign * turn_magnitude * 0.18

        # 速度越高，转向对腿的影响越明显
        speed_turn_coupling = min(speed / 100.0, 1.0)
        turn_amp_boost = 1.0 + (turn_amp_boost - 1.0) * speed_turn_coupling
        turn_angle_push *= speed_turn_coupling

        # 综合振幅
        final_amp = speed_amp * turn_amp_boost

        # 腿节向外伸展，带前后摆动
        femur_angle = base_angle + swing * final_amp + turn_angle_push
        femur = (
            coxa[0] + math.cos(femur_angle) * femur_len,
            coxa[1] + math.sin(femur_angle) * femur_len,
        )

        # 胫节从腿节末端向身体中线回折，形成明显的膝状弯曲
        knee_bend = -0.55 if side == "left" else 0.55
        tibia_angle = femur_angle + knee_bend + swing * (final_amp * 0.45)
        tibia = (
            femur[0] + math.cos(tibia_angle) * tibia_len,
            femur[1] + math.sin(tibia_angle) * tibia_len,
        )

        # 跗节继续向下/向外延伸，末端着地
        tarsus_angle = tibia_angle + knee_bend * 0.25
        tarsus = (
            tibia[0] + math.cos(tarsus_angle) * tarsus_len,
            tibia[1] + math.sin(tarsus_angle) * tarsus_len,
        )

        if is_scared:
            # 惊吓时足尖内收
            tarsus = (
                tarsus[0] - side_dir[0] * tarsus_len * 0.25,
                tarsus[1] - side_dir[1] * tarsus_len * 0.25,
            )

        return LegData(
            coxa=coxa, femur=femur, tibia=tibia,
            tarsus=tarsus, side=side,
        )

    def _compute_tegmina(
            self, thorax_center, abdomen_center, body_angle,
            left_dir, right_dir, size
    ) -> Tuple[WingData, WingData]:
        """计算鞘翅（前翅）"""
        tegmen_length = size * self.TEGMEN_LENGTH_RATIO
        tegmen_width = size * self.TEGMEN_WIDTH_RATIO
        backward = (-math.cos(body_angle), -math.sin(body_angle))

        # 翅基在胸腹交界
        wing_base_offset = (
            thorax_center[0] * 0.3 + abdomen_center[0] * 0.7,
            thorax_center[1] * 0.3 + abdomen_center[1] * 0.7,
        )

        # 鞘翅向后方延伸，尖端落在背中线上（左右翅在翅缝处相接）
        left_tip = (
            wing_base_offset[0] + backward[0] * tegmen_length,
            wing_base_offset[1] + backward[1] * tegmen_length,
        )
        right_tip = (
            wing_base_offset[0] + backward[0] * tegmen_length,
            wing_base_offset[1] + backward[1] * tegmen_length,
        )

        # 鞘翅基部落在背中线上，与对侧翅相接
        left_base = wing_base_offset
        right_base = wing_base_offset

        return (
            WingData(base=left_base, tip=left_tip, width=tegmen_width, span_angle=0),
            WingData(base=right_base, tip=right_tip, width=tegmen_width, span_angle=0),
        )

    def _compute_hindwings(
            self, thorax_center, abdomen_center, body_angle,
            left_dir, right_dir, size, is_scared
    ) -> Tuple[WingData, WingData]:
        """计算后翅（膜质翅）"""
        hindwing_length = size * self.HINDWING_LENGTH_RATIO
        hindwing_width = size * self.HINDWING_WIDTH_RATIO
        backward = (-math.cos(body_angle), -math.sin(body_angle))

        # 翅基（在鞘翅下方）
        wing_base = (
            thorax_center[0] * 0.35 + abdomen_center[0] * 0.65,
            thorax_center[1] * 0.35 + abdomen_center[1] * 0.65,
        )

        # 展开角度：惊吓时展开
        if is_scared:
            span_angle = 0.8 + self._wing_flutter_current * 0.4  # 展开约45-70度
        else:
            span_angle = 0.05  # 折叠

        left_tip = (
            wing_base[0] + backward[0] * hindwing_length * math.cos(span_angle)
            + left_dir[0] * hindwing_width * math.sin(span_angle),
            wing_base[1] + backward[1] * hindwing_length * math.cos(span_angle)
            + left_dir[1] * hindwing_width * math.sin(span_angle),
        )
        right_tip = (
            wing_base[0] + backward[0] * hindwing_length * math.cos(span_angle)
            + right_dir[0] * hindwing_width * math.sin(span_angle),
            wing_base[1] + backward[1] * hindwing_length * math.cos(span_angle)
            + right_dir[1] * hindwing_width * math.sin(span_angle),
        )

        # 翅基
        left_base = (
            wing_base[0] + left_dir[0] * hindwing_width * 0.15,
            wing_base[1] + left_dir[1] * hindwing_width * 0.15,
        )
        right_base = (
            wing_base[0] + right_dir[0] * hindwing_width * 0.15,
            wing_base[1] + right_dir[1] * hindwing_width * 0.15,
        )

        return (
            WingData(base=left_base, tip=left_tip, width=hindwing_width, span_angle=span_angle),
            WingData(base=right_base, tip=right_tip, width=hindwing_width, span_angle=span_angle),
        )

    def update_size(self, new_size: float):
        """更新身体大小"""
        self.body_size = max(10, min(200, new_size))


# ---------- 简易测试 ----------
if __name__ == "__main__":
    model = CockroachModel(body_size=40)

    print("=== 蟑螂模型测试 ===\n")

    # 模拟静止状态
    data = model.compute(
        x=500, y=400, angle=0.3, speed=0, dt=0.016, is_scared=False
    )

    print("【静止状态】")
    print(f"  身体中心: ({data.x:.0f}, {data.y:.0f})")
    print(f"  朝向: {data.angle:.2f} rad")
    print(f"  头部: ({data.head[0]:.0f}, {data.head[1]:.0f})")
    print(f"  胸部: ({data.thorax[0]:.0f}, {data.thorax[1]:.0f})")
    print(f"  腹部: ({data.abdomen[0]:.0f}, {data.abdomen[1]:.0f})")
    print(f"  身体轮廓: {len(data.body_outline)} 个顶点")
    print(f"  左触角节数: {len(data.antenna_left.segments)}")
    print(f"  腿数量: {len(data.legs)}")
    print(f"  左鞘翅: base=({data.tegmen_left.base[0]:.0f},{data.tegmen_left.base[1]:.0f})")
    print(f"  后翅展开角: 左={data.hindwing_left.span_angle:.2f}, 右={data.hindwing_right.span_angle:.2f}")
    print(f"  尾须: 左=({data.cercus_left[0]:.0f},{data.cercus_left[1]:.0f})")

    # 模拟惊吓状态
    data_scared = model.compute(
        x=500, y=400, angle=0.3, speed=300, dt=0.016, is_scared=True
    )

    print("\n【惊吓状态】")
    print(f"  后翅展开角: 左={data_scared.hindwing_left.span_angle:.2f}")
    print(f"  翅膀颤动: {data_scared.wing_flutter:.2f}")
    print(f"  身体缩放: {data_scared.body_scale:.2f}")

    # 模拟移动
    print("\n【移动动画测试 - 5帧】")
    for i in range(5):
        d = model.compute(
            x=500 + i * 20, y=400, angle=0.0, speed=150, dt=0.016, is_scared=False
        )
        print(f"  帧{i}: legs_phase={d.legs_phase:.2f}, "
              f"腿0足尖=({d.legs[0].tarsus[0]:.0f},{d.legs[0].tarsus[1]:.0f})")
