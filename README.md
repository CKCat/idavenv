# idavenv

[![PyPI](https://img.shields.io/pypi/v/idavenv.svg)](https://pypi.org/project/idavenv/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![IDA Pro](https://img.shields.io/badge/IDA%20Pro-9.0%2B-orange.svg)](https://hex-rays.com/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)

`idavenv` 是专为 **IDA Pro 9.0+** 设计的 IDAPython 虚拟环境管理工具与 Python 库，底层基于 **`uv`** 实现环境创建与依赖安装。

支持 IDA 9.0+ 官方原生解释器切换机制（`IDAPYTHON_VENV_EXECUTABLE`），同时提供非侵入式的 `idapythonrc.py` 挂载方案，便于在 IDA Pro 中管理和使用第三方 Python 库（如 `z3-solver`、`requests`、`idapro`、`ida-pro-mcp` 等）。

---

## 特性

- **环境管理**：基于 `uv` 进行虚拟环境创建与依赖安装；若系统未安装 `uv`，自动回退到 Python 标准库 `venv`。
- **双加载支持**：
  - **原生加载**：适配 IDA 9.0+ 原生机制，通过配置 `IDAPYTHON_VENV_EXECUTABLE` 实现解释器切换。
  - **Hook 兜底**：在 `$IDAUSR/idapythonrc.py` 中注入安全 Hook 块，未配置环境变量时由脚本挂载虚拟环境并保证加载优先级。
- **版本校验**：自动探测 IDA 宿主 Python 版本；目标版本与现有环境不一致时主动拦截并提示 `--force (-f)` 选项，避免旧环境静默残留。
- **二进制依赖支持**：Windows 下自动探测并注册虚拟环境及第三方包的 DLL 目录（`os.add_dll_directory`），支持 `z3`、`keystone` 等二进制依赖。
- **编码处理**：针对 Windows 中文环境（CP936/GBK）优化子进程管道流解码，避免输出特殊符号时崩溃。
- **环境隔离**：通过标记块管理 `idapythonrc.py`，不影响用户已有的自定义脚本；支持通过 `IDAPYTHON_VENV` 临时指定虚拟环境路径。

---

## 安装与使用

### 1. 使用 `uvx` 运行（无需安装）

```bash
# 初始化虚拟环境并关联 IDA
uvx idavenv init

# 安装第三方包
uvx idavenv install z3-solver requests

# 查看当前环境配置
uvx idavenv info
```

若需强制拉取最新发布的版本，可附加 `--refresh`：
```bash
uvx --refresh idavenv init
```

---

### 2. 全局安装使用

通过 `uv tool`：
```bash
uv tool install idavenv
uv tool upgrade idavenv
```

或通过 `pipx` / `pip`：
```bash
pipx install idavenv
# 或
pip install --upgrade idavenv
```

安装后直接在终端执行：
```bash
idavenv init
idavenv install z3-solver
idavenv info
```

---

## 命令行参考

```
usage: idavenv [-h] [--version] {init,info,install,list,run,uninstall} ...

positional arguments:
  init                创建虚拟环境并关联到 IDA (idapythonrc.py)
  info                查看 IDA 与虚拟环境状态
  install             安装 Python 包或 requirements.txt 依赖
  list                列出虚拟环境中已安装的依赖
  run                 在虚拟环境上下文中运行命令
  uninstall           移除 Hook 配置并可选择性删除虚拟环境
```

### 命令示例

```bash
# 初始化指定版本的 Python (如 3.12)
idavenv init --python 3.12

# 强制重建虚拟环境（切换 Python 版本时使用）
idavenv init --python 3.12 -f

# 批量安装 requirements 文件
idavenv install -r requirements.txt

# 安装本地 wheel 文件（如 IDA 自带的 idapro SDK）
idavenv install "<IDA_INSTALL_DIR>/idalib/python/idapro-0.0.11-py3-none-any.whl"

# 查看虚拟环境已安装的包
idavenv list

# 在虚拟环境中测试执行命令
idavenv run python -c "import sys; print(sys.executable)"

# 移除 Hook 并删除虚拟环境目录
idavenv uninstall --clean-venv
```

---

## IDA 9.0+ 原生模式配置

若希望 IDA 在通过各种快捷方式、独立可执行文件（`ida.exe` / `ida64.exe`）启动时直接生效，可设置系统或用户环境变量 `IDAPYTHON_VENV_EXECUTABLE`：

### Windows (PowerShell)
```pwsh
$venvPy = (idavenv info | Select-String "Python Executable" | ForEach-Object { ($_ -split ": ")[1].Trim() })
[Environment]::SetEnvironmentVariable("IDAPYTHON_VENV_EXECUTABLE", $venvPy, "User")
```

### Linux / macOS (Bash)
```bash
echo "export IDAPYTHON_VENV_EXECUTABLE=\"$(idavenv info | grep 'Python Executable' | awk -F': ' '{print $2}')\"" >> ~/.bashrc
```

设置后运行 `idavenv info`，`IDA 9.0+ Native` 将显示为 `Active`。

---

## Python API

支持在其他脚本或工具中直接调用：

```python
from idavenv import IDAVirtualenvManager

manager = IDAVirtualenvManager()

# 初始化（支持 force=True 覆盖重建）
res = manager.init(python_executable="3.12")
if not res.success:
    print(f"Error: {res.stderr}")

# 安装包
manager.install_packages(["z3-solver", "requests"])

# 查询状态
status = manager.status()
print(f"Hook installed    : {status.is_hooked}")
print(f"Venv path         : {status.venv_dir}")
print(f"Venv Python       : {status.venv_python_version}")
print(f"Detected IDA Py   : {status.detected_ida_python}")
print(f"IDA 9.0+ Native   : {status.is_ida9_native}")
```

---

## 常见问题

**Q: 启动 IDA 时提示 `Python version mismatch`？**  
当前 IDA 宿主配置的 Python 版本与虚拟环境所基于的版本不一致。执行以下命令指定当前 IDA 使用的版本并重建环境：
```bash
idavenv init --python <VERSION> -f
```

**Q: 执行 `idavenv install idalib` 提示找不到包？**  
Hex-Rays 官方的 Headless SDK 包名实际为 **`idapro`**，位于 IDA 安装目录下的 `idalib/python/` 目录中。使用本地路径安装即可：
```bash
idavenv install "<IDA_INSTALL_DIR>/idalib/python/idapro-*.whl"
```

---

## 参考链接 (References)

- [Hex-Rays 官方社区讨论: Using a virtualenv for IDAPython](https://community.hex-rays.com/t/using-a-virtualenv-for-idapython/261/9)
- [Hex-Rays IDA Pro 官方网站](https://hex-rays.com/)
- [IDAPython 官方仓库](https://github.com/idapython/src)
- [Astral uv 快速包管理工具](https://github.com/astral-sh/uv)
- [ida-pro-mcp: IDA Pro Model Context Protocol Server](https://github.com/mrexodia/ida-pro-mcp)
- [Model Context Protocol (MCP) 规范](https://modelcontextprotocol.io/)

---

## 构建与测试

### 构建分发包

```bash
uv build
```

### 运行测试

```bash
uv run pytest -v
```

---

## License

[MIT License](LICENSE).
