# GenericAgent 自动化测试

本项目使用 Python、pytest 和 Playwright，逐步验证 GenericAgent 的核心逻辑、假模型协作流程及真实模型文件任务。

## 1. 测试范围与当前结果

当前共 23 个测试项：

| 类别 | 数量 | 内容 |
|---|---:|---|
| 产品单元测试 | 10 | 工具分发、生成器输出、异常传播 |
| pytest 基础练习 | 3 | 临时目录隔离、fixture 准备与清理 |
| 假模型集成测试 | 8 | 正常完成、轮数上限、主动退出、未知工具、非法 JSON |
| 浏览器页面测试 | 1 | 页面输入框可见且可编辑 |
| 真实模型 E2E | 1 | 页面提交任务，创建 UTF-8 中文文件并独立核对 |

普通运行及 GitHub Actions 已验证：

```text
21 passed, 2 skipped
```

两项浏览器/E2E 测试需要分别显式开启。

真实模型文件任务已在本地单次执行通过，尚未验证长期稳定性。当前测试不覆盖整个产品，也不覆盖所有副作用和异常场景。

## 2. 已验证环境

- 本地系统：Windows
- CI：GitHub Actions Windows runner
- Python：3.13.8
- pytest：9.0.2
- pytest-html：4.2.0
- pytest-cov：7.1.0
- Playwright：1.64.1
- E2E 服务端 Streamlit：1.66.1

被测源码提交：

```text
a9a36b4b219593369de01c3e5973e56ac02e568b
```

依赖文件：

- requirements-test.txt：普通单元、集成测试依赖
- requirements-e2e.txt：包含基础测试依赖和 Playwright

目前仅固定直接测试依赖，尚未实现全部传递依赖锁定。

## 3. 目录结构

普通测试要求测试项目和产品源码同级：

```text
工作目录/
├── agentProject/
│   └── agent_loop.py
└── agentTest/
    ├── .github/
    │   └── workflows/
    │       └── tests.yml
    ├── pytest.ini
    ├── requirements-test.txt
    ├── requirements-e2e.txt
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   └── e2e/
    ├── reports/
    └── work/
```

pytest.ini 使用以下配置导入产品源码：

```ini
pythonpath = ../agentProject
```

其中：

- reports：生成的报告、截图和 trace
- work：本地 E2E 产品副本、运行环境及任务文件
- reports 和 work 均不纳入 Git

普通单元、集成测试使用同级的 agentProject。
浏览器 E2E 通过 HTTP 访问独立启动的产品服务。

## 4. 准备基础测试环境

以下 PowerShell 命令均在 agentTest 根目录运行。

新机器需要预先安装 Python 3.13。
仅在 .venv-auto 不存在时创建：

```powershell
py -3.13 -m venv .venv-auto
```

检查解释器及 pip：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E --version
& '.\.venv-auto\Scripts\python.exe' -E -m pip --version
```

pip 路径应位于 .venv-auto 内。

安装并检查依赖：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m pip install -r requirements-test.txt
& '.\.venv-auto\Scripts\python.exe' -E -m pip check
```

预期依赖检查结果：

```text
No broken requirements found.
```

无需激活环境，命令显式使用环境中的解释器。

-E 让 Python 忽略 PYTHONPATH 等 Python 环境变量，避免外部包路径污染。
它不会清除 RUN_BROWSER_E2E 等自定义测试开关，也不提供文件或网络隔离。

## 5. 运行普通测试

先确保没有遗留的 E2E 开关：

```powershell
Remove-Item Env:RUN_BROWSER_E2E -ErrorAction SilentlyContinue
Remove-Item Env:RUN_REAL_MODEL_E2E -ErrorAction SilentlyContinue
```

运行全部测试：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m pytest tests -v
```

当前预期：

```text
21 passed, 2 skipped
```

仅运行单元测试：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m pytest tests/unit -v
```

仅运行假模型集成测试：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m pytest tests/integration -v
```

普通单元和假模型集成测试不调用真实模型，不需要模型密钥。

## 6. 生成执行报告与覆盖率

```powershell
New-Item -ItemType Directory -Path .\reports -Force | Out-Null

& '.\.venv-auto\Scripts\python.exe' -E -m pytest tests -v --junitxml=reports/junit.xml --html=reports/all-tests-report.html --self-contained-html --cov=agent_loop --cov-branch --cov-report=term-missing --cov-report=html:reports/coverage
```

输出文件：

| 路径 | 用途 |
|---|---|
| reports/all-tests-report.html | 查看测试执行结果与失败详情 |
| reports/junit.xml | 供 CI 等工具解析测试结果 |
| reports/coverage/index.html | 查看 agent_loop 模块覆盖率 |

打开报告：

```powershell
Start-Process .\reports\all-tests-report.html
Start-Process .\reports\coverage\index.html
```

读取 JUnit 汇总：

```powershell
[xml]$testReport = Get-Content -LiteralPath .\reports\junit.xml -Raw

