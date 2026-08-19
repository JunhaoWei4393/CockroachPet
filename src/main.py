"""
main.py
电子桌宠蟑螂 - 桌面 UI 入口（单进程 + 系统托盘）

使用 tkinter 实现全桌面覆盖的透明置顶窗口，集成 CockroachPet 门面类。
渲染采用 Canvas 绘制（CockroachRenderer），支持鼠标吸引、惊吓、长按抓取/甩出。
系统托盘图标控制蟑螂显示/隐藏、打开设置窗口、退出程序。
"""

import math
import os
import sys
import threading

# 兼容 PyInstaller 打包后的单文件 exe
# 打包后所有资源被解压到 sys._MEIPASS 临时目录，必须把它加入模块搜索路径，
# 本地模块（config_manager / physics_engine 等）才能被找到。
if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import tkinter as tk
from tkinter import Menu, Toplevel

from pet import CockroachPet
from renderer import CockroachRenderer
from settings_ui import SettingsWindow

__all__ = [
    "CockroachPet",
    "CockroachPetWindow",
    "main",
]


class CockroachPetWindow:
    """
    全桌面桌面宠物窗口

    特性：
    - 无边框、全桌面覆盖、置顶、透明背景（Windows 使用透明色实现）
    - 使用全局鼠标位置（winfo_pointerx/y）跟踪光标，即使鼠标不在蟑螂上也能触发吸引/惊吓
    - 鼠标慢速靠近 = 吸引；快速靠近 = 惊吓；长按 = 抓取拖动
    - 右键菜单可调整大小、速度、阻尼、惊吓阈值、退出
    - 定期检测 config.json 外部修改，实现与设置界面的并行联动

    Args:
        master: tkinter 根窗口
    """

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("CockroachPet")

        # 窗口属性：无边框、置顶
        self.master.overrideredirect(True)
        self.master.attributes("-topmost", True)

        # 透明背景：指定洋红色为透明色（Windows）
        self.transparent_color = "#ff00ff"
        self.master.attributes("-transparentcolor", self.transparent_color)

        # 核心宠物逻辑
        self.pet = CockroachPet()
        self.pet.get_all_config()

        # 渲染画布：全桌面尺寸
        self.canvas = tk.Canvas(
            master,
            bg=self.transparent_color,
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 渲染器：负责把 RenderData 绘制到 Canvas
        self.renderer = CockroachRenderer(self.canvas)

        # 等待窗口布局完成后再获取屏幕尺寸并调整宠物位置
        self.master.update_idletasks()
        self._resize_to_desktop()

        # 状态
        self._running = True
        self._mouse_x = 0
        self._mouse_y = 0
        self._last_mouse_x = 0
        self._last_mouse_y = 0
        self._mouse_speed = 0.0
        self._mouse_pressed = False
        self._screen_w = 1
        self._screen_h = 1

        # 动画帧率
        self._fps = 60
        self._dt = 1.0 / self._fps

        # 事件绑定
        self._bind_events()

        # 右键菜单
        self._build_context_menu()

        # 设置窗口引用（Toplevel，按需创建）
        self._settings_window = None

        # 开始循环
        self._update()

    # ==================== 窗口尺寸 ====================

    def _resize_to_desktop(self):
        """将窗口调整为覆盖整个主显示器"""
        # winfo_screenwidth/height 返回主显示器分辨率
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        self.master.geometry(f"{screen_w}x{screen_h}+0+0")
        # 初始位置放到屏幕中心
        self.pet.physics.set_position(screen_w * 0.5, screen_h * 0.5)
        self.pet.behavior.reset()

    # ==================== 事件绑定 ====================

    def _bind_events(self):
        """绑定鼠标、键盘事件"""
        # <Motion> 在全屏透明窗口上可能不会被透明区域触发，
        # 因此主循环中使用 winfo_pointerx/y 获取全局鼠标位置。
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.master.bind("<KeyPress-q>", lambda e: self._quit())
        self.master.bind("<KeyPress-Escape>", lambda e: self._quit())

    def _on_mouse_down(self, event: tk.Event):
        """鼠标按下：若点在蟑螂身上则进入抓取判定"""
        self._mouse_pressed = True

    def _on_mouse_up(self, event: tk.Event):
        """鼠标释放：结束抓取，可甩出"""
        if self.pet.is_grabbed:
            # 计算甩出速度
            fling_vx = self._mouse_speed * 0.3 * math.cos(self._get_fling_angle())
            fling_vy = self._mouse_speed * 0.3 * math.sin(self._get_fling_angle())
            self.pet.release(fling_velocity_x=fling_vx, fling_velocity_y=fling_vy)

        self._mouse_pressed = False

    def _get_fling_angle(self) -> float:
        """根据最近两帧鼠标位移计算甩出方向"""
        dx = self._mouse_x - self._last_mouse_x
        dy = self._mouse_y - self._last_mouse_y
        return math.atan2(dy, dx)

    def _on_right_click(self, event: tk.Event):
        """右键弹出菜单"""
        self.context_menu.post(event.x_root, event.y_root)

    # ==================== 碰撞检测 ====================

    def _hit_test(self, x: float, y: float) -> bool:
        """
        判断鼠标是否落在蟑螂身上

        采用中心距离 + 体型半径的简化包围圆。
        """
        cx, cy = self.pet.get_position()
        size = self.pet.get_config("body_size") * 1.2
        dx = x - cx
        dy = y - cy
        return dx * dx + dy * dy <= size * size

    # ==================== 右键菜单 ====================

    def _build_context_menu(self):
        """创建右键菜单"""
        self.context_menu = Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="设置", command=self._open_settings)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="重置位置", command=self._reset_position)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="退出 (Q/Esc)", command=self._quit)

    def _reset_position(self):
        """重置蟑螂到屏幕中心"""
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.pet.physics.set_position(w * 0.5, h * 0.5)
        self.pet.behavior.reset()

    def _quit(self):
        """退出程序"""
        self._running = False
        self.pet.shutdown()
        self.master.destroy()

    # ==================== 设置窗口（同进程 Toplevel） ====================

    def _open_settings(self):
        """
        打开设置窗口（Toplevel，与桌宠同进程）

        设置窗口内嵌预览，修改参数即时生效到桌面蟑螂。
        窗口关闭后桌宠继续运行。
        """
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        top = Toplevel(self.master)
        top.title("蟑螂宠物设置")
        # 创建设置窗口（传入桌宠本体实例，修改即时生效）
        SettingsWindow(top, self.pet)
        # 窗口关闭时清理引用
        top.protocol("WM_DELETE_WINDOW",
                     lambda: (self.__setattr__("_settings_window", None), top.destroy()))
        self._settings_window = top

    # ==================== 主循环 ====================

    def _update(self):
        """每帧更新：物理、行为、渲染"""
        if not self._running:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self._screen_w = w
        self._screen_h = h

        # 使用全局鼠标位置（即使光标在透明区域也能被追踪）
        # 窗口位于 (0,0)，所以屏幕坐标与 Canvas 坐标一致
        self._mouse_x = self.master.winfo_pointerx()
        self._mouse_y = self.master.winfo_pointery()

        # 鼠标速度（像素/秒）
        dx = self._mouse_x - self._last_mouse_x
        dy = self._mouse_y - self._last_mouse_y
        raw_speed = math.hypot(dx, dy) / self._dt
        self._mouse_speed = self._mouse_speed * 0.6 + raw_speed * 0.4
        self._last_mouse_x = self._mouse_x
        self._last_mouse_y = self._mouse_y

        # 判断鼠标是否在蟑螂身上
        mouse_on_pet = self._hit_test(self._mouse_x, self._mouse_y)

        # 更新宠物状态
        render_data = self.pet.update(
            dt=self._dt,
            mouse_x=self._mouse_x,
            mouse_y=self._mouse_y,
            mouse_pressed=self._mouse_pressed,
            mouse_on_pet=mouse_on_pet,
            screen_width=w,
            screen_height=h,
        )

        # 渲染
        self._render(render_data)

        self.master.after(int(self._dt * 1000), self._update)

    # ==================== 渲染 ====================

    def _render(self, data):
        """委托渲染器绘制蟑螂（支持屏幕环绕幽灵副本）"""
        self.renderer.render(data, self._screen_w, self._screen_h)


