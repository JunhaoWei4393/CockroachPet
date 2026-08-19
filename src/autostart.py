"""
autostart.py
Windows 开机自启管理模块
通过当前用户注册表 HKCU\\...\\Run 键实现开机自启

为什么不用启动文件夹的 .bat 脚本：
1. .bat 以 UTF-8 写入时，cmd.exe 在中文系统默认按 GBK 代码页解析，
   含中文的路径会被解析成乱码，导致 cd / start 失败；
2. 路径含空格/中文时 start 命令解析易出错；
3. PyInstaller 打包后 __file__ 指向 _MEIPASS 临时目录，cd /d 失效；
4. 启动文件夹中的 .bat 容易被 Windows Defender / 360 / 火绒等杀软
   当作可疑启动脚本拦截。

注册表 Run 键是 Windows 标准自启机制，无上述问题，且当前用户注册表
无需管理员权限，仅依赖标准库 winreg。
"""

import os
import sys
import winreg
from typing import Optional


class AutostartManager:
    r"""
    Windows 开机自启管理器

    实现方式：在注册表
        HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
    下新增 / 删除以 app_name 命名的字符串条目，值为启动命令行。

    设计考量：
    - 仅依赖 Python 标准库 winreg，无需 pywin32
    - 不创建 .bat 文件，规避 cmd 代码页 / 中文路径 / 杀软误报等问题
    - 支持开发环境（.py / .pyw + pythonw.exe）与打包后（.exe）两种场景
    - 当前用户注册表（HKCU）无需管理员权限
    - 自动清理旧版本在启动文件夹残留的 .bat 脚本
    """

    # 注册表 Run 键路径（当前用户，无需管理员权限）
    _RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def __init__(self, app_name: str = "CockroachPet"):
        """
        Args:
            app_name: 应用名称，作为注册表条目名
        """
        self.app_name = app_name

    # ==================== 路径解析 ====================

    def _get_target_command(self) -> Optional[str]:
        """
        获取开机自启要执行的命令行

        Returns:
            完整命令行字符串（路径已加双引号），失败返回 None
        """
        # 情况1：PyInstaller 打包后的 exe
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            if exe_path and os.path.exists(exe_path):
                # 路径加双引号，兼容空格与中文
                return f'"{exe_path}"'
            return None

        # 情况2：开发环境，使用 pythonw.exe 运行 .pyw / .py 脚本
        main_script = self._find_main_script()
        if main_script is None:
            return None

        # 优先用 pythonw.exe（无控制台窗口）
        pythonw_path = self._find_pythonw()
        if pythonw_path:
            return f'"{pythonw_path}" "{main_script}"'

        # 回退到当前 python.exe
        python_path = sys.executable
        if python_path:
            return f'"{python_path}" "{main_script}"'

        return None

    def _find_main_script(self) -> Optional[str]:
        """
        查找项目入口脚本

        查找顺序：
        1. sys.argv[0]（如果是 .py / .pyw）
        2. 当前目录下的 main.pyw / main.py 等常见入口
        """
        # 方法1：sys.argv[0]
        if sys.argv and len(sys.argv) > 0:
            script = os.path.abspath(sys.argv[0])
            if script.endswith(('.py', '.pyw')) and os.path.exists(script):
                return script

        # 方法2：常见入口文件名
        search_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = ['main.pyw', 'main.py', 'run.pyw', 'run.py', 'app.pyw', 'app.py']
        for name in candidates:
            path = os.path.join(search_dir, name)
            if os.path.exists(path):
                return path

        # 方法3：模块方式运行
        for name in ['__main__.py']:
            path = os.path.join(search_dir, name)
            if os.path.exists(path):
                return path

        return None

    def _find_pythonw(self) -> Optional[str]:
        """
        查找 pythonw.exe 的路径（无控制台窗口版本）

        Returns:
            pythonw.exe 完整路径，找不到返回 None
        """
        # 方法1：从 sys.executable 推断
        exe = sys.executable
        if exe:
            dirname = os.path.dirname(exe)
            pythonw = os.path.join(dirname, "pythonw.exe")
            if os.path.exists(pythonw):
                return pythonw

        # 方法2：PATH 中查找
        import shutil
        pythonw = shutil.which("pythonw")
        if pythonw:
            return pythonw

        # 方法3：从 sys.base_prefix 查找
        base = getattr(sys, 'base_prefix', sys.prefix)
        pythonw = os.path.join(base, "pythonw.exe")
        if os.path.exists(pythonw):
            return pythonw

        return None

    # ==================== 旧版残留清理 ====================

    def _get_legacy_bat_path(self) -> Optional[str]:
        """获取旧版在启动文件夹遗留的 .bat 脚本路径（若存在）"""
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        startup_dir = os.path.join(
            appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        return os.path.join(startup_dir, f"{self.app_name}.bat")

    def _cleanup_legacy_bat(self):
        """
        清理旧版本在启动文件夹遗留的 .bat 脚本

        迁移到注册表方案后，残留的 .bat 仍会被系统执行并报错（路径失效），
        因此首次启用注册表自启时主动删除它。
        """
        bat_path = self._get_legacy_bat_path()
        if not bat_path or not os.path.exists(bat_path):
            return
        try:
            # 先取消隐藏属性，否则 os.remove 可能失败
            try:
                import ctypes
                FILE_ATTRIBUTE_NORMAL = 0x80
                ctypes.windll.kernel32.SetFileAttributesW(bat_path, FILE_ATTRIBUTE_NORMAL)
            except Exception:
                pass
            os.remove(bat_path)
        except (IOError, OSError, PermissionError):
            # 清理失败不影响主流程
            pass

    # ==================== 状态查询 ====================

    def is_enabled(self) -> bool:
        """
        检查当前是否已设置开机自启

        Returns:
            True 表示注册表条目存在且命令行与当前目标一致
            （路径变化时会返回 False，触发重新写入）
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._RUN_KEY_PATH,
                0,
                winreg.KEY_READ,
            ) as key:
                value, _ = winreg.QueryValueEx(key, self.app_name)
        except FileNotFoundError:
            return False
        except OSError:
            return False

        # 校验注册表中的命令是否与当前目标一致
        # （项目移动位置后旧条目失效，需重新写入）
        current = self._get_target_command()
        if current is None:
            # 无法确定当前目标（异常情况），保守视为已启用避免反复写
            return bool(value)
        return value == current

    # ==================== 启用 / 禁用 ====================

    def enable(self) -> bool:
        """
        启用开机自启（写入注册表）

        流程：
        1. 获取当前目标命令行
        2. 写入 HKCU\\...\\Run 下的 app_name 条目
        3. 清理旧版启动文件夹中残留的 .bat

        Returns:
            是否设置成功
        """
        command = self._get_target_command()
        if command is None:
            print(f"[AutostartManager] 错误：无法确定可执行文件路径")
            return False

        try:
            # CreateKey 在键已存在时等价于 OpenKey，安全调用
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, self._RUN_KEY_PATH
            ) as key:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
        except OSError as e:
            print(f"[AutostartManager] 启用失败: {e}")
            return False

        # 迁移清理：删除旧版 .bat 残留
        self._cleanup_legacy_bat()
        return True

    def disable(self) -> bool:
        """
        禁用开机自启（删除注册表条目）

        Returns:
            是否删除成功（条目不存在也算成功）
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._RUN_KEY_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, self.app_name)
        except FileNotFoundError:
            return True  # 本来就没有，视为已禁用
        except OSError as e:
            print(f"[AutostartManager] 禁用失败: {e}")
            return False

        # 同步清理旧版 .bat 残留（若存在）
        self._cleanup_legacy_bat()
        return True

    def toggle(self) -> bool:
        """
        切换开机自启状态

        Returns:
            切换后的状态（True=已启用）
        """
        if self.is_enabled():
            self.disable()
            return False
        else:
            self.enable()
            return True

    def set_enabled(self, enable: bool) -> bool:
        """
        直接设置开机自启状态

        Args:
            enable: True 启用，False 禁用

        Returns:
            操作是否成功
        """
        if enable:
            return self.enable()
        else:
            return self.disable()

    def get_status_text(self) -> str:
        """获取状态描述文本"""
        if self.is_enabled():
            return "已启用 - 开机时自动启动"
        else:
            return "已禁用"

    # ==================== 调试信息 ====================

    @property
    def script_location(self) -> str:
        """返回自启条目的注册表位置（兼容旧接口）"""
        return f"HKCU\\{self._RUN_KEY_PATH}\\{self.app_name}"

    @property
    def startup_folder(self) -> str:
        """返回自启配置所在位置（兼容旧接口）"""
        return f"HKCU\\{self._RUN_KEY_PATH}"


