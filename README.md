# GenericAgent 自动化测试

## 当前范围

- 产品单元测试：工具分发、生成器输出、异常传播。
- 假模型集成测试：结果传递、正常完成、主动退出、
  轮数上限、未知工具恢复、非法 JSON。
- pytest 基础练习：临时目录与 fixture 清理。

当前共 21 个测试项，其中 3 项为框架学习练习。
不调用真实模型，不覆盖完整前端 E2E。

## 已验证环境

- Windows
- Python 3.13.8
- 测试依赖见 requirements-test.txt
- 被测源码提交：
  a9a36b4b219593369de01c3e5973e56ac02e568b

## 目录约定

两个项目需要同级放置：

```text
工作目录/
├── agentProject/
└── agentTest/
```

pytest.ini 使用 ../agentProject 导入被测源码。
运行前应核对源码提交和本地修改。

## 首次准备环境

先进入 agentTest 目录。

新机器需要预先安装 Python 3.13。
仅在 .venv-auto 不存在时创建：

```powershell
py -3.13 -m venv .venv-auto
```

检查当前终端是否配置了额外模块路径：

```powershell
$env:PYTHONPATH
```

如果存在不属于本测试环境的 site-packages 路径，
先记录并在当前终端移除，避免加载外部包：

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
```

安装并检查依赖：

```powershell
& '.\.venv-auto\Scripts\python.exe' -m pip install -r requirements-test.txt
& '.\.venv-auto\Scripts\python.exe' -m pip check
```

无需激活环境，使用完整的相对解释器路径执行。

## 运行全部测试并生成报告

```powershell
New-Item -ItemType Directory -Path .\reports -Force | Out-Null

& '.\.venv-auto\Scripts\python.exe' -m pytest tests -v --junitxml=reports/junit.xml --html=reports/all-tests-report.html --self-contained-html --cov=agent_loop --cov-branch --cov-report=term-missing --cov-report=html:reports/coverage
```

## 查看结果

- reports/all-tests-report.html：测试执行详情。
- reports/junit.xml：供 CI 解析的结果。
- reports/coverage/index.html：agent_loop 模块覆盖率。

报告使用固定名称，再次运行会覆盖。

覆盖率仅表示代码执行范围，不证明断言有效或产品无缺陷。

## 已知限制

- 当前只固定直接测试依赖，尚非完整环境锁文件。
- 尚未验证在另一台机器上的重建。
- 原产品环境存在 FastAPI/Starlette 冲突；
  独立测试环境的检查通过不代表原环境已修复。