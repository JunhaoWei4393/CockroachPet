"""
physics_engine.py
纯物理计算模块 - 速度、加速度、阻尼、边界处理
不涉及任何行为逻辑和几何细节
"""

import math
from typing import Optional, Tuple


class Vector2:
    """二维向量，用于内部物理计算"""

    __slots__ = ('x', 'y')

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> 'Vector2':
        if scalar == 0:
            return Vector2()
        return Vector2(self.x / scalar, self.y / scalar)

    def __iadd__(self, other: 'Vector2') -> 'Vector2':
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other: 'Vector2') -> 'Vector2':
        self.x -= other.x
        self.y -= other.y
        return self

    def length(self) -> float:
        """向量长度"""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        """向量长度的平方（避免开方，用于比较）"""
        return self.x * self.x + self.y * self.y

    def normalize(self) -> 'Vector2':
        """返回单位向量"""
        length = self.length()
        if length == 0:
            return Vector2()
        return Vector2(self.x / length, self.y / length)

    def dot(self, other: 'Vector2') -> float:
        """点积"""
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: 'Vector2') -> float:
        """到另一个向量的距离"""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def angle(self) -> float:
        """向量角度（弧度，0=右，正值=顺时针）"""
        return math.atan2(self.y, self.x)

    @staticmethod
    def from_angle(angle: float, length: float = 1.0) -> 'Vector2':
        """从角度创建向量"""
        return Vector2(math.cos(angle) * length, math.sin(angle) * length)

    def rotate(self, angle: float) -> 'Vector2':
        """旋转向量"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vector2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

    def clamp_length(self, max_length: float) -> 'Vector2':
        """限制向量长度"""
        if self.length_squared() > max_length * max_length:
            return self.normalize() * max_length
        return Vector2(self.x, self.y)

    def lerp(self, target: 'Vector2', t: float) -> 'Vector2':
        """线性插值"""
        return Vector2(
            self.x + (target.x - self.x) * t,
            self.y + (target.y - self.y) * t
        )

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @staticmethod
    def from_tuple(t: Tuple[float, float]) -> 'Vector2':
        return Vector2(t[0], t[1])

    def copy(self) -> 'Vector2':
        return Vector2(self.x, self.y)

    def __repr__(self) -> str:
        return f"Vector2({self.x:.2f}, {self.y:.2f})"


class PhysicsBody:
    """单个物体的物理状态"""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.position = Vector2(x, y)
        self.velocity = Vector2(0.0, 0.0)
        self.acceleration = Vector2(0.0, 0.0)
        self.previous_position = Vector2(x, y)  # 上一帧位置，用于计算朝向

        # 转弯模型新增状态
        self.orientation = 0.0          # 身体朝向（弧度，0=右）
        self.angular_velocity = 0.0     # 朝向角速度（弧度/秒）
        self.forward_speed = 0.0        # 沿朝向的前进速度（像素/秒，可负）


class PhysicsEngine:
    """
    纯物理引擎 - 采用“汽车/昆虫式转弯模型”

    核心变更：
    - 物体有固定的身体朝向 orientation
    - 行为层提供目标朝向（舵角）和前进油门 thrust
    - 朝向只能以有限角速度改变，形成弧线轨迹
    - 速度始终沿当前朝向，避免原地绕自身中轴旋转

    不涉及任何行为决策，只做物理模拟
    """

    def __init__(
            self,
            damping: float = 0.93,
            max_speed: float = 300.0,
            mass: float = 1.0
    ):
        """
        Args:
            damping: 速度阻尼系数 (0~1)，每帧速度乘以该值。越小惯性越小
            max_speed: 最大速度限制（像素/秒）
            mass: 质量（影响加速度 = 力/质量）
        """
        self.body = PhysicsBody()
        self.damping = damping
        self.max_speed = max_speed
        self.mass = mass

        # 转弯参数（降低增益与响应、增加阻尼，抑制直线行走时的左右震荡）
        self.max_angular_velocity = 10.0      # 最大转向速率（弧度/秒）
        self.angular_damping = 0.84           # 角速度保持系数（越小越快抑制震荡）
        self.steering_gain = 10.0             # 舵角→目标角速度增益（降低以减少超调）
        self.steering_response = 14.0          # 角速度响应速度（降低以减少超调）
        self.thrust_response = 12.0           # 油门响应速度
        self.scared_angular_multiplier = 3.0  # 惊吓时最大角速度倍率
        self.scared_steering_multiplier = 2.5 # 惊吓时舵角增益倍率
        self.scared_response_multiplier = 2.5 # 惊吓时响应速度倍率
        self.scared_damping_multiplier = 0.70 # 惊吓时角阻尼倍率（越小越直接）

        # 状态
        self._is_scared = False

        # 每帧输入
        self._target_orientation = 0.0
        self._thrust = 0.0

    def set_position(self, x: float, y: float):
        """直接设置位置（用于被抓、初始化等场景）"""
        self.body.previous_position = self.body.position.copy()
        self.body.position = Vector2(x, y)
        self.body.velocity = Vector2(0.0, 0.0)
        self.body.forward_speed = 0.0
        self.body.angular_velocity = 0.0

    def set_velocity(self, vx: float, vy: float):
        """直接设置速度（用于释放拖动时弹开等场景）"""
        self.body.velocity = Vector2(vx, vy)
        self.body.forward_speed = self.body.velocity.length()
        if self.body.forward_speed > 0.01:
            self.body.orientation = self.body.velocity.angle()
            self._target_orientation = self.body.orientation

    def set_orientation(self, angle: float):
        """直接设置朝向（用于初始化）"""
        self.body.orientation = angle
        self._target_orientation = angle

    def set_target_orientation(self, angle: float):
        """设置目标朝向（行为层每帧调用）"""
        self._target_orientation = angle

    def set_thrust(self, thrust: float):
        """设置前进油门（行为层每帧调用，可负代表倒车/刹车）"""
        self._thrust = thrust

    def set_scared(self, scared: bool):
        """设置惊吓状态，惊吓时大幅提升转弯锐度"""
        self._is_scared = scared

    def add_force(self, fx: float, fy: float):
        """
        兼容旧接口：将力向量分解为油门 + 目标朝向。
        力的大小决定油门，力的方向决定目标朝向。

        朝向死区：力方向与当前朝向偏差小于阈值时不更新目标朝向，
        避免直线行走时因力的微小抖动导致目标朝向左右摆动、引发震荡。
        """
        force = Vector2(fx, fy)
        self._thrust = force.length()
        if self._thrust > 0.01:
            new_target = force.angle()
            # 死区：偏差 < 0.08 rad（约 4.6°）时保持当前目标，消除直线行走震荡
            diff = self._shortest_angle_diff(new_target, self.body.orientation)
            if abs(diff) > 0.08:
                self._target_orientation = new_target

    def add_impulse(self, ix: float, iy: float):
        """
        施加瞬时冲量（直接改变速度）
        用于弹开等场景；会同时重置朝向以匹配冲量方向
        """
        impulse = Vector2(ix, iy) / self.mass
        self.body.velocity += impulse
        self.body.forward_speed = self.body.velocity.length()
        if self.body.forward_speed > 0.01:
            self.body.orientation = self.body.velocity.angle()
            self._target_orientation = self.body.orientation

    def get_speed(self) -> float:
        """获取当前速率"""
        return self.body.forward_speed

    def get_direction(self) -> float:
        """获取当前运动方向（弧度），即身体朝向"""
        return self.body.orientation

    def get_angular_velocity(self) -> float:
        """获取当前转向速率（弧度/秒）"""
        return self.body.angular_velocity

    def _shortest_angle_diff(self, target: float, current: float) -> float:
        """计算 target - current 的最小角度差（范围 [-π, π]）"""
        diff = target - current
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        return diff

    def update(
            self,
            dt: float,
            bounds: Optional[Tuple[float, float, float, float]] = None,
            wrap: bool = False,
    ) -> Vector2:
        """
        推进一帧物理模拟

        Args:
            dt: 帧间隔（秒）
            bounds: 边界 (min_x, min_y, max_x, max_y)，None 则无边界
            wrap: 是否开启环绕边界（上下、左右相连）

        Returns:
            更新后的位置 Vector2
        """
        # 保存上一帧位置
        self.body.previous_position = self.body.position.copy()

        # ---- 转弯物理：先积分朝向，再沿朝向前进 ----
        # 1. 计算目标角速度（由当前朝向到目标朝向的舵角输入）
        # 惊吓时大幅提升转弯锐度和响应速度
        angular_mult = self.scared_angular_multiplier if self._is_scared else 1.0
        steering_mult = self.scared_steering_multiplier if self._is_scared else 1.0
        response_mult = self.scared_response_multiplier if self._is_scared else 1.0
        damping_mult = self.scared_damping_multiplier if self._is_scared else 1.0

        angle_diff = self._shortest_angle_diff(self._target_orientation, self.body.orientation)
        target_angular_velocity = angle_diff * self.steering_gain * steering_mult
        # 限制最大转向速率
        max_angular = self.max_angular_velocity * angular_mult
        target_angular_velocity = max(-max_angular, min(max_angular, target_angular_velocity))

        # 2. 角速度平滑趋近目标（模拟转向惯性）
        response = self.steering_response * response_mult
        self.body.angular_velocity += (target_angular_velocity - self.body.angular_velocity) * response * dt
        self.body.angular_velocity *= self.angular_damping * damping_mult

        # 3. 更新朝向
        self.body.orientation += self.body.angular_velocity * dt

        # 4. 前进速度由油门驱动（带阻尼）
        # 油门视为目标速度
        target_speed = self._thrust / max(1.0, self.mass * 0.5)
        target_speed = max(-self.max_speed * 0.3, min(self.max_speed, target_speed))
        self.body.forward_speed += (target_speed - self.body.forward_speed) * self.thrust_response * dt
        self.body.forward_speed *= self.damping

        # 5. 速度始终沿当前朝向
        self.body.velocity = Vector2.from_angle(self.body.orientation, self.body.forward_speed)
        self.body.acceleration = Vector2.from_angle(self.body.orientation, self._thrust / self.mass)

        # 6. 更新位置：沿当前朝向弧线前进
        self.body.position += self.body.velocity * dt

        # 边界处理
        if bounds is not None:
            if wrap:
                self._wrap_position(bounds)
            else:
                self._apply_bounds(bounds)

        # 重置输入
        self._thrust = 0.0
        self._target_orientation = self.body.orientation
        self._is_scared = False

        return self.body.position

    def _apply_bounds(self, bounds: Tuple[float, float, float, float]):
        """
        边界约束：软反弹 + 位置钳制

        bounds: (min_x, min_y, max_x, max_y)
        """
        min_x, min_y, max_x, max_y = bounds
        pos = self.body.position
        vel = self.body.velocity

        # X 轴边界
        if pos.x < min_x:
            pos.x = min_x
            if vel.x < 0:
                vel.x = -vel.x * 0.3  # 反弹但损失能量
        elif pos.x > max_x:
            pos.x = max_x
            if vel.x > 0:
                vel.x = -vel.x * 0.3

        # Y 轴边界
        if pos.y < min_y:
            pos.y = min_y
            if vel.y < 0:
                vel.y = -vel.y * 0.3
        elif pos.y > max_y:
            pos.y = max_y
            if vel.y > 0:
                vel.y = -vel.y * 0.3

    def _wrap_position(self, bounds: Tuple[float, float, float, float]):
        """
        环绕边界：超出边界时从对侧进入

        bounds: (min_x, min_y, max_x, max_y)
        """
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        pos = self.body.position

        if pos.x < min_x:
            pos.x += width
        elif pos.x > max_x:
            pos.x -= width

        if pos.y < min_y:
            pos.y += height
        elif pos.y > max_y:
            pos.y -= height

    def get_state(self) -> dict:
        """返回当前物理状态（供调试或序列化）"""
        return {
            'position':  self.body.position.to_tuple(),
            'velocity':  self.body.velocity.to_tuple(),
            'speed':     self.get_speed(),
            'direction': self.get_direction(),
        }

    def update_config(self, damping: Optional[float] = None, max_speed: Optional[float] = None):
        """运行时更新物理参数"""
        if damping is not None:
            self.damping = max(0.0, min(1.0, damping))
        if max_speed is not None:
            self.max_speed = max(1.0, max_speed)


# ---------- 简易测试 ----------
if __name__ == "__main__":
    import time

    pe = PhysicsEngine(damping=0.93, max_speed=300)
    pe.set_position(500, 400)

    print("=== 物理引擎测试 ===")
    print(f"初始位置: {pe.body.position}")

    # 施加一个力
    pe.add_force(200, -100)

    # 模拟几帧
    screen_bounds = (0, 0, 1920, 1080)
    for i in range(10):
        pos = pe.update(0.016, screen_bounds)  # ~60fps
        print(f"帧 {i + 1}: pos={pos.to_tuple()}, speed={pe.get_speed():.1f}, dir={pe.get_direction():.3f}rad")

    # 测试边界反弹
    print("\n=== 边界测试 ===")
    pe.set_position(10, 400)
    pe.set_velocity(-500, 0)
    for i in range(5):
        pos = pe.update(0.016, screen_bounds)
        print(f"帧 {i + 1}: pos={pos.to_tuple()}, vel={pe.body.velocity.to_tuple()}")