def _create_tray_icon_image():
    """
    用 PIL 生成蟑螂托盘图标

    绘制圆滑饱满的纺锤形身体、浅橙前胸背板、细长触角，
    与桌面蟑螂配色一致。
    """
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 身体（纺锤形椭圆，圆滑饱满）
    d.ellipse([16, 22, 48, 44], fill="#6B3A25", outline="#3D2216", width=2)
    # 前胸背板（浅橙盾形）
    d.ellipse([20, 24, 30, 32], fill="#E8A650", outline="#3D2618")
    # 中央深色圆盘
    d.ellipse([22, 26, 28, 30], fill="#3D2618")
    # 触角（细长丝状）
    d.line([(25, 25), (16, 8)], fill="#8B4513", width=2)
    d.line([(29, 25), (40, 8)], fill="#8B4513", width=2)
    # 腿（两侧各两条）
    d.line([(18, 32), (10, 28)], fill="#A0522D", width=2)
    d.line([(18, 38), (10, 42)], fill="#A0522D", width=2)
    d.line([(46, 32), (54, 28)], fill="#A0522D", width=2)
    d.line([(46, 38), (54, 42)], fill="#A0522D", width=2)
    # 尾须
    d.line([(48, 33), (56, 30)], fill="#8B5A3C", width=2)
    d.line([(48, 37), (56, 40)], fill="#8B5A3C", width=2)

    return img


