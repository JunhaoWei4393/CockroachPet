"""
behavior_engine.py
行为引擎 - 状态机 + 行为决策
负责决定蟑螂当前处于什么状态、该施加什么力
不涉及物理积分和几何细节
"""

import math
import random
from enum import Enum, auto
from typing import Optional, Tuple


# 引用 physics_engine 的 Vector2（实际项目中用 import）
# 这里内联一份以保持模块独立
class Vector2:
    __slots__ = ('x', 'y')

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def __add__(self, o): return Vector2(self.x + o.x, self.y + o.y)

    def __sub__(self, o): return Vector2(self.x - o.x, self.y - o.y)

    def __mul__(self, s): return Vector2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def __truediv__(self, s): return Vector2(self.x / s, self.y / s) if s != 0 else Vector2()

    def __neg__(self): return Vector2(-self.x, -self.y)

    def length(self): return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self): return self.x * self.x + self.y * self.y

    def normalize(self):
        l = self.length()
        return Vector2(self.x / l, self.y / l) if l > 0 else Vector2()

    def angle(self): return math.atan2(self.y, self.x)

    @staticmethod
    def from_angle(a, length=1.0): return Vector2(math.cos(a) * length, math.sin(a) * length)

    def rotate(self, a):
        c, s = math.cos(a), math.sin(a)
        return Vector2(self.x * c - self.y * s, self.x * s + self.y * c)

    def dot(self, o): return self.x * o.x + self.y * o.y

    def distance_to(self, o):
        dx, dy = self.x - o.x, self.y - o.y
        return math.sqrt(dx * dx + dy * dy)

    def to_tuple(self): return (self.x, self.y)

    def copy(self): return Vector2(self.x, self.y)

    def __repr__(self): return f"({self.x:.1f}, {self.y:.1f})"


class BehaviorState(Enum):
    """行为状态枚举"""
    ROAM = auto()  # 漫游：随机移动
    OBSERVE = auto()  # 观察：原地休息，触角活跃探测，偶尔缓慢环顾
    ATTRACT = auto()  # 被吸引：鼠标缓慢靠近，蟑螂被牵引
    SCARED = auto()  # 惊吓：鼠标快速靠近/点击，快速逃跑
    GRABBED = auto()  # 被抓：长按拖动中