$testReport.testsuites.testsuite |
    Select-Object tests, failures, errors, skipped
```

报告使用固定名称，再次运行会覆盖。

已验证的 agent_loop 模块覆盖率为 87%，该值仅对应当时的源码和测试集。
覆盖率表示代码执行范围，不证明断言有效、需求完整或产品不存在缺陷。

## 7. 本地浏览器与真实模型 E2E

### 7.1 前置条件

- 独立服务运行在 http://127.0.0.1:8502。
- 使用专用产品副本和运行环境。
- 本地模型配置可用。
- 循环执行与自主行动关闭。
- 运行期间不向同一服务同时提交其他任务。
- 模型配置、密钥、运行数据不纳入 Git。

当前两个测试分别由以下开关控制：

| 开关 | 作用 |
|---|---|
| RUN_BROWSER_E2E=1 | 执行页面就绪检查，不提交模型任务 |
| RUN_REAL_MODEL_E2E=1 | 执行真实模型文件任务 |

两个开关彼此独立，标记 e2e 或 real_model 本身不会开启测试。

### 7.2 准备独立产品副本

仅在目标目录不存在时执行：

```powershell
New-Item -ItemType Directory -Path .\work -Force | Out-Null

git clone --no-hardlinks ..\agentProject .\work\e2e-product

git -C .\work\e2e-product checkout --detach a9a36b4b219593369de01c3e5973e56ac02e568b
```

不要复制日常运行环境的 memory、temp 或虚拟环境。

克隆会包含该提交中已跟踪的文件，并不保证所有记忆目录为空。
独立副本可以分开保存应用状态，但不是限制 Agent 文件访问权限的安全沙箱。

### 7.3 准备 E2E 服务端环境

仅在 work/.venv-e2e 不存在时执行：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m venv .\work\.venv-e2e
```

安装核心产品依赖和已验证的前端版本：

```powershell
& '.\work\.venv-e2e\Scripts\python.exe' -E -m pip install .\work\e2e-product "streamlit==1.66.1"

& '.\work\.venv-e2e\Scripts\python.exe' -E -m pip check
```

在本机准备：

```text
work/e2e-product/mykey.py
```

可使用本人已有的有效配置。复制前检查目标文件是否已存在，避免覆盖。
不要把配置正文、密钥或令牌写入测试代码、README 或提交记录。

确认产品副本内部会忽略配置：

```powershell
git -C .\work\e2e-product check-ignore mykey.py
```

测试项目外层也应通过 /work/ 忽略整个工作目录。

### 7.4 启动独立前端

在新的 PowerShell 窗口中，从 agentTest 根目录执行：

```powershell
$e2ePython = (Resolve-Path .\work\.venv-e2e\Scripts\python.exe).Path

Set-Location .\work\e2e-product

& $e2ePython -E -m streamlit run .\frontends\stapp.py --server.address 127.0.0.1 --server.port 8502
```

保持该终端运行，在浏览器访问：

```text
http://127.0.0.1:8502
```

确认所选模型正确，循环执行和自主行动关闭。

已验证时的界面配置标签为 NativeOAI/deepseek-flash。
该标签本身不能独立证明服务端实际模型身份。

重启服务会清除进程内状态，但不会清空磁盘上的记忆和日志。
新浏览器上下文也不会重置后端 Agent。

### 7.5 安装浏览器测试依赖

回到另一个位于 agentTest 根目录的终端：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m pip install -r requirements-e2e.txt

& '.\.venv-auto\Scripts\python.exe' -E -m playwright install chromium

