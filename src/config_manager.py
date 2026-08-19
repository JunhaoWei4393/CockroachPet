"""
config_manager.py
配置管理器 - 负责配置文件的读写、默认值管理、schema 定义
无任何 GUI 依赖，纯数据层
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """配置管理器，纯数据层"""

    # 默认配置
    DEFAULT_CONFIG = {
        # 外观
        "body_size":               40,  # 蟑螂身体大小（像素）
        "opacity":                 1.0,  # 窗口透明度 0.0~1.0

        # 运动参数
        "speed_max":               600,  # 最大移动速度（像素/秒）
        "damping":                 0.93,  # 速度阻尼系数（每帧乘以此值）

        # 漫游行为
        "wander_strength":         250,  # 随机游走力度
        "wander_direction_change": 3.5,  # 每秒方向变化速率（弧度）

        # 吸引行为
        "attract_distance":        200,  # 鼠标吸引触发距离（像素）
        "attract_strength":        800,  # 吸引力强度
        "dead_zone":               30,  # 死区半径（在此范围内不受引力，避免抖动）

        # 惊吓行为
        "scare_speed_threshold":   800,  # 触发惊吓的鼠标速度阈值（像素/秒）
        "scare_distance":          150,  # 触发惊吓的鼠标距离阈值（像素）
        "scare_duration":          2.5,  # 惊吓状态持续时间（秒）
        "scare_flee_strength":     1800,  # 逃跑力度
        "scare_body_expand":       1.15,  # 惊吓时身体膨胀系数

        # 边缘行为
        "edge_margin":             60,  # 屏幕边缘排斥力作用距离
        "edge_repulsion":          400,  # 边缘排斥力强度
        "wrap_screen":             True,  # 屏幕边界是否环绕（上下、左右相连）

        # 系统
        "autostart":               False,  # 是否开机自启
        "always_on_top":           True,  # 窗口是否置顶
    }

    # 配置项描述 schema，供设置界面使用
    SCHEMA = {
        "body_size":             {
            "type":  "slider",
            "min":   20,
            "max":   80,
            "step":  5,
            "label": "蟑螂大小",
            "group": "外观"
        },
        "opacity":               {
            "type":  "slider",
            "min":   0.3,
            "max":   1.0,
            "step":  0.05,
            "label": "透明度",
            "group": "外观"
        },
        "speed_max":             {
            "type":  "slider",
            "min":   100,
            "max":   1000,
            "step":  10,
            "label": "最大速度",
            "group": "运动"
        },
        "damping":               {
            "type":  "slider",
            "min":   0.80,
            "max":   0.98,
            "step":  0.01,
            "label": "惯性（阻尼）",
            "group": "运动"
        },
        "wander_strength":       {
            "type":  "slider",
            "min":   50,
            "max":   400,
            "step":  10,
            "label": "漫游力度",
            "group": "漫游"
        },
        "attract_distance":      {
            "type":  "slider",
            "min":   80,
            "max":   400,
            "step":  10,
            "label": "吸引距离",
            "group": "吸引"
        },
        "attract_strength":      {
            "type":  "slider",
            "min":   100,
            "max":   1000,
            "step":  50,
            "label": "吸引力",
            "group": "吸引"
        },
        "scare_speed_threshold": {
            "type":  "slider",
            "min":   300,
            "max":   2000,
            "step":  50,
            "label": "惊吓-鼠标速度阈值",
            "group": "惊吓"
        },
        "scare_distance":        {
            "type":  "slider",
            "min":   60,
            "max":   300,
            "step":  10,
            "label": "惊吓-触发距离",
            "group": "惊吓"
        },
        "scare_duration":        {
            "type":  "slider",
            "min":   1.0,
            "max":   5.0,
            "step":  0.5,
            "label": "惊吓持续时间",
            "group": "惊吓"
        },
        "wrap_screen":           {
            "type":  "checkbox",
            "label": "屏幕边界环绕",
            "group": "边界"
        },
        "always_on_top":         {
            "type":  "checkbox",
            "label": "窗口置顶",
            "group": "系统"
        },
        "autostart":             {
            "type":  "checkbox",
            "label": "开机自启",
            "group": "系统",
            "note":  "需要管理员权限或手动授权"
        },
    }

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录，None 则自动确定
        """
        if config_dir is None:
            config_dir = self._get_default_config_dir()

        self._config_dir = Path(config_dir)
        self._config_file = self._config_dir / "config.json"
        self._data: dict = {}
        # 记录配置文件最后修改时间，用于检测外部修改实现热重载
        self._last_mtime: Optional[float] = None

        # 确保目录存在
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # 加载或创建配置
        self.load()

    def _get_default_config_dir(self) -> str:
        """
        获取默认配置目录
        开发环境：项目根目录（源码在 src/ 子目录，取其上一级）
        打包后：%APPDATA%/CockroachPet
        """
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            return os.path.join(appdata, "CockroachPet")
        else:
            # 开发环境，使用项目根目录（src/ 的上一级）
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def load(self) -> dict:
        """
        从文件加载配置，缺失项用默认值补全

        Returns:
            完整的配置字典
        """
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
            except (json.JSONDecodeError, IOError):
                loaded = {}
        else:
            loaded = {}

        # 用默认值补全缺失项
        self._data = self.DEFAULT_CONFIG.copy()
        for key in self.DEFAULT_CONFIG:
            if key in loaded:
                # 类型校验和修正
                expected_type = type(self.DEFAULT_CONFIG[key])
                try:
                    self._data[key] = expected_type(loaded[key])
                except (ValueError, TypeError):
                    # 类型不匹配，保留默认值
                    pass

        # 记录当前文件修改时间，供 reload_if_changed 比较
        self._refresh_mtime()

        return self._data

    def _refresh_mtime(self):
        """读取并保存配置文件当前的修改时间"""
        try:
            self._last_mtime = self._config_file.stat().st_mtime
        except OSError:
            self._last_mtime = None

    def reload_if_changed(self) -> bool:
        """
        检测配置文件是否被外部修改，是则重新加载

        用于设置界面与桌宠本体并行运行时，让桌宠感知外部配置更新。
        自己调用 save() 后会同步刷新时间戳，避免误触发重载。

        Returns:
            True 表示文件已变化并完成重载；False 表示无变化
        """
        try:
            mtime = self._config_file.stat().st_mtime
        except OSError:
            return False
        if self._last_mtime is None or mtime != self._last_mtime:
            self.load()  # load 内部会再次刷新 _last_mtime
            return True
        return False

    def save(self) -> bool:
        """
        保存配置到文件

        Returns:
            是否保存成功
        """
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            # 同步时间戳，避免自身保存触发 reload_if_changed
            self._refresh_mtime()
            return True
        except IOError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取单个配置值

        Args:
            key: 配置键名
            default: 不存在时返回的默认值

        Returns:
            配置值，不存在则返回 default
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        设置单个配置值（仅内存，不自动保存）

        Args:
            key: 配置键名
            value: 新值

        Returns:
            是否设置成功
        """
        if key not in self.DEFAULT_CONFIG:
            return False

        # 类型转换
        expected_type = type(self.DEFAULT_CONFIG[key])
        try:
            self._data[key] = expected_type(value)
        except (ValueError, TypeError):
            return False

        return True

    def set_and_save(self, key: str, value: Any) -> bool:
        """设置并立即保存"""
        if self.set(key, value):
            return self.save()
        return False

    def get_all(self) -> dict:
        """返回所有配置的副本"""
        return self._data.copy()

    def reset_to_default(self):
        """恢复默认配置并保存"""
        self._data = self.DEFAULT_CONFIG.copy()
        self.save()

    @staticmethod
    def get_schema() -> dict:
        """返回配置项描述，供设置界面使用"""
        return ConfigManager.SCHEMA.copy()

    @property
    def config_path(self) -> str:
        """返回配置文件完整路径"""
        return str(self._config_file)

    @property
    def config_dir(self) -> str:
        """返回配置目录路径"""
        return str(self._config_dir)


# ---------- 简易测试 ----------
if __name__ == "__main__":
    cm = ConfigManager()
    print(f"配置文件路径: {cm.config_path}")
    print(f"当前配置: {json.dumps(cm.get_all(), indent=2, ensure_ascii=False)}")

    # 测试设置
    cm.set("body_size", 55)
    cm.save()
    print(f"修改后 body_size: {cm.get('body_size')}")

    # 打印 schema
    schema = ConfigManager.get_schema()
    print(f"\n配置项数量: {len(schema)}")
    for k, v in schema.items():
        print(f"  {k}: {v['type']} - {v['label']}")