class BehaviorEngine:
    """
    行为引擎 - 状态机核心

    职责：
    1. 根据环境和内部状态决定当前行为状态
    2. 计算当前状态下该施加的力向量
    3. 管理状态转换逻辑
    """

    def __init__(self, config: dict):
        """
        Args:
            config: 配置字典（来自 ConfigManager.get_all()）
        """
        self.state = BehaviorState.ROAM
        self._config = config

        # 状态计时器
        self._scared_timer = 0.0  # 惊吓剩余时间
        self._roam_pause_timer = 0.0  # 漫游停顿计时（已废弃，由 OBSERVE 状态替代）
        self._roam_new_direction_timer = 0.0  # 漫游换方向计时

        # 观察状态计时
        self._observe_timer = 0.0  # 观察剩余时间
        self._observe_turn_timer = 0.0  # 下次环顾计时
        self._observe_cooldown = 0.0  # 观察结束后的冷却（避免连续触发）

        # 漫游内部状态
        self._wander_angle = random.uniform(0, 2 * math.pi)
        self._is_paused = False

        # 上一次鼠标位置（用于计算鼠标速度）
        self._prev_mouse_pos = Vector2(0, 0)
        self._mouse_velocity = 0.0

        # 鼠标按下计时（判断长按）
        self._mouse_press_duration = 0.0
        self._grab_threshold = 0.3  # 长按阈值（秒）

        # 状态转换的冷却（防止反复横跳）
        self._scare_cooldown = 0.0

        # 屏幕是否环绕
        self._wrap = False

    def update(
            self,
            dt: float,
            roach_pos: Tuple[float, float],
            mouse_pos: Tuple[float, float],
            mouse_pressed: bool,
            is_grabbed: bool,
            screen_size: Tuple[int, int],
            wrap: bool = False,
            roach_angle: float = 0.0,
    ) -> Tuple[BehaviorState, Tuple[float, float], bool]:
        """
        每帧调用，决策行为并输出力向量

        Args:
            dt: 帧间隔（秒）
            roach_pos: 蟑螂当前位置 (x, y)
            mouse_pos: 鼠标当前位置 (x, y)
            mouse_pressed: 鼠标左键是否按下
            is_grabbed: 外部告知是否正在被抓（由前端判断是否点在蟑螂身上）
            screen_size: 屏幕尺寸 (width, height)
            wrap: 是否开启屏幕边界环绕
            roach_angle: 蟑螂朝向（弧度，0=向右），用于前方120°警戒权重

        Returns:
            (新状态, (force_x, force_y), is_scared)
            - force: 该帧应施加的力，GRABBED 时返回 (0,0)（前端直接设位置）
            - is_scared: 是否处于惊吓状态（影响渲染）
        """
        roach = Vector2(roach_pos[0], roach_pos[1])
        mouse = Vector2(mouse_pos[0], mouse_pos[1])
        sw, sh = screen_size
        self._wrap = wrap
        self._roach_angle = roach_angle

        # 首次调用时初始化上一帧鼠标位置，避免首帧速度爆炸
        if self._prev_mouse_pos.x == 0.0 and self._prev_mouse_pos.y == 0.0:
            self._prev_mouse_pos = mouse.copy()

        # 更新鼠标速度（像素/秒）
        if dt > 0:
            raw_dist = mouse.distance_to(self._prev_mouse_pos)
            # 简单平滑，避免抖动
            self._mouse_velocity = self._mouse_velocity * 0.6 + (raw_dist / dt) * 0.4
        self._prev_mouse_pos = mouse.copy()

        # 更新冷却
        if self._scare_cooldown > 0:
            self._scare_cooldown -= dt
        if self._observe_cooldown > 0:
            self._observe_cooldown -= dt

        # ---- 状态转换逻辑 ----
        new_state = self._determine_state(
            dt, roach, mouse, mouse_pressed, is_grabbed, sw, sh
        )

        # ---- 计算力 ----
        force_x, force_y = 0.0, 0.0

        if new_state == BehaviorState.GRABBED:
            force_x, force_y = 0.0, 0.0  # 前端直接设位置
        elif new_state == BehaviorState.SCARED:
            force_x, force_y = self._scared_force(roach, mouse, dt, sw, sh)
        elif new_state == BehaviorState.OBSERVE:
            force_x, force_y = self._observe_force(dt)
        elif new_state == BehaviorState.ATTRACT:
            force_x, force_y = self._attract_force(roach, mouse, dt, sw, sh)
        elif new_state == BehaviorState.ROAM:
            force_x, force_y = self._roam_force(roach, dt, sw, sh)

        self.state = new_state
        return (
            self.state,
            (force_x, force_y),
            self.state == BehaviorState.SCARED
        )

    def _toroidal_diff(self, roach: Vector2, mouse: Vector2, sw: int, sh: int) -> Vector2:
        """
        计算环形边界下从蟑螂指向鼠标的最短向量。

        当 screen wrapping 开启时，屏幕上下、左右相连，
        因此需要考虑鼠标在屏幕对侧的“幽灵副本”。
        """
        if not self._wrap or sw <= 0 or sh <= 0:
            return mouse - roach

        dx = mouse.x - roach.x
        dy = mouse.y - roach.y

        # 如果跨边界更近，则使用环绕后的方向
        if abs(dx) > sw * 0.5:
            dx -= sw * (1 if dx > 0 else -1)
        if abs(dy) > sh * 0.5:
            dy -= sh * (1 if dy > 0 else -1)

        return Vector2(dx, dy)

    def _directional_weight(self, roach: Vector2, mouse: Vector2, sw: int, sh: int) -> float:
        """
        根据鼠标相对蟑螂的方位返回警戒/吸引权重（已考虑环形边界）。

        蟑螂的复眼和触角主要覆盖前方，因此正前方 120° 区域最敏感；
        侧后方属于弱感知区，权重降低。

        Returns:
            前方 120° 返回 1.4，其它方位返回 0.7（用于惊吓距离/速度阈值）
        """
        diff = self._toroidal_diff(roach, mouse, sw, sh)
        if abs(diff.x) < 1e-6 and abs(diff.y) < 1e-6:
            return 1.0
        mouse_angle = math.atan2(diff.y, diff.x)
        rel = mouse_angle - self._roach_angle
        # 归一化到 [-π, π]
        while rel > math.pi:
            rel -= 2 * math.pi
        while rel < -math.pi:
            rel += 2 * math.pi
        # 前方 120°：相对朝向绝对值 ≤ π/3
        return 1.4 if abs(rel) <= math.pi / 3 else 0.7

    def _determine_state(
            self, dt: float, roach: Vector2, mouse: Vector2,
            mouse_pressed: bool, is_grabbed: bool,
            sw: int, sh: int
    ) -> BehaviorState:
        """决定当前应该处于哪个状态（引入前方 120° 方位权重与环形边界）"""

        diff = self._toroidal_diff(roach, mouse, sw, sh)
        dist = diff.length()
        scare_dist = self._config.get("scare_distance", 150)
        attract_dist = self._config.get("attract_distance", 200)
        scare_speed = self._config.get("scare_speed_threshold", 800)

        # 0. 被抓状态优先
        if is_grabbed:
            self._scared_timer = 0
            return BehaviorState.GRABBED

        # 1. 正在惊吓中，继续惊吓直到计时结束
        if self.state == BehaviorState.SCARED and self._scared_timer > 0:
            return BehaviorState.SCARED

        # 2. 检测惊吓触发（鼠标快速且近距离 + 冷却已过）
        # 前方 120° 更敏感：等效扩大警戒距离、降低触发速度阈值
        # 侧后方更迟钝：等效缩小警戒距离、提高触发速度阈值
        if self._scare_cooldown <= 0:
            weight = self._directional_weight(roach, mouse, sw, sh)
            effective_scare_dist = scare_dist * weight
            effective_scare_speed = scare_speed / weight
            if dist < effective_scare_dist and self._mouse_velocity > effective_scare_speed:
                self._scared_timer = self._config.get("scare_duration", 2.5)
                self._scare_cooldown = 1.0  # 1秒冷却
                return BehaviorState.SCARED

        # 3. 鼠标在吸引范围内且速度不快
        # 前方吸引更强，后方吸引更弱
        if self._mouse_velocity < scare_speed * 0.5:
            weight = self._directional_weight(roach, mouse, sw, sh)
            effective_attract_dist = attract_dist * weight
            if dist < effective_attract_dist:
                return BehaviorState.ATTRACT

        # 4. 正在观察中（未被高优先级状态中断则继续）
        if self.state == BehaviorState.OBSERVE and self._observe_timer > 0:
            return BehaviorState.OBSERVE

        # 5. 漫游时随机进入观察（冷却结束后才有概率触发）
        if self.state == BehaviorState.ROAM and self._observe_cooldown <= 0:
            self._observe_timer -= dt
            if self._observe_timer <= 0:
                if random.random() < 0.10:  # 10% 概率进入观察
                    self._observe_timer = random.uniform(2.5, 6.0)
                    self._observe_turn_timer = random.uniform(0.5, 1.5)
                    return BehaviorState.OBSERVE
                self._observe_timer = random.uniform(4.0, 10.0)

        # 6. 默认漫游
        return BehaviorState.ROAM

    def _roam_force(
            self, roach: Vector2, dt: float,
            sw: int, sh: int
    ) -> Tuple[float, float]:
        """
        漫游行为力计算
        随机游走 + 边缘排斥
        （原地停顿已由 OBSERVE 状态接管）
        """
        wander_strength = self._config.get("wander_strength", 150)
        direction_change = self._config.get("wander_direction_change", 2.5)
        edge_margin = self._config.get("edge_margin", 60)
        edge_repulsion = self._config.get("edge_repulsion", 400)

        # 方向变化
        self._roam_new_direction_timer -= dt
        if self._roam_new_direction_timer <= 0:
            # 在现有方向上叠加随机偏移
            self._wander_angle += random.uniform(-direction_change, direction_change)
            self._roam_new_direction_timer = random.uniform(0.3, 1.5)

        # 游走力
        wander_force = Vector2.from_angle(self._wander_angle, wander_strength)

        # 边缘排斥力
        edge_force = self._edge_repulsion(roach, sw, sh, edge_margin, edge_repulsion)

        total = wander_force + edge_force
        return total.to_tuple()

    def _observe_force(self, dt: float) -> Tuple[float, float]:
        """
        观察状态力计算

        原地静止为主，偶尔施加极小侧向力使身体缓慢转动环顾四周。
        触角活跃探测由渲染端根据 OBSERVE 状态提升 activity 实现。
        """
        self._observe_timer -= dt
        self._observe_turn_timer -= dt

        if self._observe_turn_timer <= 0:
            self._observe_turn_timer = random.uniform(1.5, 3.5)
            # 40% 概率缓慢转身环顾
            if random.random() < 0.4:
                turn_dir = random.choice([-1, 1])
                # 施加垂直于当前朝向的微小力，让身体缓慢转一个小角度
                angle = self._roach_angle + math.pi / 2 * turn_dir + random.uniform(-0.3, 0.3)
                return Vector2.from_angle(angle, 35).to_tuple()

        # 观察结束：设置冷却，避免马上再次进入
        if self._observe_timer <= 0:
            self._observe_cooldown = random.uniform(3.0, 8.0)

        return (0.0, 0.0)

    def _attract_force(
            self, roach: Vector2, mouse: Vector2, dt: float,
            sw: int, sh: int
    ) -> Tuple[float, float]:
        """
        吸引行为力计算（支持环形边界）
        指向鼠标的引力 + 微弱随机性 + 边缘排斥
        前方 120° 吸引更强，后方更弱，模拟昆虫主要对前方刺激产生兴趣
        """
        attract_strength = self._config.get("attract_strength", 500)
        dead_zone = self._config.get("dead_zone", 30)
        wander_strength = self._config.get("wander_strength", 150)
        edge_margin = self._config.get("edge_margin", 60)
        edge_repulsion = self._config.get("edge_repulsion", 400)

        diff = self._toroidal_diff(roach, mouse, sw, sh)
        dist = diff.length()

        force = Vector2(0, 0)

        # 引力（死区外）
        if dist > dead_zone:
            to_mouse = diff.normalize()
            # 距离衰减：远强近弱
            strength = attract_strength / (1.0 + dist * 0.03)
            # 前方吸引更强，侧后方更弱
            strength *= self._directional_weight(roach, mouse, sw, sh)
            force = force + to_mouse * strength

        # 微小随机扰动（保持生物感）
        if random.random() < 0.3:
            random_angle = random.uniform(0, 2 * math.pi)
            force = force + Vector2.from_angle(random_angle, wander_strength * 0.2)

        # 边缘排斥
        edge_force = self._edge_repulsion(roach, sw, sh, edge_margin, edge_repulsion)
        force = force + edge_force

        return force.to_tuple()

    def _scared_force(
            self, roach: Vector2, mouse: Vector2, dt: float,
            sw: int, sh: int
    ) -> Tuple[float, float]:
        """
        惊吓逃跑力计算（支持环形边界）
        远离鼠标 + 随机侧向偏移 + 边缘排斥
        """
        flee_strength = self._config.get("scare_flee_strength", 1200)
        edge_margin = self._config.get("edge_margin", 60)
        edge_repulsion = self._config.get("edge_repulsion", 400)

        # 更新惊吓计时
        self._scared_timer -= dt

        # 远离鼠标的方向（环形边界下使用最短路径的反方向）
        diff = self._toroidal_diff(roach, mouse, sw, sh)
        away = -diff
        dist = away.length()

        force = Vector2(0, 0)

        if dist > 0.5:
            away_dir = away.normalize()

            # 主逃离力：坚定背离鼠标
            flee_force = away_dir * flee_strength

            # 极微弱的侧向偏移，避免完全机械直线但保持逃跑意图明确
            perpendicular = Vector2(-away_dir.y, away_dir.x)
            side_strength = random.uniform(-0.12, 0.12) * flee_strength
            side_force = perpendicular * side_strength

            force = flee_force + side_force
        else:
            # 太近了，沿当前朝向继续冲
            random_angle = random.uniform(-0.3, 0.3)
            force = Vector2.from_angle(self._roach_angle + random_angle, flee_strength)

        # 边缘排斥
        edge_force = self._edge_repulsion(roach, sw, sh, edge_margin, edge_repulsion * 1.5)
        force = force + edge_force

        return force.to_tuple()

    def _edge_repulsion(
            self, roach: Vector2, sw: int, sh: int,
            margin: float, strength: float
    ) -> Vector2:
        """
        边缘排斥力
        靠近屏幕边缘时产生向内推的力；开启屏幕环绕时返回零力
        """
        if self._wrap:
            return Vector2(0, 0)

        force = Vector2(0, 0)

        # 左边缘
        if roach.x < margin:
            force.x += (margin - roach.x) / margin * strength
        # 右边缘
        if roach.x > sw - margin:
            force.x -= (roach.x - (sw - margin)) / margin * strength
        # 上边缘
        if roach.y < margin:
            force.y += (margin - roach.y) / margin * strength
        # 下边缘
        if roach.y > sh - margin:
            force.y -= (roach.y - (sh - margin)) / margin * strength

        return force

    def get_scared_progress(self) -> float:
        """获取惊吓剩余比例 0~1（用于渲染效果）"""
        duration = self._config.get("scare_duration", 2.5)
        if duration <= 0:
            return 0.0
        return max(0.0, min(1.0, self._scared_timer / duration))

    def is_grab_ready(self, mouse_pressed_duration: float) -> bool:
        """判断是否满足长按抓取条件"""
        return mouse_pressed_duration >= self._grab_threshold

    def suppress_scare(self, duration: float = 1.5):
        """
        抑制惊吓触发一段时间（用于释放拖动后避免误触惊吓）。
        同时重置鼠标速度追踪，避免拖动残留的高速触发误判。
        """
        self._scare_cooldown = max(self._scare_cooldown, duration)
        self._mouse_velocity = 0.0

    def update_config(self, config: dict):
        """运行时更新配置"""
        self._config = config

    def reset(self):
        """重置状态（如重新开始时调用）"""
        self.state = BehaviorState.ROAM
        self._scared_timer = 0.0
        self._scare_cooldown = 0.0
        self._observe_timer = 0.0
        self._observe_turn_timer = 0.0
        self._observe_cooldown = 0.0
        self._roam_pause_timer = 0.0
        self._is_paused = False
        self._wander_angle = random.uniform(0, 2 * math.pi)


