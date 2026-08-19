"""
pet.py
电子桌宠蟑螂 - 顶层门面类

封装配置管理、物理引擎、行为决策、几何模型的全部逻辑。
前端只需要：
1. 创建 CockroachPet 实例
2. 每帧调用 update() 获取 CockroachRenderData
3. 根据 RenderData 绘制蟑螂
4. 通过 grab()/release() 处理拖动
5. 通过 configure() 修改设置
"""

import math

from config_manager import ConfigManager
from physics_engine import PhysicsEngine, Vector2
from behavior_engine import BehaviorEngine, BehaviorState
from cockroach_model import (
    CockroachModel,
    CockroachRenderData,
    AntennaData,
    LegData,
    WingData,
)
from autostart import AutostartManager

__all__ = [
    "CockroachPet",
    "CockroachRenderData",
    "AntennaData",
    "LegData",
    "WingData",
    "BehaviorState",
]


class CockroachPet:
    """
    电子桌宠蟑螂 - 顶层门面类

    封装了配置管理、物理引擎、行为决策、几何模型的全部逻辑。
    """

    def __init__(self, config_dir: str = None):
        """
        初始化蟑螂桌宠

        Args:
            config_dir: 配置文件目录，None 则自动确定
        """
        # ---- 核心模块 ----
        self.config = ConfigManager(config_dir)
        cfg = self.config.get_all()

        self.physics = PhysicsEngine(
            damping=cfg.get("damping", 0.93),
            max_speed=cfg.get("speed_max", 300),
        )
        self.behavior = BehaviorEngine(cfg)
        self.model = CockroachModel(body_size=cfg.get("body_size", 40))
        self.autostart = AutostartManager("CockroachPet")

        # ---- 拖动状态 ----
        self._is_grabbed = False
        self._grab_offset_x = 0.0
        self._grab_offset_y = 0.0
        self._mouse_press_timer = 0.0
        self._mouse_was_pressed = False

        # ---- 鼠标速度追踪 ----
        self._prev_mouse_x = 0.0
        self._prev_mouse_y = 0.0
        self._mouse_velocity = 0.0

        # 屏幕边界
        self._screen_width = 1920
        self._screen_height = 1080

        # ---- 初始化位置 ----
        self._init_start_position()

        # ---- 应用开机自启设置 ----
        self._apply_autostart_setting()

    def _init_start_position(self):
        """设置初始位置（屏幕中下方偏右）"""
        self.physics.set_position(
            self._screen_width * 0.55,
            self._screen_height * 0.65,
        )

    def _apply_autostart_setting(self):
        """根据配置应用开机自启设置"""
        should_autostart = self.config.get("autostart")
        current_state = self.autostart.is_enabled()
        if should_autostart != current_state:
            self.autostart.set_enabled(should_autostart)

    # ==================== 核心更新 ====================

    def update(
            self,
            dt: float,
            mouse_x: float,
            mouse_y: float,
            mouse_pressed: bool,
            mouse_on_pet: bool,
            screen_width: int,
            screen_height: int,
    ) -> CockroachRenderData:
        """
        每帧更新，返回渲染所需数据

        Args:
            dt: 帧间隔（秒），建议 0.016（60fps）
            mouse_x, mouse_y: 鼠标屏幕坐标
            mouse_pressed: 鼠标左键是否按下
            mouse_on_pet: 鼠标是否悬停在蟑螂身上（前端判断）
            screen_width, screen_height: 屏幕尺寸

        Returns:
            CockroachRenderData: 包含所有身体部位的坐标和状态
        """
        # 更新屏幕边界
        self._screen_width = screen_width
        self._screen_height = screen_height

        # 首次调用时，将上一帧鼠标位置初始化为当前位置，避免首帧速度爆炸
        if self._prev_mouse_x == 0.0 and self._prev_mouse_y == 0.0:
            self._prev_mouse_x = mouse_x
            self._prev_mouse_y = mouse_y

        # 更新鼠标速度（像素/秒）
        if dt > 0:
            dx = mouse_x - self._prev_mouse_x
            dy = mouse_y - self._prev_mouse_y
            raw_speed = math.sqrt(dx * dx + dy * dy) / dt
            # 指数平滑
            self._mouse_velocity = self._mouse_velocity * 0.6 + raw_speed * 0.4
        self._prev_mouse_x = mouse_x
        self._prev_mouse_y = mouse_y

        # 拖动逻辑
        self._update_grab(dt, mouse_x, mouse_y, mouse_pressed, mouse_on_pet)

        # 获取当前位置
        pos = self.physics.body.position

        # 行为决策 → 获得力向量
        if self._is_grabbed:
            # 被抓：直接设置位置
            target_x = mouse_x - self._grab_offset_x
            target_y = mouse_y - self._grab_offset_y
            self.physics.set_position(target_x, target_y)
            force_x, force_y = 0.0, 0.0
            behavior_state = BehaviorState.GRABBED
            is_scared = False
        else:
            # 用物理朝向作为蟑螂身体朝向（转弯模型保证朝向与运动方向一致）
            roach_angle = self.physics.get_direction()
            behavior_state, (force_x, force_y), is_scared = self.behavior.update(
                dt=dt,
                roach_pos=(pos.x, pos.y),
                mouse_pos=(mouse_x, mouse_y),
                mouse_pressed=mouse_pressed,
                is_grabbed=False,
                screen_size=(screen_width, screen_height),
                wrap=self.config.get("wrap_screen", True),
                roach_angle=roach_angle,
            )
            # 将行为力转换为油门 + 目标朝向
            self.physics.add_force(force_x, force_y)
            # 将惊吓状态传入物理引擎，以提升逃跑时转弯锐度
            self.physics.set_scared(is_scared)

        # 屏幕边界环绕配置
        wrap_screen = self.config.get("wrap_screen", True)

        # 物理更新（转弯模型：沿弧线前进）
        bounds = (0, 0, screen_width, screen_height)
        self.physics.update(dt, bounds, wrap=wrap_screen)

        # 获取更新后的物理状态
        new_pos = self.physics.body.position
        speed = self.physics.get_speed()
        direction = self.physics.get_direction()
        turn_rate = self.physics.get_angular_velocity()

        # 几何模型 → 计算渲染数据（使用物理朝向与真实角速度）
        is_observing = (not self._is_grabbed) and behavior_state == BehaviorState.OBSERVE
        render_data = self.model.compute(
            x=new_pos.x,
            y=new_pos.y,
            angle=direction,
            speed=speed,
            dt=dt,
            is_scared=is_scared,
            turn_rate=turn_rate,
            is_observing=is_observing,
        )

        # 保存环绕状态供前端渲染幽灵副本
        render_data.wrap_screen = wrap_screen

        # 如果被抓，覆盖惊吓状态
        if self._is_grabbed:
            render_data.is_scared = False

        return render_data

    def _update_grab(
            self, dt: float,
            mouse_x: float, mouse_y: float,
            mouse_pressed: bool, mouse_on_pet: bool,
    ):
        """
        更新拖动状态机

        拖动条件：
        1. 鼠标按住超过阈值时间（长按）
        2. 鼠标在蟑螂身上
        3. 鼠标移动速度慢（不触发惊吓）
        """
        GRAB_HOLD_TIME = 0.35  # 长按阈值（秒）
        GRAB_MAX_SPEED = 400  # 拖动触发最大鼠标速度

        # 鼠标按下计时
        if mouse_pressed and not self._mouse_was_pressed:
            self._mouse_press_timer = 0.0

        if mouse_pressed:
            self._mouse_press_timer += dt
        else:
            self._mouse_press_timer = 0.0

        # 开始拖动
        if (
                mouse_pressed
                and mouse_on_pet
                and not self._is_grabbed
                and self._mouse_press_timer >= GRAB_HOLD_TIME
                and self._mouse_velocity < GRAB_MAX_SPEED
        ):
            self._is_grabbed = True
            pos = self.physics.body.position
            self._grab_offset_x = mouse_x - pos.x
            self._grab_offset_y = mouse_y - pos.y

        # 释放拖动
        if not mouse_pressed and self._is_grabbed:
            self.release()

        self._mouse_was_pressed = mouse_pressed

    # ==================== 拖动接口 ====================

    def grab(self, offset_x: float, offset_y: float):
        """
        手动设置拖动（前端判断点击在蟑螂身上时调用）

        Args:
            offset_x, offset_y: 鼠标点击位置相对于蟑螂中心的偏移
        """
        self._is_grabbed = True
        self._grab_offset_x = offset_x
        self._grab_offset_y = offset_y

    def release(self, fling_velocity_x: float = 0.0, fling_velocity_y: float = 0.0):
        """
        释放拖动

        Args:
            fling_velocity_x, fling_velocity_y: 甩出速度（可选，模拟惯性甩出）
        """
        self._is_grabbed = False
        if fling_velocity_x != 0.0 or fling_velocity_y != 0.0:
            self.physics.set_velocity(fling_velocity_x, fling_velocity_y)
        self._grab_offset_x = 0.0
        self._grab_offset_y = 0.0
        # 释放后抑制惊吓触发，避免拖动残留的高速鼠标误触逃跑
        self.behavior.suppress_scare(1.5)
        self._mouse_velocity = 0.0

    @property
    def is_grabbed(self) -> bool:
        """是否正在被抓"""
        return self._is_grabbed

    def is_grabbable(self) -> bool:
        """当前是否允许被抓"""
        return (
                self._mouse_press_timer >= 0.35
                and self._mouse_velocity < 400
        )

    # ==================== 配置接口 ====================

    def get_config(self, key: str):
        """获取单个配置值"""
        return self.config.get(key)

    # 需要批量刷新行为引擎的配置键
    _BEHAVIOR_KEYS = (
        "wander_strength", "wander_direction_change",
        "attract_distance", "attract_strength", "dead_zone",
        "scare_speed_threshold", "scare_distance",
        "scare_duration", "scare_flee_strength",
        "edge_margin", "edge_repulsion",
    )

    def apply_config(self, key: str, value) -> bool:
        """
        设置配置值并立即应用到对应子模块（不写文件）

        供设置界面拖动滑块时频繁调用，配合 config.save() 防抖使用。

        Args:
            key: 配置键名
            value: 新值

        Returns:
            是否设置成功
        """
        if not self.config.set(key, value):
            return False

        cfg = self.config.get_all()
        if key == "body_size":
            self.model.update_size(value)
        elif key in ("speed_max", "damping"):
            self.physics.update_config(
                damping=cfg.get("damping"),
                max_speed=cfg.get("speed_max"),
            )
        elif key == "autostart":
            self.autostart.set_enabled(value)
        elif key in self._BEHAVIOR_KEYS:
            self.behavior.update_config(cfg)
        return True

    def set_config(self, key: str, value) -> bool:
        """
        设置配置值、立即生效并保存到文件

        适合右键菜单等低频修改场景；设置界面建议用 apply_config + 防抖 save。
        """
        if not self.apply_config(key, value):
            return False
        self.config.save()
        return True

    def get_all_config(self) -> dict:
        """获取全部配置"""
        return self.config.get_all()

    def get_config_schema(self) -> dict:
        """获取配置项描述（供设置界面生成控件）"""
        return ConfigManager.get_schema()

    def set_autostart(self, enable: bool) -> bool:
        """设置开机自启"""
        result = self.autostart.set_enabled(enable)
        self.config.set("autostart", enable)
        self.config.save()
        return result

    def is_autostart_enabled(self) -> bool:
        """检查开机自启状态"""
        return self.autostart.is_enabled()

    # ==================== 状态查询 ====================

    def get_position(self) -> tuple:
        """获取当前位置 (x, y)"""
        p = self.physics.body.position
        return (p.x, p.y)

    def get_behavior_state(self) -> BehaviorState:
        """获取当前行为状态"""
        return self.behavior.state

    def is_scared(self) -> bool:
        """是否处于惊吓状态"""
        return self.behavior.state == BehaviorState.SCARED

    def get_scared_progress(self) -> float:
        """惊吓剩余进度 0~1"""
        return self.behavior.get_scared_progress()

    # ==================== 生命周期 ====================

    def reload_config_if_changed(self) -> bool:
        """
        检测外部配置文件是否被修改，是则重新加载并应用到各子模块

        用于桌宠本体与设置界面并行运行时，让本体感知并应用外部配置更新，
        而无需重启进程。autostart 不在此处重复应用，避免每次重载都
        操作系统启动项。

        Returns:
            True 表示检测到变化并已重载应用；False 表示无变化
        """
        if not self.config.reload_if_changed():
            return False
        cfg = self.config.get_all()
        self.physics.update_config(
            damping=cfg.get("damping"),
            max_speed=cfg.get("speed_max"),
        )
        self.behavior.update_config(cfg)
        self.model.update_size(cfg.get("body_size"))
        return True

    def reset(self):
        """重置所有状态（重新开始）"""
        self.behavior.reset()
        self.physics.set_position(
            self._screen_width * 0.5,
            self._screen_height * 0.5,
        )
        self._is_grabbed = False
        self._grab_offset_x = 0.0
        self._grab_offset_y = 0.0
        self._mouse_press_timer = 0.0

    def shutdown(self):
        """关闭时调用，保存配置"""
        self.config.save()