# ---------- 简易测试 ----------
if __name__ == "__main__":
    am = AutostartManager("CockroachPet")

    print("=== 开机自启管理器测试 ===\n")
    print(f"应用名称: {am.app_name}")
    print(f"自启位置: {am.script_location}")
    print(f"当前目标命令: {am._get_target_command()}")
    print(f"pythonw路径: {am._find_pythonw()}")
    print(f"主脚本路径: {am._find_main_script()}")
    print(f"旧版 .bat 残留: {am._get_legacy_bat_path()}")
    print(f"\n当前状态: {am.get_status_text()}")

    print("\n--- 交互测试 ---")
    print("可用命令: enable, disable, toggle, status, quit")

    while True:
        try:
            cmd = input("\n> ").strip().lower()
            if cmd == "enable":
                result = am.enable()
                print(f"启用结果: {'成功' if result else '失败'}")
            elif cmd == "disable":
                result = am.disable()
                print(f"禁用结果: {'成功' if result else '失败'}")
            elif cmd == "toggle":
                result = am.toggle()
                print(f"切换结果: {'已启用' if result else '已禁用'}")
            elif cmd == "status":
                print(f"当前状态: {am.get_status_text()}")
            elif cmd == "quit":
                break
            else:
                print("未知命令")
        except KeyboardInterrupt:
            break
        except EOFError:
            break

    print("测试结束")
