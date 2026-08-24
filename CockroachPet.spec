# -*- mode: python ; coding: utf-8 -*-
import os

project_dir = os.path.abspath(SPECPATH)
src_dir = os.path.join(project_dir, 'src')

# 显式打包所有本地 .py 模块，防止 PyInstaller 漏收集
# （源码统一放在 src/ 子目录下）
local_py_files = [
    'config_manager.py',
    'physics_engine.py',
    'behavior_engine.py',
    'cockroach_model.py',
    'autostart.py',
    'pet.py',
    'renderer.py',
    '__init__.py',
    'settings_ui.py',
]
local_datas = [(os.path.join(src_dir, f), '.') for f in local_py_files]

a = Analysis(
    [os.path.join(src_dir, 'main.py')],
    pathex=[project_dir, src_dir],
    binaries=[],
    datas=local_datas,
    hiddenimports=[
        'config_manager',
        'physics_engine',
        'behavior_engine',
        'cockroach_model',
        'autostart',
        'pet',
        'renderer',
        'settings_ui',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        # winreg 是标准库，PyInstaller 默认会包含，无需显式声明
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CockroachPet_2026.08.24',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
