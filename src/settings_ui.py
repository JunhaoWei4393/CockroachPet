"""
settings_ui.py
电子桌宠蟑螂 - 独立设置界面（可单独打包为 exe）

特性：
- 左侧实时预览蟑螂动画（独立 CockroachPet 实例，不影响正在运行的桌宠本体）
- 右侧基于 schema 自动生成的参数控件，按分组排列，可滚动
- 修改参数立即生效于预览，并通过防抖写入 config.json
- 桌宠本体进程检测到 config.json 变化后热重载，实现"修改即反馈、运行互不干扰"

与 main.py 的关系：两者是完全独立的进程，只通过 config.json 通信。
本程序可独立运行/打包，无需桌宠本体正在运行。
"""

import os
import sys

# 兼容 PyInstaller 打包后的单文件 exe
if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import tkinter as tk
from tkinter import LabelFrame, Scale, Checkbutton, BooleanVar, Button, Frame, Label, Canvas

from pet import CockroachPet
from renderer import CockroachRenderer
from config_manager import ConfigManager

__all__ = ["SettingsWindow", "SettingsApp", "main"]


class SettingsWindow:
    """
    设置窗口（作为 Toplevel 嵌入主进程）

    左侧实时预览（独立 CockroachPet 实例），右侧参数控件。
    修改参数同时应用到预览实例和桌宠本体实例，即时生效。

    Args:
        master: Toplevel 父窗口
        target_pet: 桌宠本体的 CockroachPet 实例，修改即时生效到桌面蟑螂
    """

    # 预览区尺寸
    PREVIEW_W = 380
    PREVIEW_H = 380
    # 防抖保存延迟（毫秒）：拖动滑块时避免频繁写文件
    SAVE_DEBOUNCE_MS = 500
    # 动画帧间隔
    DT = 1.0 / 60.0

    def __init__(self, master, target_pet: CockroachPet):
        self.master = master
        self.master.title("蟑螂宠物设置")
        self.master.geometry("780x540")
        self.master.resizable(False, False)

        # 桌宠本体实例（修改即时生效到桌面蟑螂）
        self.target_pet = target_pet
        # 预览用独立实例（动画预览，不影响桌面蟑螂）
        self.pet = CockroachPet()
        # 预览的渲染器
        self.renderer = None  # 在 _build_preview 中创建

        # 防抖保存计时器 ID
        self._save_after_id = None
        # 防止初次设置控件值时触发回调写入
        self._loading_controls = False
        # 控件引用，用于恢复默认后刷新显示值
        self._scales = {}
        self._check_vars = {}

        # 构建界面
        self._build_preview()
        self._build_controls()
        self._build_buttons()

        # 把预览蟑螂放到预览框中心
        self.pet.physics.set_position(self.PREVIEW_W * 0.5, self.PREVIEW_H * 0.5)
        self.pet.behavior.reset()

        # 开始预览动画
        self._update_preview()

    # ==================== 布局 ====================

    def _build_preview(self):
        """左侧预览区"""
        left = Frame(self.master, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH)

        Label(left, text="实时预览", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W)

        # 预览画布：浅色背景便于看清深色蟑螂
        self.preview_canvas = Canvas(
            left,
            width=self.PREVIEW_W,
            height=self.PREVIEW_H,
            bg="#d8d0c0",
            highlightthickness=1,
            highlightbackground="#888",
        )
        self.preview_canvas.pack(pady=(4, 0))

        # 渲染器绑定到预览画布
        self.renderer = CockroachRenderer(self.preview_canvas)

        # 状态提示
        self._status_label = Label(left, text="修改参数后自动保存", fg="#666")
        self._status_label.pack(anchor=tk.W, pady=(6, 0))

    def _build_controls(self):
        """右侧参数控件区（可滚动）"""
        right = Frame(self.master, padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 滚动容器：Canvas + Scrollbar + 内部 Frame
        scroll_canvas = Canvas(right, highlightthickness=0)
        scrollbar = tk.Scrollbar(right, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = Frame(scroll_canvas)
        inner_id = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")

        # 内部 Frame 大小变化时更新滚动区域
        def _on_inner_configure(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        inner.bind("<Configure>", _on_inner_configure)

        # 使内部 Frame 宽度跟随 Canvas，避免内容被挤压
        def _on_canvas_configure(event):
            scroll_canvas.itemconfig(inner_id, width=event.width)
        scroll_canvas.bind("<Configure>", _on_canvas_configure)

        # 鼠标滚轮滚动
        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind("<Enter>", lambda e: scroll_canvas.bind("<MouseWheel>", _on_mousewheel))
        scroll_canvas.bind("<Leave>", lambda e: scroll_canvas.unbind("<MouseWheel>"))

        # 按 schema 分组生成控件
        self._loading_controls = True
        schema = ConfigManager.get_schema()
        groups = {}
        for key, meta in schema.items():
            groups.setdefault(meta.get("group", "其他"), []).append((key, meta))

        for group_name, items in groups.items():
            lf = LabelFrame(inner, text=group_name, padx=8, pady=6)
            lf.pack(fill=tk.X, pady=(0, 8))
            for key, meta in items:
                self._build_one_control(lf, key, meta)

        self._loading_controls = False

    def _build_one_control(self, parent, key: str, meta: dict):
        """根据 schema 生成单个参数控件"""
        ctype = meta.get("type")
        label = meta.get("label", key)

        if ctype == "slider":
            Label(parent, text=label).pack(anchor=tk.W)
            scale = Scale(
                parent,
                from_=meta["min"],
                to=meta["max"],
                resolution=meta.get("step", 1),
                orient=tk.HORIZONTAL,
                command=lambda v, k=key: self._on_slider_change(k, v),
                length=280,
            )
            scale.set(self.pet.get_config(key))
            scale.pack(fill=tk.X, pady=(0, 6))
            self._scales[key] = scale
        elif ctype == "checkbox":
            var = BooleanVar(value=self.pet.get_config(key))
            Checkbutton(
                parent,
                text=label,
                variable=var,
                command=lambda k=key, v=var: self._on_check_change(k, v.get()),
            ).pack(anchor=tk.W, pady=(0, 6))
            self._check_vars[key] = var

    def _build_buttons(self):
        """底部按钮区"""
        bar = Frame(self.master, padx=10, pady=8)
        bar.pack(side=tk.BOTTOM, fill=tk.X)

        Button(bar, text="恢复默认", command=self._reset_default).pack(side=tk.LEFT, padx=(0, 8))
        Button(bar, text="保存并关闭", command=self._save_and_close).pack(side=tk.RIGHT)

    # ==================== 参数变更处理 ====================

    def _on_slider_change(self, key: str, value_str: str):
        """滑块变化：转换类型后应用到预览并防抖保存"""
        if self._loading_controls:
            return
        # 按默认值类型转换
        default = ConfigManager.DEFAULT_CONFIG[key]
        if isinstance(default, bool):
            value = value_str == "1"
        elif isinstance(default, int):
            value = int(float(value_str))
        else:
            value = float(value_str)
        self._apply_and_schedule_save(key, value)

    def _on_check_change(self, key: str, value: bool):
        """复选框变化"""
        if self._loading_controls:
            return
        self._apply_and_schedule_save(key, value)

    def _apply_and_schedule_save(self, key: str, value):
        """
        立即应用到预览实例和桌宠本体，并防抖写入 config.json

        同进程下直接 apply_config 到桌宠本体，桌面蟑螂即时响应；
        预览实例同步更新以反映效果；防抖保存避免拖动时频繁写文件。
        """
        self.pet.apply_config(key, value)
        self.target_pet.apply_config(key, value)
        self._status_label.config(text="修改中…", fg="#c87000")
        if self._save_after_id is not None:
            self.master.after_cancel(self._save_after_id)
        self._save_after_id = self.master.after(self.SAVE_DEBOUNCE_MS, self._save_to_file)

    def _save_to_file(self):
        """把当前配置写入 config.json"""
        self.target_pet.config.save()
        self._save_after_id = None
        self._status_label.config(text="已保存", fg="#2a7a2a")

    # ==================== 预览动画 ====================

    def _update_preview(self):
        """预览帧循环：让蟑螂在预览框内自由漫游"""
        # 鼠标放到预览框外，避免触发吸引/惊吓，展示纯漫游状态
        render_data = self.pet.update(
            dt=self.DT,
            mouse_x=-9999.0,
            mouse_y=-9999.0,
            mouse_pressed=False,
            mouse_on_pet=False,
            screen_width=self.PREVIEW_W,
            screen_height=self.PREVIEW_H,
        )
        # 预览框内不绘制幽灵副本（预览区域小，环绕副本会干扰观察）
        render_data.wrap_screen = False
        self.renderer.render(render_data, self.PREVIEW_W, self.PREVIEW_H)

        self.master.after(int(self.DT * 1000), self._update_preview)

    # ==================== 操作 ====================

    def _reset_default(self):
        """恢复默认配置，同步应用到预览和桌宠本体，刷新控件"""
        self.target_pet.config.reset_to_default()
        cfg = self.target_pet.config.get_all()
        # 应用到桌宠本体
        self.target_pet.physics.update_config(damping=cfg["damping"], max_speed=cfg["speed_max"])
        self.target_pet.behavior.update_config(cfg)
        self.target_pet.model.update_size(cfg["body_size"])
        # 同步预览实例
        self.pet.config.reset_to_default()
        self.pet.physics.update_config(damping=cfg["damping"], max_speed=cfg["speed_max"])
        self.pet.behavior.update_config(cfg)
        self.pet.model.update_size(cfg["body_size"])

        # 刷新控件显示值（暂停回调避免触发写入）
        self._loading_controls = True
        for key, scale in self._scales.items():
            scale.set(cfg[key])
        for key, var in self._check_vars.items():
            var.set(cfg[key])
        self._loading_controls = False

        self._save_to_file()

    def _save_and_close(self):
        """保存并关闭设置窗口（不影响桌宠本体运行）"""
        if self._save_after_id is not None:
            self.master.after_cancel(self._save_after_id)
        self.target_pet.config.save()
        self.master.destroy()


# 兼容别名
SettingsApp = SettingsWindow


def main():
    """独立测试入口（正常使用由 main.py 托盘菜单调用）"""
    root = tk.Tk()
    root.withdraw()
    pet = CockroachPet()
    top = tk.Toplevel(root)
    SettingsWindow(top, pet)
    top.protocol("WM_DELETE_WINDOW", lambda: (pet.shutdown(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
