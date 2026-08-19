# 🪳 电子桌宠蟑螂 · 白痴级源码教学

> 写给"有 Python 语法基础、但基本没见过库、数学还不错"的大学生。
> 目标是：**读完这份文档，你能彻底看懂这个项目的每一行代码，并且能自己动手改。**

---

## 目录

- [第 0 章 这是什么东西？](#第-0-章-这是什么东西)
- [第 1 章 开工前需要知道的知识](#第-1-章-开工前需要知道的知识)
- [第 2 章 整体架构：一张图看懂](#第-2-章-整体架构一张图看懂)
- [第 3 章 游戏循环：一切的核心](#第-3-章-游戏循环一切的核心)
- [第 4 章 逐文件深度教学](#第-4-章-逐文件深度教学)
  - [4.1 config_manager.py —— 配置数据层](#41-config_managerpy--配置数据层)
  - [4.2 physics_engine.py —— 向量与物理](#42-physics_enginepy--向量与物理)
  - [4.3 behavior_engine.py —— 行为状态机](#43-behavior_enginepy--行为状态机)
  - [4.4 cockroach_model.py —— 几何模型](#44-cockroach_modelpy--几何模型)
  - [4.5 renderer.py —— 画布绘制](#45-rendererpy--画布绘制)
  - [4.6 pet.py —— 顶层门面](#46-petpy--顶层门面)
  - [4.7 main.py —— 入口与窗口](#47-mainpy--入口与窗口)
  - [4.8 settings_ui.py —— 设置界面](#48-settings_uipy--设置界面)
  - [4.9 autostart.py —— 开机自启](#49-autostartpy--开机自启)
- [第 5 章 一帧的生命周期（数据流全景）](#第-5-章-一帧的生命周期数据流全景)
- [第 6 章 动手实验：改着玩](#第-6-章-动手实验改着玩)
- [第 7 章 怎么打包成 exe](#第-7-章-怎么打包成-exe)
- [第 8 章 术语表](#第-8-章-术语表)

---

## 第 0 章 这是什么东西？

一个会**在桌面上到处乱爬的蟑螂**。它用 Python 写，长这样：

- 平时在桌面上**漫游**（随机爬来爬去）
- 你把鼠标**慢慢靠近**它 → 它会被**吸引**（朝你爬过来）
- 你把鼠标**快速甩向**它 → 它会被**吓跑**（惊恐逃跑）
- 你**按住**它不放（长按 0.35 秒）→ 可以**抓起来**，甩手一扔 → 它会被**甩出去**
- 右键点它 → 弹出菜单（设置 / 重置位置 / 退出）
- 系统托盘有个小蟑螂图标 → 可以显示/隐藏、打开设置、退出

它全部由 **tkinter**（Python 自带的 GUI 库）绘制，没有用任何游戏引擎。

> 💡 一句话概括这个项目的本质：
> **一个每秒钟刷新 60 次的"仿真循环"：每帧都做三件事 —— ① 看鼠标在哪、动得快不快 → ② 决定蟑螂"想干嘛"（脑子）→ ③ 计算"身体怎么动"（物理）→ ④ 画出来（渲染）。**

---

## 第 1 章 开工前需要知道的知识

如果你没接触过下面这些，先花 10 分钟扫一眼。**都只需要"见过、知道是干嘛的"程度**，不用精通。

### 1.1 这个项目用到的全部库

| 库 | 干嘛的 | 自带？ |
| --- | --- | --- |
| `tkinter` | Python 自带 GUI，用来画窗口和图形 | ✅ 自带 |
| `pystray` | 系统托盘图标（右下角小图标） | ❌ 需安装 |
| `PIL` / `Pillow` | 生成托盘图标图片 | ❌ 需安装 |
| `winreg` | 操作 Windows 注册表（开机自启用） | ✅ 自带（仅 Windows） |
| `json` | 读写配置文件 | ✅ 自带 |
| `os` / `sys` / `threading` | 系统相关 | ✅ 自带 |
| `math` / `random` | 数学和随机数 | ✅ 自带 |
| `dataclasses` | 快速定义"装数据的类" | ✅ 自带（Python 3.7+） |
| `enum` | 定义枚举（一组命名常量） | ✅ 自带 |

> 安装依赖命令（项目根目录下）：
>
> ```bash
> pip install pystray Pillow
> ```

### 1.2 你需要懂的 4 个 Python 特性

#### ① `@dataclass` —— "装数据的盒子"

普通类要写一堆 `__init__` 赋值，太啰嗦。`@dataclass` 帮你自动生成。

```python
from dataclasses import dataclass

@dataclass
class AntennaData:
    base: tuple          # 触角基部坐标
    segments: list       # 各节坐标
    tip: tuple           # 末端坐标
```

相当于自动帮你写了 `__init__(self, base, segments, tip)` 并一一赋值。**本质是一个"数据盒子"**，专门用来把一组数据打包传递。本项目里 `CockroachRenderData` 就是最大号的"盒子"，一帧渲染所需的**所有**数据都装在里面。

#### ② `Enum` —— 给一组常量起名字

```python
from enum import Enum, auto

class BehaviorState(Enum):
    ROAM = auto()      # 漫游
    OBSERVE = auto()   # 观察
    ATTRACT = auto()   # 被吸引
    SCARED = auto()    # 惊吓
    GRABBED = auto()   # 被抓
```

`auto()` 自动给每个成员一个数字（1、2、3…）。好处是代码里写 `BehaviorState.SCARED` 而不是写魔法数字 `3`，**可读性暴增**。你可以用 `.name` 拿名字（如 `"SCARED"`），用 `==` 比较。

#### ③ 类型标注（Type Hint）—— 注释的"高级版"

```python
def update(self, dt: float, mouse_x: float) -> tuple:
```

`dt: float` 的意思是"dt 应该是浮点数"。**Python 不强制**，但让读代码的人（和 IDE）知道每个参数是什么。这个项目标注得很全，是很好的学习样本。

#### ④ `__slots__` —— 省内存的小优化

```python
class Vector2:
    __slots__ = ('x', 'y')
```

普通类实例有个 `__dict__` 字典装属性；`__slots__` 告诉 Python"这个类只有 x、y 两个属性"，省内存、访问更快。**性能优化用，知道就行，不用自己写。**

### 1.3 屏幕坐标和角度（重点中的重点！）

游戏/图形里用的坐标系和数学课上的**不一样**，一定要先建立直觉：

```text
  屏幕坐标系（y 向下为正！）
  
  (0,0) ────────────→ x 增大（向右）
   │
   │
   ↓ y 增大（向下）
```

- **角度单位是弧度（radian）**，不是度。$\pi$ 弧度 = 180°。
- **角度 0 表示"朝右"**，正方向是**顺时针**（因为 y 向下）。

```text
         y↓
         |
    -90° |  +90°  （注意！数学里这是逆时针为正，这里反过来）
         |
 180° ───┼─── 0°  （0 朝右）
```

对应到代码就是 `physics_engine.py` 里的：

```python
def angle(self) -> float:
    """向量角度（弧度，0=右，正值=顺时针）"""
    return math.atan2(self.y, self.x)
```

`math.atan2(y, x)` 是"已知横纵坐标求角度"的函数。而 `math.cos(angle)` / `math.sin(angle)` 是"已知角度求方向"：

```python
@staticmethod
def from_angle(angle: float, length: float = 1.0) -> 'Vector2':
    """从角度创建向量"""
    return Vector2(math.cos(angle) * length, math.sin(angle) * length)
```

> 📐 **记忆口诀**：`cos` 管 x、`sin` 管 y；`atan2(y, x)` 是逆运算。

### 1.4 向量（Vector）—— 这个项目的心脏

向量 = **既有大小又有方向的箭头**。在 2D 里用一个 `(x, y)` 对表示。

比如 `Vector2(3, 4)` 就是"往右 3、往下 4"的箭头，长度是 $\sqrt{3^2+4^2}=5$。

这个项目里 **Vector2 到处都是**：位置是向量、速度是向量、力是向量、方向是向量。所以代码里专门写了一个 `Vector2` 类，还重载了运算符（`+`、`-`、`*`），让向量能像数字一样直接加减乘：

```python
v1 + v2    # 两个向量相加 = 两个箭头首尾相连
v1 - v2    # 相减 = 从 v2 指向 v1 的箭头
v * 2      # 向量拉长 2 倍
v.normalize()  # 变成"单位向量"（长度 1，方向不变）
v.length()     # 向量的长度（模）
v.dot(o)       # 点积
```

> 💡 你会看到两个文件里都定义了 `Vector2`（`physics_engine.py` 和 `behavior_engine.py`）。作者为了模块独立各自复制了一份。**实际项目中更好的做法是只留一份然后 import**，这个"缺点"你可以记住。

### 1.5 什么是"面向对象"在这个项目里的体现

这个项目是教科书级的**分层设计**，每层是一个类，各干各的事：

```text
CockroachPetWindow（窗口，管显示）
   │  用了
   ▼
CockroachPet（门面，管"指挥"）
   │  分别拥有
   ├──→ ConfigManager     （管配置，纯数据）
   ├──→ PhysicsEngine     （管物理，纯计算）
   ├──→ BehaviorEngine    （管脑子，纯决策）
   ├──→ CockroachModel    （管身体，纯几何）
   ├──→ AutostartManager  （管开机自启）
CockroachRenderer（渲染器，被窗口和设置界面共用）
```

**关键思想**：每一层都不知道别的层怎么实现的。

- 行为引擎只管"决定施加什么力"，不知道这力最后怎么变成位置；
- 物理引擎只管"把力积分成位置"，不知道蟑螂长什么样；
- 模型只管"算身体各部位坐标"，不知道屏幕长什么样；
- 渲染器只管"画"，不知道蟑螂为什么会动。

这就是**单一职责原则**——每个类只做一件事。改一个地方不影响别的。

---

## 第 2 章 整体架构：一张图看懂

### 2.1 文件地图

```text
ElectricalCockroach/
│
├── src/                   ← 📦 全部源码
│   ├── main.py            ← 🚪 程序入口（双击运行这个）
│   ├── pet.py             ← 🧩 门面类 CockroachPet（连接所有模块）
│   ├── physics_engine.py  ← 🧲 物理引擎（位置、速度、转向）
│   ├── behavior_engine.py ← 🧠 行为引擎（状态机：漫游/吸引/惊吓…）
│   ├── cockroach_model.py ← 🦗 几何模型（算蟑螂每个部位坐标）
│   ├── renderer.py        ← 🎨 渲染器（把坐标画到屏幕上）
│   ├── config_manager.py  ← 📋 配置管理（读写 config.json）
│   ├── settings_ui.py     ← ⚙️ 设置界面（改参数）
│   ├── autostart.py       ← 🚀 开机自启管理
│   └── __init__.py        ← 📦 让 src 变成"包"
├── config.json            ← 📄 配置文件（改这里就能改参数）
└── …（其余：assets / spec / 文档等）
```

### 2.2 数据流图（核心！建议反复看）

```text
                       ┌─────────────────────────────┐
                       │       main.py（每帧循环）      │
                       │  1. 读鼠标位置/速度/按键        │
                       │  2. 调用 pet.update(...)      │
                       └──────────────┬──────────────┘
                                      │ 输入：鼠标位置、鼠标速度、
                                      │      是否按住、是否点在蟑螂上
                                      ▼
                       ┌─────────────────────────────┐
                       │       pet.py（门面）           │
                       │  ① behavior.update()         │
                       │      → 决定"什么状态 + 施加什么力" │
                       │  ② physics.add_force()       │
                       │      → 把力喂给物理             │
                       │  ③ physics.update()          │
                       │      → 算出新位置/朝向          │
                       │  ④ model.compute()           │
                       │      → 算出所有部位坐标         │
                       └──────────────┬──────────────┘
                                      │ 输出：CockroachRenderData
                                      ▼
                       ┌─────────────────────────────┐
                       │       renderer.py            │
                       │  把数据画到 tkinter Canvas    │
                       └─────────────┬───────────────┘
                                     ▼
                            屏幕上的蟑螂 🪳
```

**一句话版本**：`鼠标 → 脑子(behavior) → 力 → 物理(physics) → 位置 → 模型(model) → 坐标 → 渲染(renderer) → 屏幕`。

---

## 第 3 章 游戏循环：一切的核心

### 3.1 动画的本质 = 快速切换静止画面

电影 24 帧/秒、游戏 60 帧/秒。**"会动"其实是一秒切换 60 张几乎一样的图**，每次只变一点点。

本项目用 tkinter 的 `after` 实现帧循环，代码在 `main.py`：

```python
def _update(self):
    """每帧更新：物理、行为、渲染"""
    if not self._running:
        return

    # ...（读鼠标、算鼠标速度、调用 pet.update、渲染）...

    self.master.after(int(self._dt * 1000), self._update)  # 关键！这一行
```

`master.after(毫秒, 函数)` 的意思是：**"过 16 毫秒后，再调用一次 `_update`"**。

于是 `_update` 被一遍遍调用，形成无限循环：

```text
_update() 调用完 → 等 16ms → 再调用 _update() → 等 16ms → ...
```

每秒 1000/16 ≈ **60 次**，这就是 60 FPS（帧率）。

### 3.2 `dt` —— 帧间隔时间

每两帧之间的时间差叫 `dt`（delta time，变化量时间）。这里固定为 `1/60` 秒：

```python
self._fps = 60
self._dt = 1.0 / self._fps   # = 0.0166 秒
```

为什么所有物理计算都要乘 `dt`？因为**速度×时间=位移**。速度是"每秒多少像素"，要算"这一帧走了多远"，就得乘以这一帧持续的时间：

```python
self.body.position += self.body.velocity * dt   # 位置 += 速度 × 时间
```

> 💡 不用 dt 的话，程序在不同电脑上帧率不同，蟑螂速度就不一样。用了 dt，**任何帧率下速度都一致**。这是游戏开发的标准做法。

### 3.3 为什么用 `winfo_pointerx/y` 而不是鼠标事件？

你可能奇怪：为什么不用 `<Motion>` 事件（鼠标移动事件）？

看 `main.py` 里的注释：

```python
# <Motion> 在全屏透明窗口上可能不会被透明区域触发，
# 因此主循环中使用 winfo_pointerx/y 获取全局鼠标位置。
```

因为窗口是**透明的**，tkinter 的鼠标事件在透明区域可能不触发。所以改用 `winfo_pointerx()` —— 这是 tkinter 提供的方法，**直接问操作系统"鼠标现在在哪"**，不问"有没有事件"。

```python
self._mouse_x = self.master.winfo_pointerx()
self._mouse_y = self.master.winfo_pointery()
```

### 3.4 鼠标速度是怎么算出来的？（重点）

蟑螂要区分"鼠标慢慢靠近（吸引）"和"鼠标快速靠近（吓跑）"，所以每帧都要算鼠标速度。

代码在 `main.py` 和 `pet.py` 里各有一份（原理相同）：

```python
# 鼠标速度（像素/秒）
dx = self._mouse_x - self._last_mouse_x    # 这一帧鼠标横移了多少
dy = self._mouse_y - self._last_mouse_y    # 这一帧鼠标纵移了多少
raw_speed = math.hypot(dx, dy) / self._dt  # 距离 ÷ 时间 = 速度（像素/秒）
self._mouse_speed = self._mouse_speed * 0.6 + raw_speed * 0.4   # 平滑
self._last_mouse_x = self._mouse_x
self._last_mouse_y = self._mouse_y
```

逐行解释：

1. `dx`/`dy`：这一帧鼠标移动的距离（相对上一帧）。
2. `math.hypot(dx, dy)`：勾股定理求斜边 = 移动的总距离 $\sqrt{dx^2+dy^2}$。
3. 除以 `dt`：距离 ÷ 时间 = 速度（单位：像素/秒）。
4. **指数平滑**：`新速度 = 旧速度×0.6 + 本次速度×0.4`。

为什么平滑？因为鼠标瞬间抖动会导致速度剧烈跳动，平滑后速度更稳定。0.6/0.4 是权重，**越靠前的数字越大，越"恋旧"**。这个公式会在行为引擎里再见到一次，是同一个套路。

---

## 第 4 章 逐文件深度教学

下面按**依赖顺序**（从最底层到最上层）讲解，这样你能顺着逻辑走：先数据、再物理、再行为、再几何、再渲染、最后串起来。

---

### 4.1 config_manager.py —— 配置数据层

**一句话**：这个文件负责"读配置、写配置、给默认值、描述每个配置项长什么样"。

#### 它解决什么问题？

蟑螂的大小、速度、惊吓阈值……这些参数不该写死在代码里，否则改一次要改代码。所以放进一个 `config.json` 文件，程序启动时读进来。**改参数 = 改文件，不用动代码。**

#### 核心结构 1：`DEFAULT_CONFIG` —— 默认配置字典

```python
DEFAULT_CONFIG = {
    "body_size": 40,            # 蟑螂身体大小（像素）
    "opacity": 1.0,             # 窗口透明度 0.0~1.0
    "speed_max": 600,           # 最大移动速度（像素/秒）
    "damping": 0.93,            # 速度阻尼系数
    "wander_strength": 250,     # 随机游走力度
    ...
    "wrap_screen": True,        # 屏幕边界是否环绕
    "autostart": False,         # 是否开机自启
}
```

这是一个**普通的字典**：键是参数名，值是默认值。整个程序到处都在 `cfg.get("xxx", 默认值)`，就是从这拿参数。

#### 核心结构 2：`SCHEMA` —— 配置项"说明书"

```python
SCHEMA = {
    "body_size": {
        "type": "slider",       # 设置界面用滑块
        "min": 20, "max": 80, "step": 5,
        "label": "蟑螂大小",
        "group": "外观"
    },
    ...
    "wrap_screen": {
        "type": "checkbox",     # 设置界面用复选框
        "label": "屏幕边界环绕",
        "group": "边界"
    },
}
```

这份 `SCHEMA` 告诉设置界面（`settings_ui.py`）：**每个参数用什么控件、范围多少、显示什么名字、归哪一组**。设置界面就是靠遍历这个字典**自动生成**控件的——这叫**"数据驱动 UI"**，加一个新参数 = 在 SCHEMA 里加一条，界面自动多一个滑块，非常优雅。

#### 核心方法逐个讲

**`load()` —— 从文件读配置，缺的用默认值补**

```python
def load(self) -> dict:
    # 1. 尝试读文件
    if self._config_file.exists():
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, IOError):
            loaded = {}    # 文件坏了就当空配置
    else:
        loaded = {}

    # 2. 用默认值打底，再覆盖用户配置
    self._data = self.DEFAULT_CONFIG.copy()
    for key in self.DEFAULT_CONFIG:
        if key in loaded:
            expected_type = type(self.DEFAULT_CONFIG[key])
            try:
                self._data[key] = expected_type(loaded[key])   # 类型校验
            except (ValueError, TypeError):
                pass    # 类型不对就保留默认值

    self._refresh_mtime()   # 记录文件修改时间
    return self._data
```

要点：

- `encoding="utf-8"`：因为配置文件里有中文注释，必须指定 UTF-8。
- `expected_type(loaded[key])`：强制把读到的值转成默认值的类型。比如默认值是 `int`（40），用户手滑把 json 写成 `"四十"` 字符串，这里会转类型失败 → 保留默认值。**这是"防御性编程"**。
- `_refresh_mtime()`：记录文件最后修改时间，供"热重载"用（见下）。

**`save()` —— 写回文件**

```python
def save(self) -> bool:
    with open(self._config_file, "w", encoding="utf-8") as f:
        json.dump(self._data, f, indent=2, ensure_ascii=False)
    self._refresh_mtime()   # 关键：保存后刷新时间戳
    return True
```

`indent=2` 让 JSON 文件有缩进（人类可读）；`ensure_ascii=False` 让中文不被转成 `\uXXXX`。

**`reload_if_changed()` —— 热重载（很聪明的设计）**

```python
def reload_if_changed(self) -> bool:
    try:
        mtime = self._config_file.stat().st_mtime
    except OSError:
        return False
    if self._last_mtime is None or mtime != self._last_mtime:
        self.load()
        return True
    return False
```

原理：`st_mtime` 是文件的最后修改时间。**每次启动程序记下这个时间；之后每隔一会儿检查一下文件时间变没变**。变了就重新 load。

这有什么用？—— **设置界面和桌宠本体是两个进程**（后面讲 settings_ui 会细说）。设置界面改了参数并写入 config.json，桌宠本体**不用重启**，靠这个函数感知变化并重新加载。这就是"改完设置，蟑螂立刻变"的秘密。

`get()` / `set()` / `get_all()` 就是字典的薄封装，很简单，不多讲。

---

### 4.2 physics_engine.py —— 向量与物理

**一句话**：这个文件管"蟑螂的身体怎么移动"——位置、速度、朝向、转向，纯数学，不知道蟑螂长什么样。

#### 4.2.1 `Vector2` —— 二维向量类

最底层的是 `Vector2`。前面第 1.4 节已经讲过概念，这里看几个关键实现：

```python
class Vector2:
    __slots__ = ('x', 'y')

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)
```

`__add__`、`__sub__`、`__mul__` 这些"双下划线方法"（dunder methods）是 Python 的**运算符重载**：定义了它们，`v1 + v2` 才会真的调用 `__add__`。写一次，到处能用 `+ - *`，代码像数学一样简洁。

```python
def length(self) -> float:
    """向量长度"""
    return math.sqrt(self.x * self.x + self.y * self.y)

def length_squared(self) -> float:
    """向量长度的平方（避免开方，用于比较）"""
    return self.x * self.x + self.y * self.y
```

注意 `length_squared`：比较距离时**不需要真的开方**，直接比平方更快（开方很慢）。这是性能优化的经典技巧。代码里 `_hit_test` 就用了：

```python
dx = x - cx
dy = y - cy
return dx * dx + dy * dy <= size * size    # 距离平方 ≤ 半径平方
```

#### 4.2.2 `PhysicsBody` —— 物体的物理状态

```python
class PhysicsBody:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.position = Vector2(x, y)          # 位置
        self.velocity = Vector2(0.0, 0.0)      # 速度
        self.acceleration = Vector2(0.0, 0.0)  # 加速度
        self.previous_position = Vector2(x, y) # 上一帧位置
        self.orientation = 0.0          # 身体朝向（弧度，0=右）
        self.angular_velocity = 0.0     # 角速度（转向速度，弧度/秒）
        self.forward_speed = 0.0        # 沿朝向的前进速度
```

这就是"一辆小车"的全部状态：

- `position`：车在哪
- `velocity`：车多快、往哪
- `orientation`：车头朝哪（重要！蟑螂有头，不能横着走）
- `angular_velocity`：转向有多快

#### 4.2.3 `PhysicsEngine` —— "汽车转弯模型"（本项目物理的精髓）

**这是整个项目最值得反复读的物理设计。** 注释里写得很清楚：

```python
"""
核心变更：
- 物体有固定的身体朝向 orientation
- 行为层提供目标朝向（舵角）和前进油门 thrust
- 朝向只能以有限角速度改变，形成弧线轨迹
- 速度始终沿当前朝向，避免原地绕自身中轴旋转
"""
```

想象蟑螂是一辆**不能横着走的汽车**：

1. 行为层告诉它"往那个方向开"（目标朝向）和"油门踩多大"（thrust）；
2. 车头不能瞬间转向，只能**以有限的速度转弯**（角速度有上限）；
3. 车**永远沿车头方向前进**（不能平移）；
4. 于是它走的是**弧线**，转弯有过程——这就是"生物感"的来源。

**`update()` 一帧的物理流程**（这是核心中的核心，逐段讲）：

```python
def update(self, dt, bounds=None, wrap=False):
    # 保存上一帧位置（供计算朝向）
    self.body.previous_position = self.body.position.copy()

    # ---- 1. 计算"目标角速度"：现在朝向 → 目标朝向 还差多少度 ----
    angle_diff = self._shortest_angle_diff(self._target_orientation, self.body.orientation)
    target_angular_velocity = angle_diff * self.steering_gain * steering_mult
```

`_shortest_angle_diff` 求两个角度之间的**最短差**（处理 359° 和 1° 只差 2° 而不是 358° 的情况）：

```python
def _shortest_angle_diff(self, target, current):
    diff = target - current
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return diff
```

然后"差多少度 × 转向增益 = 该用多快的角速度转过去"。**差得越多，转得越快**（但后面会限制上限）。

```python
    # 限制最大转向速率
    max_angular = self.max_angular_velocity * angular_mult
    target_angular_velocity = max(-max_angular, min(max_angular, target_angular_velocity))
```

```python
    # ---- 2. 角速度平滑趋近目标（模拟转向惯性）----
    response = self.steering_response * response_mult
    self.body.angular_velocity += (target_angular_velocity - self.body.angular_velocity) * response * dt
    self.body.angular_velocity *= self.angular_damping * damping_mult
```

注意这里又是**平滑趋近**的套路：`当前值 += (目标值 - 当前值) × 响应速度 × dt`。角速度不会"啪"地跳到目标，而是平滑逼近——像方向盘打过去有个过程。

```python
    # ---- 3. 更新朝向 ----
    self.body.orientation += self.body.angular_velocity * dt

    # ---- 4. 前进速度由油门驱动 ----
    target_speed = self._thrust / max(1.0, self.mass * 0.5)
    target_speed = max(-self.max_speed * 0.3, min(self.max_speed, target_speed))
    self.body.forward_speed += (target_speed - self.body.forward_speed) * self.thrust_response * dt
    self.body.forward_speed *= self.damping
```

油门（thrust）被当成"目标速度"，然后平滑趋近，再乘阻尼 `damping`（0.93，每帧速度保留 93%，即每次衰减 7%）。阻尼让速度慢慢衰减，像松开油门后的滑行。

```python
    # ---- 5. 速度始终沿当前朝向 ----
    self.body.velocity = Vector2.from_angle(self.body.orientation, self.body.forward_speed)

    # ---- 6. 更新位置：沿当前朝向弧线前进 ----
    self.body.position += self.body.velocity * dt
```

关键在第 5 步：**速度的方向永远等于车头朝向**。所以只要车头转了，速度方向就跟着转，走出来的就是弧线。

#### 4.2.4 `add_force` —— 兼容旧接口的"力 → 油门+朝向"转换

行为引擎输出的是"力向量"（有方向有大小）。物理引擎把它拆成**油门 + 目标朝向**：

```python
def add_force(self, fx, fy):
    force = Vector2(fx, fy)
    self._thrust = force.length()          # 力的大小 = 油门
    if self._thrust > 0.01:
        new_target = force.angle()         # 力的方向 = 目标朝向
        diff = self._shortest_angle_diff(new_target, self.body.orientation)
        if abs(diff) > 0.08:               # 死区：偏差太小就不更新
            self._target_orientation = new_target
```

注意那个 `0.08` 的死区（约 4.6°）：如果力方向和当前朝向只差一点点，就不更新目标朝向。**为什么？** 注释说了——直线行走时力的方向会有微小抖动，如果每次抖动都更新目标朝向，车头会左右摆、震荡。死区让它在直线时保持稳定。这是很精细的调参功夫。

#### 4.2.5 惊吓时转弯更"灵活"

```python
scared_angular_multiplier = 3.0    # 惊吓时最大角速度 ×3
scared_steering_multiplier = 2.5   # 惊吓时舵角增益 ×2.5
scared_response_multiplier = 2.5   # 惊吓时响应速度 ×2.5
scared_damping_multiplier = 0.70   # 惊吓时角阻尼 ×0.7
```

被吓时，蟑螂能**更快转向、更急转弯**，逃跑路线更锐利。这就是"吓得到处乱窜"的感觉来源。

#### 4.2.6 边界处理：反弹 vs 环绕

```python
def _apply_bounds(self, bounds):   # 反弹模式
    if pos.x < min_x:
        pos.x = min_x
        if vel.x < 0:
            vel.x = -vel.x * 0.3   # 反弹但损失 70% 能量

def _wrap_position(self, bounds):  # 环绕模式（贪吃蛇效果）
    if pos.x < min_x:
        pos.x += width             # 从左边出去，从右边进来
    elif pos.x > max_x:
        pos.x -= width
```

反弹 = 撞墙弹回（还损失能量，很真实）；环绕 = 出左边进右边（像贪吃蛇/小蜜蜂）。

---

### 4.3 behavior_engine.py —— 行为状态机

**一句话**：这个文件是蟑螂的"脑子"。它每帧决定三件事：**① 我现在处于什么状态 ② 该施加多大的力 ③ 是不是在惊吓**。

#### 4.3.1 状态机（State Machine）概念

蟑螂的行为可以分成几个互斥的"状态"，**任何时刻只能处于一个状态**：

```text
        ┌─────────┐
        │  ROAM   │ 漫游：随机乱爬
        └────┬────┘
             │
        ┌────▼────┐
        │ OBSERVE │ 观察：停下来，触角乱晃
        └────┬────┘
             │
    ┌────────┴─────────┐
    ▼                  ▼
┌─────────┐      ┌─────────┐
│ ATTRACT │      │ SCARED  │
│ 被吸引   │      │ 被惊吓   │
└─────────┘      └─────────┘
                    │
                 （抓取时）
                    ▼
              ┌─────────┐
              │ GRABBED │ 被抓
              └─────────┘
```

状态之间靠"条件"转换。这就是**状态机**——游戏 AI 最基础也最重要的设计模式。

#### 4.3.2 `update()` —— 每帧的决策流程

```python
def update(self, dt, roach_pos, mouse_pos, mouse_pressed, is_grabbed, screen_size, wrap, roach_angle):
    roach = Vector2(roach_pos[0], roach_pos[1])   # 蟑螂位置
    mouse = Vector2(mouse_pos[0], mouse_pos[1])   # 鼠标位置
    ...
    # 更新鼠标速度（和 main.py 一样的指数平滑）
    ...
    # 更新冷却计时器
    if self._scare_cooldown > 0:
        self._scare_cooldown -= dt
    ...
    # 1. 决定新状态
    new_state = self._determine_state(...)
    # 2. 根据状态算力
    if new_state == BehaviorState.GRABBED:
        force = (0, 0)
    elif new_state == BehaviorState.SCARED:
        force = self._scared_force(...)
    ...
    self.state = new_state
    return (self.state, force, self.state == BehaviorState.SCARED)
```

#### 4.3.3 `_determine_state()` —— 状态转换的"大脑"

**优先级的顺序很重要**，从上到下判断：

```python
def _determine_state(self, ...):
    # 0. 被抓优先（优先级最高）
    if is_grabbed:
        return BehaviorState.GRABBED

    # 1. 正在惊吓中 → 继续惊吓，直到计时结束
    if self.state == BehaviorState.SCARED and self._scared_timer > 0:
        return BehaviorState.SCARED

    # 2. 检测惊吓触发：鼠标快 + 近 + 冷却已过
    if self._scare_cooldown <= 0:
        weight = self._directional_weight(roach, mouse, sw, sh)
        effective_scare_dist = scare_dist * weight      # 前方更敏感
        effective_scare_speed = scare_speed / weight
        if dist < effective_scare_dist and self._mouse_velocity > effective_scare_speed:
            self._scared_timer = self._config.get("scare_duration", 2.5)
            self._scare_cooldown = 1.0                  # 1 秒冷却
            return BehaviorState.SCARED

    # 3. 鼠标近 + 慢 → 吸引
    if self._mouse_velocity < scare_speed * 0.5:
        weight = self._directional_weight(roach, mouse, sw, sh)
        if dist < attract_dist * weight:
            return BehaviorState.ATTRACT

    # 4. 正在观察中 → 继续观察
    if self.state == BehaviorState.OBSERVE and self._observe_timer > 0:
        return BehaviorState.OBSERVE

    # 5. 漫游时 10% 概率随机进入观察
    if self.state == BehaviorState.ROAM and self._observe_cooldown <= 0:
        ...
        if random.random() < 0.10:
            return BehaviorState.OBSERVE

    # 6. 默认漫游
    return BehaviorState.ROAM
```

几个设计亮点：

#### ① 惊吓是"持续状态"，用计时器控制

```python
self._scared_timer = self._config.get("scare_duration", 2.5)
```

一旦触发惊吓，`_scared_timer` 设为 2.5 秒，每帧递减，**在归零前一直保持惊吓**。这样蟑螂不会因为鼠标停一下就立刻恢复，逃跑过程是连续的。

#### ② 冷却（cooldown）防止"反复横跳"

```python
self._scare_cooldown = 1.0
```

触发一次惊吓后 1 秒内不能再触发，否则鼠标一直晃动会让蟑螂在"吓→停→吓"之间疯狂切换，看着很蠢。

**③ 前方 120° 更敏感 —— `_directional_weight`**

蟑螂的感知不是全向的，**正面更敏感**。看这个函数：

```python
def _directional_weight(self, roach, mouse, sw, sh) -> float:
    diff = self._toroidal_diff(roach, mouse, sw, sh)
    mouse_angle = math.atan2(diff.y, diff.x)     # 鼠标相对蟑螂的方位角
    rel = mouse_angle - self._roach_angle        # 相对蟑螂朝向的偏角
    # 归一化到 [-π, π]
    while rel > math.pi: rel -= 2 * math.pi
    while rel < -math.pi: rel += 2 * math.pi
    # 前方 120°（±60°=±π/3）返回 1.4，否则 0.7
    return 1.4 if abs(rel) <= math.pi / 3 else 0.7
```

`rel` 是"鼠标相对蟑螂正前方的偏角"。偏角 ≤ 60°（正前方 120° 扇形内）→ 权重 1.4（更敏感）；否则 0.7。

这个权重怎么用？看状态判断：

```python
effective_scare_dist = scare_dist * weight       # 前方警戒距离 ×1.4 = 更远就触发
effective_scare_speed = scare_speed / weight     # 前方触发速度阈值 ÷1.4 = 更慢就触发
```

**前方**：警戒距离变远、触发阈值变低 → 更容易吓到、更容易吸引。
**后方**：反之，迟钝一点。

这是很高级的生物模拟思想——蟑螂主要感知前方。

**④ 环形边界的距离计算 —— `_toroidal_diff`**

如果开启了屏幕环绕（贪吃蛇模式），屏幕左右、上下是相连的。那么"鼠标在屏幕最右边、蟑螂在最左边"时，它们的真实距离其实很近（就隔一条边界）。`_toroidal_diff` 就负责算这种**环形最短距离**：

```python
def _toroidal_diff(self, roach, mouse, sw, sh) -> Vector2:
    if not self._wrap or sw <= 0 or sh <= 0:
        return mouse - roach
    dx = mouse.x - roach.x
    dy = mouse.y - roach.y
    if abs(dx) > sw * 0.5:      # 水平差超过半屏 → 从另一边绕更近
        dx -= sw * (1 if dx > 0 else -1)
    if abs(dy) > sh * 0.5:
        dy -= sh * (1 if dy > 0 else -1)
    return Vector2(dx, dy)
```

如果水平差超过半屏，说明"往反方向穿过边界"更近，就减去一个屏宽。这样蟑螂隔着屏幕也能"看到"鼠标，会朝边界爬过去（配合渲染器的幽灵副本实现视觉上的连续）。

#### 4.3.4 各状态的力计算

**漫游力 `_roam_force`** —— 随机游走 + 边缘排斥

```python
def _roam_force(self, roach, dt, sw, sh):
    # 每隔 0.3~1.5 秒随机换一个方向
    self._roam_new_direction_timer -= dt
    if self._roam_new_direction_timer <= 0:
        self._wander_angle += random.uniform(-direction_change, direction_change)
        self._roam_new_direction_timer = random.uniform(0.3, 1.5)

    wander_force = Vector2.from_angle(self._wander_angle, wander_strength)
    edge_force = self._edge_repulsion(roach, sw, sh, edge_margin, edge_repulsion)
    return (wander_force + edge_force).to_tuple()
```

`_wander_angle` 是当前漫游方向，每隔随机时间在旧方向上加一个随机偏移（**不是完全重新随机，而是"偏转"**，这样路径更连贯、像生物而不是乱跳）。然后加上边缘排斥力，防止它卡在屏幕边上。

**吸引力 `_attract_force`** —— 指向鼠标的引力

```python
diff = self._toroidal_diff(roach, mouse, sw, sh)
dist = diff.length()

if dist > dead_zone:    # 死区外才施加引力（死区内会抖动）
    to_mouse = diff.normalize()
    strength = attract_strength / (1.0 + dist * 0.03)   # 距离衰减：远强近弱
    strength *= self._directional_weight(roach, mouse, sw, sh)  # 前方吸引更强
    force += to_mouse * strength

# 30% 概率加一点随机扰动（保持生物感）
if random.random() < 0.3:
    force += Vector2.from_angle(random.uniform(0, 2*math.pi), wander_strength * 0.2)

force += self._edge_repulsion(...)
```

几个细节：

- **死区（dead_zone）**：鼠标离蟑螂太近（30px 内）就不施加引力。否则蟑螂会"钻到鼠标底下"疯狂抖动。
- **距离衰减**：`attract_strength / (1 + dist*0.03)` —— 距离越远力越小，模仿"引力随距离减弱"。
- **随机扰动**：30% 概率加个小随机力，让靠近过程不那么直愣愣，更生动。

**惊吓力 `_scared_force`** —— 逃离鼠标

```python
diff = self._toroidal_diff(roach, mouse, sw, sh)
away = -diff                      # 背离鼠标的方向
away_dir = away.normalize()

flee_force = away_dir * flee_strength    # 主逃离力

# 微弱的侧向偏移，避免完全机械直线
perpendicular = Vector2(-away_dir.y, away_dir.x)   # 垂直向量
side_strength = random.uniform(-0.12, 0.12) * flee_strength
side_force = perpendicular * side_strength

force = flee_force + side_force
```

主方向是"背离鼠标"，叠加一个很小的随机侧向力，让逃跑路径略有弧度，不那么机械。逃跑时边缘排斥力 ×1.5，防止它一头撞进边界出不去。

**观察力 `_observe_force`** —— 原地休息 + 偶尔转身

```python
if self._observe_turn_timer <= 0:
    self._observe_turn_timer = random.uniform(1.5, 3.5)
    if random.random() < 0.4:      # 40% 概率转身
        turn_dir = random.choice([-1, 1])
        angle = self._roach_angle + math.pi / 2 * turn_dir + random.uniform(-0.3, 0.3)
        return Vector2.from_angle(angle, 35).to_tuple()
return (0.0, 0.0)
```

观察状态基本不施加力（原地静止），但每隔 1.5~3.5 秒有 40% 概率施加一个**垂直朝向的微小力**，让身体缓慢转个角度"环顾四周"。触角的活跃探测由模型层（根据 OBSERVE 状态）负责。

#### 4.3.5 记录一个设计模式：`suppress_scare`

```python
def suppress_scare(self, duration: float = 1.5):
    self._scare_cooldown = max(self._scare_cooldown, duration)
    self._mouse_velocity = 0.0
```

**用途**：当你把蟑螂甩出去后，鼠标速度可能还很高，会立刻触发惊吓。这个函数把惊吓冷却设为 1.5 秒并清零鼠标速度，防止"甩出去后马上又吓跑"的误触。这是针对具体 bug 的补丁式修复，很有借鉴意义。

---

### 4.4 cockroach_model.py —— 几何模型

**一句话**：这个文件把"身体中心点 + 朝向 + 速度"变成"头、胸、腹、触角、6 条腿、翅膀、尾须的所有坐标"。它管的是**蟑螂长什么样、怎么动**，纯几何数学。

#### 4.4.1 身体坐标系 —— 一切几何的根基

在 `compute()` 开头，定义了四个关键方向向量：

```python
cos_a = math.cos(angle)
sin_a = math.sin(angle)

forward = (cos_a, sin_a)        # 头朝向（前）
backward = (-cos_a, -sin_a)     # 尾朝向（后）
left = (-sin_a, cos_a)          # 左侧
right = (sin_a, -cos_a)         # 右侧
```

这是"局部坐标系"：不管蟑螂身体转到哪个角度，`forward` 总是指向它的头，`left/right` 总是指向它左右。**所有部位都基于这个坐标系计算**，所以身体转来转去，各个部位的相对位置永远正确。

怎么理解 `left = (-sin_a, cos_a)`？这是把 `forward` 顺时针旋转 90° 得到的结果（在 y 向下的坐标系里）。可以用具体数字验证：angle=0 时，`forward=(1,0)`（朝右），`left=(0,1)`（朝下，即屏幕上的"下"），`right=(0,-1)`（朝上）。你可以在纸上画一下。

#### 4.4.2 解剖结构比例 —— 常量表

```python
HEAD_RATIO = 0.12            # 头部半径比例
THORAX_LENGTH_RATIO = 0.20   # 胸部长度
ABDOMEN_LENGTH_RATIO = 0.80  # 腹部长度（写实修长）
ANTENNA_LENGTH_RATIO = 3.8   # 触角总长（远超身体！）
ANTENNA_SEGMENTS = 14        # 触角节数
...
```

**所有部位尺寸都 = body_size × 比例常量**。这样：

1. 只改 `body_size`，整只蟑螂按比例缩放，不用重写所有坐标；
2. 想调"头多大、触角多长"，改一个常量即可。

这就是**参数化建模**：用一组参数描述整个形状。

#### 4.4.3 三大部分：头、胸、腹的中心点

```python
thorax_length = size * self.THORAX_LENGTH_RATIO
abdomen_length = size * self.ABDOMEN_LENGTH_RATIO

# 身体中心在胸部和腹部交界处偏前
thorax_center = self._offset((x, y), forward, thorax_length * 0.6)
abdomen_center = self._offset((x, y), backward, abdomen_length * 0.5)
head_center = self._offset((x, y), forward, thorax_length * 0.6 + size * self.HEAD_RATIO * 0.7)
```

`_offset` 是通用工具：从某点沿某方向偏移一定距离：

```python
def _offset(self, origin, direction, distance, direction2=None, distance2=0.0):
    x = origin[0] + direction[0] * distance
    y = origin[1] + direction[1] * distance
    if direction2 is not None:      # 可选叠加第二个方向
        x += direction2[0] * distance2
        y += direction2[1] * distance2
    return (x, y)
```

从身体中心 `(x,y)` 出发：沿 `forward` 偏移一段 = 头部；沿 `backward` 偏移 = 腹部。

#### 4.4.4 身体轮廓 —— 用 18 个采样点画"饱满椭圆"

`_compute_body_outline` 是几何最复杂的地方。思路：**沿身体中轴（头→尾）取 18 个点，每个点根据位置算一个"半宽度"，左右对称连成封闭多边形**。

```python
def half_width(t):     # t 是 0(头部) 到 1(尾部) 的参数
    if t < 0.08:
        # 头部前端：尖圆
        local = t / 0.08
        return head_radius * 0.50 * local
    elif t < 0.22:
        # 颈部：明显收细
        ...
    elif t < 0.35:
        # 前胸背板：迅速放宽
        ...
    elif t < 0.45:
        # 胸腹交界
        ...
    elif t < 0.58:
        # 腹部前端：放宽到最大
        ...
    elif t < 0.90:
        # 腹部主体：向后收细
        ...
    else:
        # 腹部末端：尖圆收尾
        ...
```

这个函数定义了**蟑螂从尖头→细颈→宽胸→宽腹→窄尾**的完整轮廓。注意它大量使用 `math.sin(local * math.pi * 0.5)` 做**平滑插值**（从 0 平滑过渡到 1），避免生硬的折角。

然后对称地生成左右两排点：

```python
# 左侧轮廓（从头到尾）
for i in range(n_segments + 1):
    t = i / n_segments
    points.append((center[0] + left[0] * w, center[1] + left[1] * w))

# 右侧轮廓（从尾到头）
for i in range(n_segments, -1, -1):
    ...
```

最后渲染器拿到这 36 个点画一个 `smooth=True` 的多边形，就是那个饱满的椭圆形身体。

#### 4.4.5 触角 —— 分段 + 波动 + 鞭子效应

触角是 14 节线段，每节从基部到尖端逐段生长，方向受几种因素叠加：

```python
for i in range(n_segments):
    t = i / n_segments
    wave1 = math.sin(phase + t * 3.5) * 0.18      # 基础传播波
    wave2 = math.sin(phase * 1.4 + t * 2.2 + 0.7) * 0.12  # 第二谐波
    tip_amp = 0.3 + t * t * 0.9                   # 鞭子效应：越靠近尖端摆幅越大
    wave = (wave1 + wave2) * tip_amp * activity   # 叠加
    wave += random.uniform(-0.025, 0.025)         # 每节随机扰动
    speed_drag = -activity * t * 0.22             # 速度感应后飘（空气阻力感）
    ...
    next_pt = (current[0] + math.cos(seg_angle) * segment_length,
               current[1] + math.sin(seg_angle) * segment_length)
```

- **双谐波叠加**：两个不同频率的正弦波叠加 → 运动更"不规律"、更自然；
- **鞭子效应**：`tip_amp` 随 `t²` 增大，根部摆幅小、尖端大，像甩鞭子/面条；
- **随机扰动**：每节加一点随机，模拟颤动；
- **后飘**：活跃度高时触角尖端向后偏，模拟"跑太快触角被风吹到后面"。

#### 4.4.6 六条腿 —— 打破对称的"伪随机步态"

这是"生物感"最浓的地方。先看每条腿的初始化随机参数：

```python
# 每条腿独立的基础相位偏移、频率系数、振幅系数
self._leg_base_phase_offset = [random.uniform(-0.65, 0.65) for _ in range(6)]
self._leg_freq_noise = [random.uniform(0.78, 1.22) for _ in range(6)]
self._leg_amp_noise = [random.uniform(0.70, 1.35) for _ in range(6)]
```

**6 条腿的摆动频率、振幅、相位都略有不同**——如果完全一样，六条腿会像机器人一样同步摆动，非常假。这里故意打乱，模拟真实昆虫"近似但不规则"的步态。

腿部摆动核心：

```python
base_swing = math.sin(effective_phase)     # 基础摆动
irregular_swing = (
    0.18 * math.sin(effective_phase * 2.7 + noise_phase) +
    0.08 * math.sin(effective_phase * 4.1 + noise_phase * 1.3)
)
swing = (base_swing + irregular_swing) * amp_jitter
```

又见**多谐波叠加**：基础正弦波 + 2.7 倍频 + 4.1 倍频的叠加，让腿的摆动细碎、快速、不规律。

转向调制也很精彩：

```python
is_outer = (sign == turn_sign)     # 转弯方向外侧的腿
if is_outer:
    turn_amp_boost = 1.0 + turn_magnitude * 0.90   # 外侧腿摆幅加大（主要推进）
else:
    turn_amp_boost = 1.0 - turn_magnitude * 0.40   # 内侧腿摆幅减小（作支点）
```

转弯时**外侧腿用力蹬、内侧腿当支点**——这是真实生物的转弯姿态！

#### 4.4.7 惊吓反应 —— 身体膨胀 + 翅膀展开 + 后翅颤动

```python
if is_scared:
    body_scale = 1.08 + math.sin(self._abdomen_wave * 3) * 0.03   # 身体微微膨胀+抖动

# 翅膀颤动（惊吓时快速颤动）
self._wing_flutter_target = 1.0 if is_scared else 0.0
flutter_speed = 15.0 if is_scared else 5.0
self._wing_flutter_current += (self._wing_flutter_target - self._wing_flutter_current) * flutter_speed * dt
```

被吓时：身体膨胀到 1.08 倍并轻微抖动、后翅展开 45~70°、快速颤动。又是"平滑趋近"的套路（`当前值 += (目标-当前)×速度×dt`）。

#### 4.4.8 腿部三对足的角度

```python
if pair_index == 0:    # 前足：向前外侧约 35°
    base_angle = body_angle + sign * math.pi / 5.1
elif pair_index == 1:  # 中足：向后外侧约 80°
    base_angle = body_angle + sign * math.pi / 2.25
else:                  # 后足：明显向后约 130°
    base_angle = body_angle + sign * math.pi / 1.38
```

$\pi/5.1 \approx 35°$，$\pi/2.25 \approx 80°$，$\pi/1.38 \approx 130°$。注意注释里专门提到"中足向后 80°，避免正侧向的螃蟹感"——**作者在调参数时明显观察过真实蟑螂 vs 螃蟹的区别**。

#### 4.4.9 输出：`CockroachRenderData`

```python
@dataclass
class CockroachRenderData:
    x: float                      # 身体中心 X
    y: float                      # 身体中心 Y
    angle: float                  # 身体朝向
    head: tuple                   # 头部中心
    thorax: tuple                 # 胸部中心
    abdomen: tuple                # 腹部中心
    body_outline: list            # 身体轮廓多边形
    head_radius: float
    body_size: float
    eye_left: tuple; eye_right: tuple
    antenna_left: AntennaData; antenna_right: AntennaData
    legs: list                    # 六条腿
    tegmen_left/right: WingData   # 鞘翅
    hindwing_left/right: WingData # 后翅
    cercus_left/right: tuple      # 尾须
    legs_phase: float; antenna_phase: float
    body_scale: float; abdomen_wave: float
    is_scared: bool; wing_flutter: float
    wrap_screen: bool = False
```

**这个 dataclass 是"模型层"和"渲染层"的契约**。模型层负责把这一切填满，渲染层只负责读。两边通过这个"数据盒子"解耦。

---

### 4.5 renderer.py —— 画布绘制

**一句话**：把 `CockroachRenderData` 里的坐标变成 tkinter Canvas 上的图形。**它只负责"画"，完全不关心蟑螂为什么动。**

#### 4.5.1 主入口 `render()`

```python
def render(self, data, screen_w, screen_h):
    self.canvas.delete("all")        # 清空上一帧的所有图形
    self.draw_cockroach(data)        # 画本体
    # 屏幕环绕时，画幽灵副本
    if getattr(data, "wrap_screen", False):
        for dx, dy in self._get_wrap_offsets(data, screen_w, screen_h):
            ghost = self._translate_render_data(data, dx, dy)
            self.draw_cockroach(ghost)
```

每帧先 `delete("all")` 清空再重画——这是 Canvas 动画的标准做法（简单但有效）。

**幽灵副本**：环绕模式下，蟑螂在屏幕边缘时，在对面画一个"复制品"，看起来它是穿过去到另一边了。

#### 4.5.2 `draw_cockroach()` —— 绘制顺序有讲究

```python
def draw_cockroach(self, data):
    # 1. 后翅（最底层）
    if data.hindwing_left.span_angle > 0.1:
        self._draw_hindwing(...)
    # 2. 腿部
    for leg in data.legs:
        self._draw_leg_realistic(leg)
    # 3. 身体底色
    self.canvas.create_polygon(outline, fill=..., smooth=True)
    # 4. 鞘翅（盖在身体上）
    self._draw_tegmen_realistic(...)
    # 5. 翅缝
    self._draw_suture(...)
    # 6. 头部（先画，被前胸背板部分遮盖）
    self._draw_head_realistic(...)
    # 7. 前胸背板（盖在头部后面）
    self._draw_pronotum_realistic(...)
    # 8. 触角
    self._draw_antenna_realistic(...)
    # 9. 尾须
```

**绘制顺序 = 遮挡关系**。Canvas 后画的盖在先画的上面。所以：后翅最底 → 身体 → 鞘翅 → 头 → 前胸背板（遮住部分头）→ 触角最上。

#### 4.5.3 核心绘图 API（tkinter Canvas 基础）

这个文件用到的 Canvas 方法，其实就是 tkinter 的 4 个基础图形：

```python
canvas.create_polygon(points, fill=..., outline=..., smooth=True)  # 多边形（smooth=圆滑）
canvas.create_oval(x1, y1, x2, y2, fill=...)                       # 椭圆（对角坐标）
canvas.create_line(points, fill=..., width=..., smooth=True)       # 折线/曲线
```

注意 `create_oval` 传的是**对角两点** `(左上x, 左上y, 右下x, 右下y)`，不是中心和半径。所以代码里有辅助函数：

```python
def _draw_ellipse(self, x, y, rx, ry, fill, outline="", width=1):
    self.canvas.create_oval(
        x - rx, y - ry, x + rx, y + ry,   # 从中心减半轴 到 中心加半轴
        fill=fill, outline=outline, width=width
    )
```

#### 4.5.4 腿的画法 —— 锥形分段 + 刚毛

```python
def _draw_leg_realistic(self, leg):
    # 三段：基节→腿节→胫节→跗节，每段从粗到细
    self._draw_tapered_segment(coxa, femur, 4.0, 2.8, color_leg)
    self._draw_tapered_segment(femur, tibia, 2.8, 2.0, color_leg_mid)
    self._draw_tapered_segment(tibia, tarsus, 2.0, 1.3, color_leg_dark)
    # 刚毛
    self._draw_leg_spines(coxa, femur, color_spine, count=8, length=3.5)
    ...
```

`_draw_tapered_segment` 画"一端粗一端细"的腿段——用**法向量**（垂直于线段方向的单位向量）构造梯形：

```python
ux, uy = dx / length, dy / length   # 线段方向单位向量
nx, ny = -uy, ux                    # 法向量（垂直）
points = [
    (p1.x + nx*hw1, p1.y + ny*hw1),  # 起点粗的一侧
    (p1.x - nx*hw1, p1.y - ny*hw1),  # 起点粗的另一侧
    (p2.x - nx*hw2, p2.y - ny*hw2),  # 终点细的一侧
    (p2.x + nx*hw2, p2.y + ny*hw2),  # 终点细的另一侧
]
```

这是 2D 图形学基础操作：**已知线段两端点，用单位方向向量和法向量，就能构造"沿线段的任意宽度多边形"**。刚毛则是沿线段每隔一段距离画一条向外的小短线。

#### 4.5.5 鞘翅 —— 参数化椭圆弧

```python
a = length * 0.5    # 椭圆长半轴
b = half_w          # 椭圆短半轴
for i in range(n_arc, -1, -1):
    t = math.pi * i / n_arc        # π → 0
    arc_x = cx + a*math.cos(t)*ux + sign*b*math.sin(t)*px   # 椭圆参数方程
    arc_y = cy + a*math.cos(t)*uy + sign*b*math.sin(t)*py
```

椭圆的参数方程是 $(x,y) = (cx + a\cos t, cy + b\sin t)$，这里再叠加方向向量 `(ux,uy)`（椭圆长轴方向）和 `(px,py)`（短轴方向），让椭圆能**任意旋转朝向**。`t` 从 π 到 0 只走半圈 → 半椭圆。

#### 4.5.6 幽灵副本 —— 递归平移整个数据盒子

最巧的部分是 `_translate_render_data`：**怎么把整个 `CockroachRenderData` 里所有坐标都平移 (dx, dy)？**

```python
@staticmethod
def _translate_render_data(data, dx, dy):
    def _translate(obj):
        if is_dataclass(obj):                    # 是数据盒子 → 遍历每个字段递归
            changes = {}
            for f in fields(obj):
                changes[f.name] = _translate(getattr(obj, f.name))
            return replace(obj, **changes)       # 生成新实例
        if isinstance(obj, tuple):
            if len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj):
                return (obj[0] + dx, obj[1] + dy)   # 二维数值元组 = 坐标 → 平移
            return tuple(_translate(v) for v in obj)
        if isinstance(obj, list):
            return [_translate(v) for v in obj]
        return obj                                # 标量/字符串 → 原样返回
    return _translate(data)
```

用 `is_dataclass` 判断是不是数据盒子，用 `fields()` 拿到所有字段名，用 `replace()` 生成新实例。**递归**地：遇到 dataclass 就钻进去、遇到二维数值元组就平移、遇到别的就原样返回。

这个函数是"通用工具"——不管数据结构多复杂（嵌套 dataclass、列表套列表），都能完整平移。**递归 + 类型判断（isinstance/is_dataclass）是处理嵌套数据的经典手法**。

---

### 4.6 pet.py —— 顶层门面

**一句话**：`CockroachPet` 是"总经理"，把所有模块装起来，对外只暴露简单的接口。前端（main.py / settings_ui.py）不用知道内部细节，只管调 `update()`。

#### 4.6.1 `__init__` —— 组装所有模块

```python
def __init__(self, config_dir: str = None):
    self.config = ConfigManager(config_dir)          # 配置
    cfg = self.config.get_all()

    self.physics = PhysicsEngine(                     # 物理
        damping=cfg.get("damping", 0.93),
        max_speed=cfg.get("speed_max", 300),
    )
    self.behavior = BehaviorEngine(cfg)               # 行为
    self.model = CockroachModel(body_size=cfg.get("body_size", 40))  # 模型
    self.autostart = AutostartManager("CockroachPet") # 开机自启

    # 拖动状态
    self._is_grabbed = False
    self._grab_offset_x = 0.0
    ...
    self._init_start_position()        # 初始位置
    self._apply_autostart_setting()    # 应用自启设置
```

**"门面模式"（Facade Pattern）**：把所有子系统藏在一个类后面，调用者只需要一个对象。好处：前端代码极简、各子系统互不干扰。

#### 4.6.2 `update()` —— 一帧的完整编排（重点！）

这是整个项目**最重要的方法**，把前面所有模块串起来：

```python
def update(self, dt, mouse_x, mouse_y, mouse_pressed, mouse_on_pet,
           screen_width, screen_height) -> CockroachRenderData:
    self._screen_width = screen_width
    self._screen_height = screen_height

    # 首帧初始化上一帧鼠标位置，避免速度爆炸
    if self._prev_mouse_x == 0.0 and self._prev_mouse_y == 0.0:
        self._prev_mouse_x = mouse_x
        self._prev_mouse_y = mouse_y

    # 更新鼠标速度（指数平滑）
    if dt > 0:
        dx = mouse_x - self._prev_mouse_x
        dy = mouse_y - self._prev_mouse_y
        raw_speed = math.sqrt(dx*dx + dy*dy) / dt
        self._mouse_velocity = self._mouse_velocity * 0.6 + raw_speed * 0.4
    self._prev_mouse_x = mouse_x
    self._prev_mouse_y = mouse_y

    # 拖动逻辑
    self._update_grab(dt, mouse_x, mouse_y, mouse_pressed, mouse_on_pet)

    pos = self.physics.body.position

    if self._is_grabbed:
        # 被抓：直接设位置（跟着鼠标走）
        target_x = mouse_x - self._grab_offset_x
        target_y = mouse_y - self._grab_offset_y
        self.physics.set_position(target_x, target_y)
        force = (0, 0)
        behavior_state = BehaviorState.GRABBED
        is_scared = False
    else:
        # 行为决策 → 力
        roach_angle = self.physics.get_direction()
        behavior_state, (force_x, force_y), is_scared = self.behavior.update(...)
        self.physics.add_force(force_x, force_y)   # 力喂给物理
        self.physics.set_scared(is_scared)         # 惊吓状态告诉物理（转弯更锐）

    # 物理推进
    self.physics.update(dt, (0, 0, screen_width, screen_height), wrap=wrap_screen)

    # 读物理结果
    new_pos = self.physics.body.position
    speed = self.physics.get_speed()
    direction = self.physics.get_direction()
    turn_rate = self.physics.get_angular_velocity()

    # 模型计算渲染坐标
    is_observing = (not self._is_grabbed) and behavior_state == BehaviorState.OBSERVE
    render_data = self.model.compute(
        x=new_pos.x, y=new_pos.y, angle=direction,
        speed=speed, dt=dt, is_scared=is_scared,
        turn_rate=turn_rate, is_observing=is_observing,
    )
    render_data.wrap_screen = wrap_screen
    if self._is_grabbed:
        render_data.is_scared = False
    return render_data
```

**一帧的顺序（背下来！）**：

1. 算鼠标速度
2. 处理拖动（抓/放）
3. 若是被抓 → 直接设位置；否则 → 行为引擎给力
4. 物理引擎推进（转弯模型积分）
5. 模型层算渲染坐标
6. 返回 `CockroachRenderData`

注意**状态传递链**：`behavior 判断惊吓 → 告诉 physics set_scared → 物理用更快的转弯参数 → 转弯速率传给 model → 腿的转向调制`。一个状态层层传递影响，这就是分层架构的优雅协作。

#### 4.6.3 `_update_grab` —— 抓取状态机

```python
GRAB_HOLD_TIME = 0.35   # 长按阈值（秒）
GRAB_MAX_SPEED = 400    # 拖动触发最大鼠标速度

# 鼠标按下计时
if mouse_pressed and not self._mouse_was_pressed:
    self._mouse_press_timer = 0.0
if mouse_pressed:
    self._mouse_press_timer += dt
else:
    self._mouse_press_timer = 0.0

# 开始拖动：按住 + 点在蟑螂上 + 没在抓 + 超过0.35s + 鼠标速度不快
if (mouse_pressed and mouse_on_pet and not self._is_grabbed
        and self._mouse_press_timer >= GRAB_HOLD_TIME
        and self._mouse_velocity < GRAB_MAX_SPEED):
    self._is_grabbed = True
    pos = self.physics.body.position
    self._grab_offset_x = mouse_x - pos.x   # 记录"鼠标-蟑螂"偏移
    self._grab_offset_y = mouse_y - pos.y
```

**抓取条件设计得很讲究**：

- 长按 0.35 秒（防止误触）；
- 鼠标要在蟑螂身上；
- **鼠标速度不能太快**（快速甩过去会触发惊吓而不是抓取，这是"长按慢移才能抓"的体验设计）。

`_grab_offset` 记录鼠标和蟑螂中心的偏移，这样抓起后蟑螂不会"跳"到鼠标正下方，而是保持在鼠标旁边原来相对的位置（体验更自然）。

#### 4.6.4 `release()` —— 甩出去

```python
def release(self, fling_velocity_x=0.0, fling_velocity_y=0.0):
    self._is_grabbed = False
    if fling_velocity_x != 0.0 or fling_velocity_y != 0.0:
        self.physics.set_velocity(fling_velocity_x, fling_velocity_y)  # 给初速度
    ...
    self.behavior.suppress_scare(1.5)   # 抑制惊吓误触
    self._mouse_velocity = 0.0
```

甩出速度在 `main.py` 里算好（基于鼠标速度 × 0.3 和一个方向角）：

```python
fling_vx = self._mouse_speed * 0.3 * math.cos(self._get_fling_angle())
fling_vy = self._mouse_speed * 0.3 * math.sin(self._get_fling_angle())
self.pet.release(fling_velocity_x=fling_vx, fling_velocity_y=fling_vy)
```

`_get_fling_angle` 用最近两帧鼠标位移求甩出方向：

```python
def _get_fling_angle(self):
    dx = self._mouse_x - self._last_mouse_x
    dy = self._mouse_y - self._last_mouse_y
    return math.atan2(dy, dx)     # 鼠标移动方向
```

#### 4.6.5 `apply_config` —— 改配置即时生效

```python
_BEHAVIOR_KEYS = ("wander_strength", "attract_distance", ...)   # 行为相关键

def apply_config(self, key, value) -> bool:
    if not self.config.set(key, value):
        return False
    cfg = self.config.get_all()
    if key == "body_size":
        self.model.update_size(value)
    elif key in ("speed_max", "damping"):
        self.physics.update_config(damping=cfg.get("damping"), max_speed=cfg.get("speed_max"))
    elif key == "autostart":
        self.autostart.set_enabled(value)
    elif key in self._BEHAVIOR_KEYS:
        self.behavior.update_config(cfg)
    return True
```

**不同的配置键，要应用到不同的子模块**：`body_size` 改模型、`speed_max` 改物理、行为参数改行为引擎。这是一个"路由表"——根据键名分发到对应模块。

`set_config` = `apply_config` + 立即保存文件（低频场景用）；设置界面用 `apply_config` + 防抖保存（高频拖动场景用）。两种策略分工明确。

---

### 4.7 main.py —— 入口与窗口

**一句话**：程序入口。创建透明全屏窗口、绑定事件、跑主循环、管系统托盘。

#### 4.7.1 透明全屏窗口 —— 桌宠的实现原理

```python
self.master.overrideredirect(True)      # 去掉窗口边框和标题栏
self.master.attributes("-topmost", True)  # 置顶

self.transparent_color = "#ff00ff"      # 洋红色
self.master.attributes("-transparentcolor", self.transparent_color)  # 把洋红设为透明
```

**原理**：窗口是全屏的、铺满整个桌面，背景是洋红色 `#ff00ff`，然后告诉 Windows"这种颜色=透明"。于是整个窗口不可见，但上面画的蟑螂（不是洋红色的图形）可见。这是 Windows 上 tkinter 做透明桌宠的标准技巧。

#### 4.7.2 初始定位到屏幕中心

```python
def _resize_to_desktop(self):
    screen_w = self.master.winfo_screenwidth()   # 屏幕宽
    screen_h = self.master.winfo_screenheight()  # 屏幕高
    self.master.geometry(f"{screen_w}x{screen_h}+0+0")
    self.pet.physics.set_position(screen_w * 0.5, screen_h * 0.5)
    self.pet.behavior.reset()
```

`winfo_screenwidth()` 拿到主显示器分辨率，`geometry("宽x高+左+上")` 设置窗口大小和位置。

#### 4.7.3 事件绑定

```python
self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)   # 左键按下
self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)   # 左键释放
self.canvas.bind("<Button-3>", self._on_right_click)       # 右键
self.master.bind("<KeyPress-q>", lambda e: self._quit())   # 按 Q 退出
self.master.bind("<KeyPress-Escape>", lambda e: self._quit())  # Esc 退出
```

tkinter 事件绑定：`bind("<事件>", 回调)`。回调收到一个 `event` 对象（含坐标等）。

#### 4.7.4 命中检测 `_hit_test`

```python
def _hit_test(self, x, y):
    cx, cy = self.pet.get_position()
    size = self.pet.get_config("body_size") * 1.2   # 体型半径（放大1.2倍好点）
    dx = x - cx
    dy = y - cy
    return dx*dx + dy*dy <= size*size    # 距离平方 ≤ 半径平方
```

简化版碰撞检测：把蟑螂当成一个圆（中心 + 半径），判断鼠标是否在圆内。用平方比较避免开方（性能优化）。

#### 4.7.5 右键菜单

```python
self.context_menu = Menu(self.master, tearoff=0)
self.context_menu.add_command(label="设置", command=self._open_settings)
self.context_menu.add_separator()
self.context_menu.add_command(label="重置位置", command=self._reset_position)
self.context_menu.add_separator()
self.context_menu.add_command(label="退出 (Q/Esc)", command=self._quit)
```

`Menu` + `add_command` 是 tkinter 菜单的标准用法。

#### 4.7.6 系统托盘 —— pystray + 多线程

```python
tray_icon = Icon(
    "CockroachPet",
    _create_tray_icon_image(),        # PIL 生成的图标
    "蟑螂宠物（左键显示/隐藏）",
    menu=Menu(
        MenuItem("显示/隐藏蟑螂", _on_toggle, default=True),
        MenuItem("设置", _on_settings),
        Menu.SEPARATOR,
        MenuItem("退出", _on_quit),
    ),
)

tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
tray_thread.start()

root.mainloop()
```

**为什么要多线程？** 因为 `tray_icon.run()` 会**阻塞**（内部自己有个循环），而 `root.mainloop()` 也阻塞。两个阻塞循环不能都在主线程，所以托盘跑在子线程：

```python
tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
```

`daemon=True` 表示"主程序退出时这个线程自动结束"，避免残留。

**tkinter 线程安全陷阱**：托盘菜单的回调在子线程执行，不能直接操作 tkinter 控件。所以用 `root.after(0, func)` 把操作**调度回主线程**执行：

```python
def _on_toggle(icon, item):
    root.after(0, _toggle_visibility)   # 排队到主线程
```

这是 tkinter 多线程编程的铁律：**所有 UI 操作必须在主线程**。

#### 4.7.7 PIL 画托盘图标

```python
def _create_tray_icon_image():
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))   # 透明底
    d = ImageDraw.Draw(img)
    d.ellipse([16, 22, 48, 44], fill="#6B3A25", ...)      # 身体
    d.line([(25, 25), (16, 8)], fill="#8B4513", width=2)  # 触角
    ...
    return img
```

PIL 的 `ImageDraw` 提供和 Canvas 类似的绘图 API（ellipse、line 等），用来生成托盘小图标。注意这段 import 放在函数内部（**延迟导入**）——只有创建图标时才需要 PIL，避免启动时加载慢。

---

### 4.8 settings_ui.py —— 设置界面

**一句话**：设置窗口，左边实时预览，右边根据 SCHEMA 自动生成滑块/复选框，改参数实时生效并防抖保存。

#### 4.8.1 两种使用方式

看文件头注释：

```python
"""
电子桌宠蟑螂 - 独立设置界面（可单独打包为 exe）
...
与 main.py 的关系：两者是完全独立的进程，只通过 config.json 通信。
"""
```

这个文件**既能嵌进主进程（Toplevel），也能独立运行**：

- 在 `main.py` 里作为 Toplevel 嵌入（同进程，共享 `target_pet` 实例）；
- 也可以 `python settings_ui.py` 独立跑（独立进程，靠 config.json 通信）。

`SettingsWindow` 接受 `target_pet` 参数——传入桌宠本体实例，修改就能**直接作用到桌面上的蟑螂**：

```python
def __init__(self, master, target_pet: CockroachPet):
    self.target_pet = target_pet      # 桌宠本体（修改即时生效）
    self.pet = CockroachPet()         # 独立的预览实例（只用来预览动画）
```

#### 4.8.2 预览区

```python
self.preview_canvas = Canvas(left, width=380, height=380, bg="#d8d0c0", ...)
self.renderer = CockroachRenderer(self.preview_canvas)
```

预览也用同一个 `CockroachRenderer`（**渲染器复用**，保证预览和桌面效果完全一致）。预览的帧循环：

```python
def _update_preview(self):
    render_data = self.pet.update(
        dt=self.DT,
        mouse_x=-9999.0, mouse_y=-9999.0,   # 鼠标放到超远处 → 纯漫游
        mouse_pressed=False, mouse_on_pet=False,
        screen_width=self.PREVIEW_W, screen_height=self.PREVIEW_H,
    )
    render_data.wrap_screen = False          # 预览不画幽灵副本
    self.renderer.render(render_data, self.PREVIEW_W, self.PREVIEW_H)
    self.master.after(int(self.DT * 1000), self._update_preview)
```

**把鼠标坐标设为 -9999** 这个技巧很妙：鼠标在"超级远的地方"，蟑螂永远处于漫游状态，预览就展示自由爬行。

#### 4.8.3 按 SCHEMA 自动生成控件

```python
schema = ConfigManager.get_schema()
groups = {}
for key, meta in schema.items():
    groups.setdefault(meta.get("group", "其他"), []).append((key, meta))

for group_name, items in groups.items():
    lf = LabelFrame(inner, text=group_name, ...)
    for key, meta in items:
        self._build_one_control(lf, key, meta)
```

遍历 SCHEMA，按 `group` 分组，每组一个 `LabelFrame`，每个配置项生成一个控件。`_build_one_control` 根据 `meta["type"]` 决定：

```python
if ctype == "slider":
    scale = Scale(parent, from_=meta["min"], to=meta["max"],
                  resolution=meta.get("step", 1), orient=tk.HORIZONTAL,
                  command=lambda v, k=key: self._on_slider_change(k, v), ...)
elif ctype == "checkbox":
    var = BooleanVar(value=self.pet.get_config(key))
    Checkbutton(parent, text=label, variable=var,
                command=lambda k=key, v=var: self._on_check_change(k, v.get()), ...)
```

注意 `lambda v, k=key: ...` —— **默认参数捕获 key**。这是 Python 经典陷阱的解法：如果不 `k=key`，lambda 里的 `key` 会在循环结束后统一变成最后一个值（闭包延迟绑定）。`k=key` 把当前值"钉死"。

#### 4.8.4 防抖保存（Debounce）

```python
SAVE_DEBOUNCE_MS = 500   # 500ms

def _apply_and_schedule_save(self, key, value):
    self.pet.apply_config(key, value)          # 预览实例立即生效
    self.target_pet.apply_config(key, value)   # 桌宠本体立即生效
    self._status_label.config(text="修改中…", fg="#c87000")
    if self._save_after_id is not None:
        self.master.after_cancel(self._save_after_id)   # 取消上一次的保存任务
    self._save_after_id = self.master.after(self.SAVE_DEBOUNCE_MS, self._save_to_file)
```

**防抖**：拖动滑块时 `_on_slider_change` 会被疯狂调用（每秒几十次）。如果每次都写文件，磁盘受不了。所以：

- 每次修改先"取消"上一次安排的保存任务；
- 安排一个 500ms 后执行的保存任务；
- **只有停下来 500ms 不再拖动，才真正写文件**。

这是 UI 编程里非常经典的技术（防抖/节流）。

#### 4.8.5 滚动容器

```python
scroll_canvas = Canvas(right, highlightthickness=0)
scrollbar = tk.Scrollbar(right, orient=tk.VERTICAL, command=scroll_canvas.yview)
scroll_canvas.configure(yscrollcommand=scrollbar.set)
inner = Frame(scroll_canvas)
inner_id = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")
```

tkinter 做可滚动区域的标准模板：**Canvas 作为"视口"，在里面放一个 Frame（create_window），外面挂 Scrollbar**。内容超长时通过滚动条移动视口。这个模板建议背下来，以后做任何可滚动 UI 都用得上。

---

### 4.9 autostart.py —— 开机自启

**一句话**：把程序写进 Windows 注册表，实现开机自启。只用标准库 `winreg`。

#### 4.9.1 原理

Windows 开机自启有几种方式：

1. **启动文件夹**：放个 `.bat` 或快捷方式
2. **注册表 Run 键**：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 下加个字符串值

项目用了注册表方式，文件头注释解释了**为什么不用 .bat**（非常值得读）：

```python
"""
为什么不用启动文件夹的 .bat 脚本：
1. .bat 以 UTF-8 写入时，cmd.exe 在中文系统默认按 GBK 代码页解析，
   含中文的路径会被解析成乱码，导致 cd / start 失败；
2. 路径含空格/中文时 start 命令解析易出错；
3. PyInstaller 打包后 __file__ 指向 _MEIPASS 临时目录，cd /d 失效；
4. 启动文件夹中的 .bat 容易被杀软当作可疑启动脚本拦截。
注册表 Run 键是 Windows 标准自启机制，无上述问题，且当前用户注册表
无需管理员权限，仅依赖标准库 winreg。
"""
```

**这个注释本身就是极佳的学习材料**：它记录了"踩过的坑 + 为什么选择这个方案"，这就是工程思维。

#### 4.9.2 三个核心方法

**启用（写注册表）**：

```python
def enable(self) -> bool:
    command = self._get_target_command()   # 生成启动命令
    if command is None:
        return False
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self._RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
    self._cleanup_legacy_bat()
    return True
```

**禁用（删注册表）**：

```python
def disable(self) -> bool:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, self.app_name)
    ...
```

**查询状态**：

```python
def is_enabled(self) -> bool:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
        value, _ = winreg.QueryValueEx(key, self.app_name)
    ...
    current = self._get_target_command()
    return value == current    # 命令一致才算"已启用"
```

注意 `is_enabled` 不只是看"注册表里有没有"，还要**校验注册表里的命令和当前目标一致**（项目移动位置后旧条目失效，需重写）。这又是防御性设计的细节。

#### 4.9.3 路径解析 —— 兼容开发/打包两种场景

```python
def _get_target_command(self):
    # 情况1：打包后的 exe
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        return f'"{exe_path}"'
    # 情况2：开发环境，用 pythonw.exe 运行脚本
    pythonw_path = self._find_pythonw()
    if pythonw_path:
        return f'"{pythonw_path}" "{main_script}"'
    ...
```

`sys.frozen` 是 PyInstaller 打包后特有的标志。**同一个代码，开发环境和打包环境都能正确自启**——这是"一个代码两种环境"的经典处理。

---

## 第 5 章 一帧的生命周期（数据流全景）

把第 4 章全部串起来，模拟一帧 1/60 秒内发生的事：

```text
时间线（60 FPS，每 16.6ms 一帧）
│
├─ [main.py] _update() 被 after() 触发
│   ├─ 读全局鼠标位置 winfo_pointerx/y
│   ├─ 算鼠标速度（指数平滑）
│   ├─ 命中检测：鼠标在蟑螂身上吗？
│   ├─ 调用 pet.update(...)
│   │   ├─ [pet] 更新屏幕尺寸
│   │   ├─ [pet] 更新鼠标速度（自己也算一份）
│   │   ├─ [pet] _update_grab：按住超过0.35s且点在身上且鼠标不快 → 抓住
│   │   ├─ [pet] 是否被抓？
│   │   │   ├─ 是 → physics.set_position(跟鼠标走) → 状态=GRABBED
│   │   │   └─ 否 ↓
│   │   │       ├─ [behavior] update()：决定状态（漫游/观察/吸引/惊吓）
│   │   │       │    ├─ 计算鼠标速度、距离（含环形边界）
│   │   │       │    ├─ 计算前方120°权重
│   │   │       │    ├─ 判断状态（优先级：被抓>惊吓>吸引>观察>漫游）
│   │   │       │    └─ 按状态算力向量 (fx, fy)
│   │   │       ├─ [physics] add_force(fx, fy) → 拆成油门+目标朝向
│   │   │       └─ [physics] set_scared(惊吓?) → 惊吓则转弯参数加强
│   │   ├─ [physics] update(dt)：转弯积分 → 新位置/朝向/角速度
│   │   ├─ [model] compute(...)：
│   │   │    ├─ 更新动画相位（腿/触角/腹部）
│   │   │    ├─ 算头胸腹中心、身体轮廓、眼睛、触角、6腿、翅、尾须坐标
│   │   │    └─ 打包成 CockroachRenderData
│   │   └─ 返回 render_data
│   ├─ [main] _render(data) → [renderer] render()
│   │   ├─ canvas.delete("all") 清空
│   │   ├─ draw_cockroach(本体)（后翅→腿→身→鞘翅→头→前胸背板→触角→尾须）
│   │   └─ 环绕模式下画幽灵副本（递归平移数据）
│   └─ self.master.after(16, self._update)   ← 安排下一帧
│
└─ 16.6ms 后，再来一遍……
```

**整个项目 = 这帧循环以 60Hz 无限重复。**

---

## 第 6 章 动手实验：改着玩

> 学习的最好方式就是**改坏它、修好它**。下面每个实验都有明确的"改哪、看什么效果"。

### 实验 0：先跑起来

```bash
cd "c:\Users\12991\Desktop\XMU_Study\Self_Study\Programing\python\Apps\Small_Toys\ElectricalPet\ElectricalCockroach"
python src/main.py
```

> 如果报错 `ModuleNotFoundError: pystray`，先 `pip install pystray Pillow`。

### 实验 1：改参数，看反应（最简单）

打开 `config.json`，把 `body_size` 改成 `70`，保存。**不用重启**，等 1 秒蟑螂就变大了（热重载生效！）。

再试 `scare_speed_threshold` 改成 `300`（更容易吓到），`wander_strength` 改成 `500`（爬得更猛）。

> 📝 练习：把所有参数都改一遍，然后记录每个参数的实际效果。这会让你彻底理解"配置 → 行为"的映射。

### 实验 2：给蟑螂换颜色

打开 `renderer.py`，在 `draw_cockroach` 顶部有配色：

```python
color_body = "#6B3A25"        # 身体深红棕
color_pronotum = "#E8A650"    # 前胸背板浅橙
```

把 `color_body` 改成 `"#336699"`（蓝色）看看。再改成你喜欢的颜色。

> 📝 练习：把整只蟑螂改成"金色的"（body、leg、antenna 全部）。

### 实验 3：加一个新的行为状态

这是最进阶的实验，能检验你是否真懂状态机。

目标：加一个"吃饱了发呆"的状态。步骤：

1. 在 `behavior_engine.py` 的 `BehaviorState` 枚举里加 `SLEEP = auto()`
2. 在 `_determine_state` 里加一条转换规则（比如漫游时 5% 概率进入）
3. 在 `update()` 里加一个 `elif new_state == BehaviorState.SLEEP:` 分支，力设为 (0,0)
4. 在渲染端可以给睡眠状态加个"ZZZ"或变暗

### 实验 4：改触角长度

打开 `cockroach_model.py`，找到：

```python
ANTENNA_LENGTH_RATIO = 3.8
```

改成 `6.0`，蟑螂的触角会变得超长。改成 `1.0` 看它变得多短。

### 实验 5：写自己的小模块测试

每个核心文件末尾都有 `if __name__ == "__main__":` 测试代码。直接运行看看输出：

```bash
python physics_engine.py    # 物理引擎自测
python behavior_engine.py   # 行为引擎自测
python cockroach_model.py   # 模型自测
python config_manager.py    # 配置自测
```

> 建议：**自己写一个测试脚本**，import 这些模块，手动喂数据打印结果，观察状态转换。

### 实验 6：理解帧循环

在 `main.py` 的 `_update` 里加一行打印：

```python
def _update(self):
    if not self._running:
        return
    print("tick", self._mouse_speed)   # ← 加这行
```

运行后会疯狂打印（每秒 60 次），观察鼠标速度数值随鼠标移动的变化。看完删掉。

---

## 第 7 章 怎么打包成 exe

项目里有 `CockroachPet.spec`，是用 PyInstaller 打包的配置。重新打包：

```bash
pip install pyinstaller
pyinstaller CockroachPet.spec
```

打包产物在 `dist/` 目录。打包后的注意点（代码里都有处理）：

1. **资源路径**：打包后 `sys.frozen` 为 True，用 `sys._MEIPASS` 找资源（`main.py` / `settings_ui.py` 顶部都有兼容代码）；
2. **配置文件路径**：打包后 config 放在 `%APPDATA%/CockroachPet/`（`config_manager.py` 的 `_get_default_config_dir`）；
3. **开机自启**：打包后注册表里写 exe 路径（`autostart.py` 的 `_get_target_command` 处理了）。

> 关于 `.spec` 文件：它是 PyInstaller 的"构建配方"，记录了入口脚本、图标、隐藏导入等。如果你以后想打包，建议先看官方文档理解 spec 语法。

---

## 第 8 章 术语表

| 术语 | 含义 |
| --- | --- |
| **dt** | delta time，两帧之间的时间差（秒），物理计算都要乘它 |
| **FPS** | 帧率，每秒刷新的次数（本项目 60） |
| **状态机** | 一组互斥状态 + 转换条件，AI 决策的骨架 |
| **向量 (Vector)** | 有大小和方向的量，用 (x,y) 表示 |
| **单位向量** | 长度=1 的向量，`normalize()` 得到，用于表示"纯方向" |
| **点积 (dot)** | 两向量投影相关运算，可用于算夹角 |
| **阻尼 (damping)** | 速度衰减系数，每帧乘一次，模拟摩擦/空气阻力 |
| **死区 (dead zone)** | 某个阈值内不响应，避免微小扰动导致抖动 |
| **指数平滑** | `新 = 旧×a + 新×b`，让波动值变平滑 |
| **热重载** | 程序运行中检测外部文件变化并重新加载，无需重启 |
| **门面模式 (Facade)** | 用一个类封装一堆子系统，对外提供简单接口 |
| **dataclass** | 自动生成 `__init__` 等方法的"数据盒子"类 |
| **防抖 (Debounce)** | 高频触发时只在"停手后"执行一次，避免频繁操作 |
| **幽灵副本** | 环绕模式下画在屏幕对侧的复制品，实现视觉连续 |
| **坐标系** | 屏幕坐标系：原点左上、x 右、y 下；角度 0 朝右、顺时针为正 |
| **局部坐标系** | 相对物体自身的坐标系（forward/left/right），随物体旋转 |
| **单进程 vs 多进程** | 单进程=一个程序里多个窗口；多进程=多个独立程序靠文件通信 |

---

## 结语：这个项目教会你什么？

如果你完整读完了这份文档，你收获的不只是"看懂了一个蟑螂程序"，而是几个可迁移的**核心编程思想**：

1. **分层架构**：数据/物理/行为/模型/渲染各司其职，互相解耦——这是任何中大型项目的骨架。
2. **状态机**：复杂"智能"（AI）的本质是一堆状态 + 转换条件。游戏、机器人、协议解析都用它。
3. **游戏循环 + dt**：一切动画和模拟的核心骨架。
4. **向量与坐标变换**：图形学、物理模拟的地基。
5. **平滑/阻尼/死区/防抖**：让程序"手感好"的细节技术，全是调参的艺术。
6. **数据驱动 UI**：用 SCHEMA 描述配置，界面自动生成——加参数不改界面代码。
7. **工程细节**：类型校验、防御性编程、热重载、兼容开发/打包双环境、线程安全。

建议下一步：按第 6 章的实验从 1 做到 6，然后尝试**自己加一个新功能**（比如：双击蟑螂会跳一下、给蟑螂加个影子、让蟑螂睡觉时呼出"Zzz"文字……）。

祝你玩得开心，喵～ 🪳