& '.\.venv-auto\Scripts\python.exe' -E -m pip check
```

### 7.6 执行页面就绪检查

此测试只打开页面并检查输入框，不发送模型任务：

```powershell
$env:RUN_BROWSER_E2E = '1'
try {
    & '.\.venv-auto\Scripts\python.exe' -E -m pytest tests/e2e/test_page_ready.py -v
}
finally {
    Remove-Item Env:RUN_BROWSER_E2E -ErrorAction SilentlyContinue
}
```

已验证单次结果为 1 passed。

### 7.7 执行真实模型文件任务

此测试会调用真实模型，可能产生费用：

```powershell
$env:RUN_REAL_MODEL_E2E = '1'
try {
    & '.\.venv-auto\Scripts\python.exe' -E -m pytest tests/e2e/test_real_file_task.py -v
}
finally {
    Remove-Item Env:RUN_REAL_MODEL_E2E -ErrorAction SilentlyContinue
}
```

测试过程：

1. 创建包含唯一运行标记的专用目录。
2. 通过页面提交创建文件任务。
3. 等待 RUNNING 状态出现并消失。
4. 独立检查目标文件存在。
5. 使用 UTF-8 读取正文并比较，仅忽略末尾回车、换行。
6. 保存截图和浏览器 trace。

已验证单次结果为 1 passed。
单次通过不代表真实模型的长期稳定性。

### 7.8 查看 E2E 证据

- 页面检查截图：reports/e2e/page-ready.png
- 真实任务证据：reports/e2e/<运行标记>/
- 任务文件：work/e2e-runs/<运行标记>/result.txt

真实任务证据目录包含成功或失败截图，以及 trace.zip。
这些文件可能含对话内容，分享前检查。

查看指定 trace：

```powershell
& '.\.venv-auto\Scripts\python.exe' -E -m playwright show-trace 'reports/e2e/替换为实际运行标记/trace.zip'
```

Trace Viewer 中可查看：

- Fill：填写任务
- Press Enter：提交任务
- Expect visible：等待运行开始
- Expect hidden：等待运行结束
- Before / After：操作前后的页面快照
- Log：定位与等待过程

Python 的磁盘读取和普通 assert 不会作为浏览器操作显示在 trace 中。

### 7.9 当前 E2E 限制

- 尚未完成多次重复运行和稳定性统计。
- 极快任务可能在页面采样前结束，导致未观察到 RUNNING。
- 等待超时是局部操作上限，不是整个测试的总时限。
- 超时后会尝试停止任务，但尚未独立验证强停效果。
- 文件断言没有验证其他文件和记忆完全未变化。
- 独立产品副本不提供操作系统级沙箱。
- 显式运行时仍需检查实际结果，不能把 skipped 当成执行通过。

## 8. GitHub Actions

工作流文件：

```text
.github/workflows/tests.yml
```

当前触发方式：

- 推送到 master
- 向 master 发起 Pull Request
- 手动触发 workflow_dispatch

流水线会：

1. 获取测试仓库。
2. 获取固定提交的 GenericAgent 产品源码。
3. 保持 agentTest 和 agentProject 同级。
4. 准备 Python 3.13.8。
5. 安装 requirements-test.txt。
6. 执行 pip check。
7. 运行测试，生成 JUnit、HTML 和覆盖率报告。
8. 即使测试失败，也尝试上传已有报告。

报告产物名称：

```text
test-reports
```

保留期为 7 天。

普通 CI 不安装浏览器依赖，不设置 E2E 开关，不调用真实模型。
当前已验证结果为 21 passed、2 skipped。

已通过教学 PR 验证：

```text
故意失败 → CI 红灯 → 报告仍可下载
删除演示测试 → CI 恢复绿灯
```

CI 显示失败不等于已配置强制禁止合并。
分支保护和必需检查规则尚未作为本项目已完成内容。

## 9. 版本管理约定

建议纳入 Git：

- 测试代码
- pytest 配置
- 依赖清单
- GitHub Actions 工作流
- 运行说明

以下内容由 .gitignore 排除：

- 本地虚拟环境
- Python 和 pytest 缓存
- 生成的报告
- 下载的 CI 报告目录
- E2E 工作副本与运行数据
- 本地环境配置

不要使用 git add . 直接纳入未经检查的现场数据。
提交前检查暂存清单：

```powershell
git diff --cached --name-only
git diff --cached --check
```

## 10. 已知环境问题与复现边界

- 原产品 .venv313 曾存在 FastAPI/Starlette 依赖冲突，尚未修复。
- 专用测试环境检查通过，不代表原产品环境已修复。
- 曾存在 PYTHONPATH 指向外部 site-packages 的情况；
  本文使用 -E 避免 Python 环境变量污染。
- GitHub Actions 已验证可以在云端新环境中安装依赖并运行普通测试。
- 本地真实模型 E2E 仍依赖人工准备的配置和运行中的服务。
- 直接依赖已固定，但传递依赖和 Actions 版本尚未完整锁定。
- 当前结论绑定已记录的源码提交和测试范围。

## 11. 教学交接

本地教学进度记录：

```text
AUTOMATION_HANDOFF_ZH.md
```

新对话可先读取该文件，再核对当前代码和实际运行结果。
交接文件是否上传，以 Git 实际跟踪状态为准。