# ---------- 简易测试 ----------
if __name__ == "__main__":
    import time

    config = {
        "scare_distance":          150,
        "scare_speed_threshold":   800,
        "scare_duration":          2.5,
        "attract_distance":        200,
        "attract_strength":        500,
        "dead_zone":               30,
        "wander_strength":         150,
        "wander_direction_change": 2.5,
        "scare_flee_strength":     1200,
        "edge_margin":             60,
        "edge_repulsion":          400,
    }

    be = BehaviorEngine(config)

    print("=== 行为引擎测试 ===")
    roach = (500, 400)
    mouse_far = (900, 600)  # 远处鼠标
    mouse_close = (520, 410)  # 近处鼠标
    mouse_fast = (520, 410)  # 模拟快速移动
    screen = (1920, 1080)

    # 测试漫游
    print("\n1. 漫游状态（鼠标远）:")
    for i in range(5):
        state, force, scared = be.update(0.016, roach, mouse_far, False, False, screen)
        print(f"  帧{i}: state={state.name}, force=({force[0]:.0f},{force[1]:.0f}), scared={scared}")

    # 测试吸引
    print("\n2. 吸引状态（鼠标近+慢）:")
    for i in range(5):
        state, force, scared = be.update(0.016, roach, mouse_close, False, False, screen)
        print(f"  帧{i}: state={state.name}, force=({force[0]:.0f},{force[1]:.0f}), scared={scared}")

    # 测试惊吓
    print("\n3. 惊吓状态（模拟快速鼠标）:")
    # 先让鼠标速度积累
    be._mouse_velocity = 1200
    state, force, scared = be.update(0.016, roach, mouse_close, False, False, screen)
    print(f"  帧0: state={state.name}, force=({force[0]:.0f},{force[1]:.0f}), scared={scared}")
    for i in range(5):
        state, force, scared = be.update(0.016, roach, mouse_close, False, False, screen)
        print(f"  帧{i + 1}: state={state.name}, force=({force[0]:.0f},{force[1]:.0f}), scared={scared}, timer={be._scared_timer:.2f}")
