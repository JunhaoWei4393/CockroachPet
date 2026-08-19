# 🪳 电子桌宠蟑螂 · CockroachPet

> 一只会爬、会怕你、能被抓起来甩飞的桌面宠物蟑螂 🪳

用 Python 原生 **tkinter** 绘制，无需任何游戏引擎，纯标准库 + 两个小依赖。

![蟑螂预览](assets/cockroach_preview.png)

## ✨ 特性

- 🚶 **漫游**：在桌面上随机乱爬
- 🧲 **吸引**：鼠标慢慢靠近，它会被你吸引
- 😱 **惊吓**：鼠标快速甩向它，它会惊恐逃跑
- ✋ **抓取**：长按 0.35 秒抓起，甩手扔飞
- 🖱️ **右键菜单**：设置 / 重置位置 / 退出
- 🪟 **系统托盘**：显示/隐藏、设置、退出
- ⚙️ **配置热重载**：改 `config.json` 立即生效，无需重启

## 🚀 快速开始

### 运行源码

```bash
pip install -r requirements.txt
python src/main.py
```

### 打包成 exe

```bash
pyinstaller CockroachPet.spec
# 产物输出到 dist/ 目录
```

## 📂 目录结构

```text
.
├── src/                    # 全部源码
│   ├── main.py             # 入口与窗口
│   ├── pet.py              # 顶层门面（整合逻辑）
│   ├── renderer.py         # 画布绘制
│   ├── physics_engine.py   # 向量与物理
│   ├── behavior_engine.py  # 行为状态机
│   ├── cockroach_model.py  # 几何模型
│   ├── config_manager.py   # 配置数据层
│   ├── settings_ui.py      # 设置界面
│   ├── autostart.py        # 开机自启
│   └── previews/           # 开发预览脚本
├── assets/                 # 演示素材（README 使用）
├── config.json             # 运行配置（可调参数）
├── CockroachPet.spec       # PyInstaller 打包配置
├── requirements.txt        # 依赖清单
├── LEARNING_GUIDE.md       # 📖 白痴级源码教学
├── build/ · dist/          # 打包产物（自动生成）
└── archive/                # 历史版本构建产物存档
```

## 📖 文档

- [**LEARNING_GUIDE.md**](LEARNING_GUIDE.md) —— 从零讲透每一行代码的教学文档，适合 Python 初学者

## 📜 许可

[MIT](LICENSE)
