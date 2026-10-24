# idavenv 🚀

[![PyPI](https://img.shields.io/pypi/v/idavenv.svg)](https://pypi.org/project/idavenv/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![IDA Pro](https://img.shields.io/badge/IDA%20Pro-9.0%2B-orange.svg)](https://hex-rays.com/)
[![Backend](https://img.shields.io/badge/Powered%20by-uv-purple.svg)](https://github.com/astral-sh/uv)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)]()
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)

基于 **`uv`** 的跨平台自动化 **IDAPython 虚拟环境** 管理工具与 Python 库，专为 **IDA Pro 9.0+** 设计。

参考 Hex-Rays 官方社区讨论 [Using a virtualenv for IDAPython](https://community.hex-rays.com/t/using-a-virtualenv-for-idapython/261/9) 与 **IDAPython 9.0+ 官方 C 级原生实现**，提供**双轨虚拟环境加载机制**（官方原生 `IDAPYTHON_VENV_EXECUTABLE` + 非侵入式 `idapythonrc.py` 智能 Hook 兜底），使 IDA Pro 能够无缝、极速加载独立的 Python 虚拟环境及其第三方依赖（如 `z3-solver`, `requests`, `capstone`, `ida-pro-mcp` 等）。

---

## 🌟 核心特性

- ⚡ **毫秒级极速管理**：深度集成 Astral 的 **`uv`**（`uv venv` 和 `uv pip`），秒级创建环境与解析依赖，同时提供标准库 `venv` 的无缝回退支持。
- 🎯 **IDA 9.0+ 双轨原生架构**：
  - **原生 C 级别加载 (轨道 1)**：完全契合 IDA 9.0+ IDAPython 源码检测机制。通过配置 `IDAPYTHON_VENV_EXECUTABLE`，IDA 在启动时直接由 C 源码层切换虚拟环境解释器，完全原生抑制系统全局包。
  - **智能 Hook 兜底 (轨道 2)**：自动注入 `$IDAUSR/idapythonrc.py`。若已被原生接管则瞬间 0 开销标记退出；若未设置环境变量，则以最高优先级挂载虚拟环境并持久化 DLL 目录。
- 🖥️ **全平台深度适配**：
  - **Windows**：自动探测 `%APPDATA%\Hex-Rays\IDA Pro` 与 `Lib/site-packages`，原生支持 Python 3.8+ `os.add_dll_directory` 并持久化 DLL 句柄（解决 `z3`, `unicorn`, `keystone` 等二进制扩展 DLL 动态加载问题）。
  - **Linux**：自动探测 `~/.idapro` 与 `lib/pythonX.Y/site-packages`。
  - **macOS**：自动探测 `~/.idapro`。
  - 支持 `$IDAUSR` 多路径智能发现（优先复用已有配置）。
- 🛡️ **安全隔离与智能诊断**：
  - 使用专用标记块 (`# >>> IDAPython Virtualenv Hook >>>`) 注入 `idapythonrc.py`，绝不破坏用户原有的 IDA 配置。
  - 自动提升虚拟环境在 `sys.path` 中的加载优先级，彻底防止宿主全局旧版本包覆盖（Shadowing）。
  - 内置 `builtins` 哨兵变量机制，杜绝在 IDA 中切换数据库或重复执行时的重入副作用。
  - 包含 Python 版本不匹配智能诊断与友好告警。
- 🔄 **动态多环境切换**：
  - 支持通过环境变量 `IDAPYTHON_VENV=/path/to/custom_venv` 动态临时覆盖当前激活的虚拟环境。
- 📦 **支持多种依赖安装格式**：
  - 支持安装单个/多个包：`idavenv install z3-solver requests`
  - 支持批量安装依赖文件：`idavenv install -r requirements.txt`
  - 支持安装 GitHub 仓库：`idavenv install "git+https://github.com/mrexodia/ida-pro-mcp"`

---

## 🚀 极速上手

### 方式 1：使用 `uvx` 免安装直接运行（最优雅推荐！）

无需提前安装任何包，直接在终端中调用：

```bash
# 1. 一键初始化 IDAPython 虚拟环境并自动关联 IDA
uvx idavenv init

# 2. 为 IDA 安装依赖（秒级解析安装）
uvx idavenv install z3-solver requests

# 3. 诊断当前环境状态
uvx idavenv info
```

---

### 方式 2：使用 `pip` 或 `pipx` 全局安装

```bash
pip install idavenv

# 随后可在任意终端直接使用 idavenv 命令：
idavenv init
idavenv install z3-solver
idavenv info
```

---

### 方式 3：源码本地运行

```bash
uv run main.py init
uv run main.py install z3-solver
uv run main.py info
```

---

## 🛠️ 命令行参考 (CLI Reference)

```
usage: idavenv [-h] [--version] {init,info,install,list,run,uninstall} ...

positional arguments:
  init                Create virtualenv and link to IDA via idapythonrc.py
  info                Display IDA and IDAPython virtualenv status.
  install             Install Python packages or requirement files into IDAPython virtualenv.
  list                List packages installed in IDAPython virtualenv.
  run                 Run a command inside IDAPython virtualenv environment.
  uninstall           Remove IDAPython virtualenv hook and optionally delete venv.
```

### 常用命令示例

```bash
# 1. 初始化并指定特定 Python 解释器 (例如 3.11)
idavenv init --python 3.11

# 2. 安装 requirements.txt 文件中的所有依赖
idavenv install -r requirements.txt

# 3. 查看环境中已安装的依赖
idavenv list

# 4. 在虚拟环境中执行测试命令
idavenv run python -c "import z3; print(z3.__version__)"

# 5. 解除 IDA 关联
idavenv uninstall
```

---

## 💻 Python API 使用

作为第三方库被其它 IDA 插件或自动化工具集成：

```python
from idavenv import IDAVirtualenvManager

manager = IDAVirtualenvManager()

# 初始化环境并关联 IDA
manager.init()

# 安装依赖
manager.install_packages(packages=["z3-solver", "requests"])

# 查看状态
status = manager.status()
print(f"Hook installed : {status.is_hooked}")
print(f"Venv path      : {status.venv_dir}")
print(f"IDA 9.0+ Native: {status.is_ida9_native}")
```

---

## 📦 PyPI 构建与发布指南

### 构建分发包

```bash
uv build
# 产物生成在 dist/ 目录下：
# - dist/idavenv-0.1.0.tar.gz (sdist)
# - dist/idavenv-0.1.0-py3-none-any.whl (wheel)
```

### 发布到 PyPI

```bash
# 使用 uv publish 上传
uv publish
# 或通过 API Token 发布
uv publish --token <YOUR_PYPI_API_TOKEN>
```

---

## 🧪 自动化测试

项目遵循严格的 TDD 规范，覆盖全部跨平台路径、Hook 注入、DLL 目录、版本诊断、IDA 9.0+ 原生接管检测与 CLI 全功能（60 项测试全部通过）：

```bash
uv run pytest -v
```

---

## 📄 License

MIT License.