def main():
    """
    程序入口：单进程，桌宠窗口 + 系统托盘图标

    托盘图标右键菜单：
    - 显示/隐藏蟑螂：切换桌宠窗口可见性
    - 设置：打开设置窗口（Toplevel，同进程，修改即时生效）
    - 退出：关闭程序

    托盘图标左键点击：等价于"显示/隐藏蟑螂"
    """
    from pystray import Icon, Menu, MenuItem

    root = tk.Tk()
    app = CockroachPetWindow(root)

    # 设置窗口引用（托盘和右键菜单共用）
    settings_state = {"top": None}

    def _toggle_visibility():
        """切换桌宠显示/隐藏"""
        if root.state() == "withdrawn":
            root.deiconify()
        else:
            root.withdraw()

    def _open_settings():
        """打开设置窗口（同进程 Toplevel）"""
        if settings_state["top"] is not None and settings_state["top"].winfo_exists():
            settings_state["top"].lift()
            settings_state["top"].focus_force()
            return
        top = Toplevel(root)
        SettingsWindow(top, app.pet)
        top.protocol(
            "WM_DELETE_WINDOW",
            lambda: (settings_state.__setitem__("top", None), top.destroy()),
        )
        settings_state["top"] = top

    def _quit_app():
        """退出程序"""
        tray_icon.stop()
        app._quit()

    # 托盘菜单回调在子线程执行，用 root.after 调度到主线程（tkinter 非线程安全）
    def _on_toggle(icon, item):
        root.after(0, _toggle_visibility)

    def _on_settings(icon, item):
        root.after(0, _open_settings)

    def _on_quit(icon, item):
        root.after(0, _quit_app)

    tray_icon = Icon(
        "CockroachPet",
        _create_tray_icon_image(),
        "蟑螂宠物（左键显示/隐藏）",
        menu=Menu(
            MenuItem("显示/隐藏蟑螂", _on_toggle, default=True),
            MenuItem("设置", _on_settings),
            Menu.SEPARATOR,
            MenuItem("退出", _on_quit),
        ),
    )

    # 托盘图标在子线程运行（icon.run 阻塞），tkinter mainloop 在主线程
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    root.mainloop()
    # mainloop 退出后清理托盘图标（无论是右键退出还是托盘退出）
    tray_icon.stop()


if __name__ == "__main__":
    main()
