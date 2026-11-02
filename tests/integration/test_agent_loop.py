from copy import deepcopy
from os import system
from types import SimpleNamespace
from agent_loop import BaseHandler, StepOutcome, agent_runner_loop, exhaust
import pytest
import json

# ---------- 第一部分：准备模型响应 ----------

def make_echo_response():
    """第1轮响应：要求调用 echo 工具。"""
    function = SimpleNamespace(
        name="echo",
        arguments='{"text": "你好"}',
    )

    tool_call = SimpleNamespace(
        id="call_echo_001",
        function=function,
    )

    return SimpleNamespace(
        content="",
        tool_calls=[tool_call],
    )


def make_final_response():
    """第2轮响应：给出最终回复，不再调用工具。"""
    return SimpleNamespace(
        content="任务完成",
        tool_calls=[],
    )

def make_stop_response():
    return SimpleNamespace(
        content="",
        tool_calls=[
            SimpleNamespace(
                id="call_stop_001",
                function=SimpleNamespace(
                    name="stop",
                    arguments="{}",
                ),
            )
        ],
    )

# ---------- 第二部分：假模型客户端 ----------

class FakeClient:
    def __init__(self):
        self.responses = [
            make_echo_response(),
            make_final_response(),
        ]
        self.calls = []

    def chat(self, messages, tools):
        """记录本轮请求，然后返回下一个预设响应。"""
        self.calls.append(
            {
                "messages": deepcopy(messages),
                "tools": deepcopy(tools),
            }
        )

        if not self.responses:
            raise AssertionError("模型调用次数超出预期")

        response = self.responses.pop(0)

        yield "假模型正在响应\n"
        return response


# ---------- 第三部分：提供可控工具的处理器 ----------

class IntegrationHandler(BaseHandler):
    def __init__(self):
        # 真实循环需要访问这两个属性
        self.parent = SimpleNamespace(task_dir=None)
        self._done_hooks = []

        # 记录工具执行情况，供测试检查
        self.echo_calls = []

    def do_echo(self, args, response):
        """模拟一个工具：返回输入文字，并要求循环继续。"""
        self.echo_calls.append(args.copy())

        return StepOutcome(
            data=args["text"],
            next_prompt="请根据工具结果完成回复",
            should_exit=False,
        )

    def do_no_tool(self, args, response):
        """模型没有调用工具时，结束当前任务。"""
        return StepOutcome(
            data=response.content,
            next_prompt=None,
            should_exit=False,
        )

    def do_stop(self, args, response):
        return StepOutcome(
            data="主动停止",
            next_prompt="这条提示不应触发下一轮",
            should_exit=True,
        )


# ---------- 第四部分：真正的集成测试 ----------

@pytest.mark.parametrize(
    "verbose",
    [
        pytest.param(False, id="compact"),
        pytest.param(True, id="verbose"),
    ],
)
def test_loop_passes_tool_result_to_model_and_finishes(verbose):
    # 1. 准备
    client = FakeClient()
    handler = IntegrationHandler()
    user_input = "请使用 echo 工具返回你好"

    # 本测试的假客户端不使用工具描述，因此传空列表
    tools_schema = []

    # 2. 执行真实 Agent 循环
    result = exhaust(
        agent_runner_loop(
            client=client,
            system_prompt="你是测试助手",
            user_input=user_input,
            handler=handler,
            tools_schema=tools_schema,
            max_turns=3,
            verbose=verbose,
        )
    )

    # 3. 检查模型调用次数
    assert len(client.calls) == 2

    # 4. 检查首轮输入
    assert client.calls[0]["messages"] == [
        {"role": "system", "content": "你是测试助手"},
        {"role": "user", "content": user_input},
    ]

    # 5. 检查工具收到的参数，以及只执行了一次
    assert handler.echo_calls == [
        {
            "text": "你好",
            "_index": 0,
            "_tool_num": 1,
        }
    ]

    # 6. 检查工具结果确实进入第二轮模型请求
    assert client.calls[1]["messages"] == [
        {
            "role": "user",
            "content": "请根据工具结果完成回复",
            "tool_results": [
                {
                    "tool_use_id": "call_echo_001",
                    "content": "你好",
                }
            ],
        }
    ]

    # 7. 检查循环正常完成，而非耗尽最大轮数
    assert result == {
        "result": "CURRENT_TASK_DONE",
        "data": "任务完成",
    }

@pytest.mark.parametrize("max_turns", [1, 2, 3])
def test_loop_stops_at_max_turns(max_turns):
    client = FakeClient()
    handler = IntegrationHandler()

    client.responses = [
        make_echo_response()
        for _ in range(max_turns + 1)
    ]

    result = exhaust(
        agent_runner_loop(
            client=client,
            system_prompt="你是测试助手",
            user_input="持续调用echo工具",
            handler=handler,
            tools_schema=[],
            max_turns=max_turns,
            verbose=False,
        )
    )
    assert result == {"result": "MAX_TURNS_EXCEEDED"}
    assert len(client.calls) == max_turns
    assert len(handler.echo_calls) == max_turns
    assert len(client.responses) == 1

def test_loop_exits_when_tool_requests_stop():
    client = FakeClient()
    handler = IntegrationHandler()

    client.responses = [
        make_stop_response(),
        make_final_response(),
    ]

    result = exhaust(
        agent_runner_loop(
            client=client,
            system_prompt="你是测试助手",
            user_input="请停止任务",
            handler=handler,
            tools_schema=[],
            max_turns=3,
            verbose=False,
        )
    )

    assert result == {
        "result":"EXITED",
        "data":"主动停止",
    }
    assert len(client.calls) == 1
    assert len(client.responses) == 1
    assert handler.echo_calls == []


def test_loop_reports_unknown_tool_and_recovers():
    client = FakeClient()
    handler = IntegrationHandler()

    # 复用已有响应结构，只把工具名改为不存在的名称
    unknown_response = make_echo_response()
    unknown_response.tool_calls[0].function.name = "missing_tool_xyz"

    client.responses = [
        unknown_response,
        make_final_response(),
    ]

    # 设置非空标记，检查未知工具分支是否清除此缓存字段
    client.last_tools = "cached-tool-description"

    result = exhaust(
        agent_runner_loop(
            client=client,
            system_prompt="你是测试助手",
            user_input="执行工具任务",
            handler=handler,
            tools_schema=[],
            max_turns=3,
            verbose=False,
        )
    )

    assert len(client.calls) == 2

    assert client.calls[1]["messages"] == [
        {
            "role": "user",
            "content": "未知工具 missing_tool_xyz",
            "tool_results": [],
        }
    ]

    assert client.last_tools == ""
    assert handler.echo_calls == []

    assert result == {
        "result": "CURRENT_TASK_DONE",
        "data": "任务完成",
    }

def test_loop_rejects_invalid_tool_arguments():
    client = FakeClient()
    handler = IntegrationHandler()

    invalid_response = make_echo_response()
    invalid_response.tool_calls[0].function.arguments = "{"

    client.responses = [
        invalid_response,
        make_final_response(),
    ]

    with pytest.raises(json.JSONDecodeError):
        exhaust(
            agent_runner_loop(
                client=client,
                system_prompt="你是测试助手",
                user_input="执行工具任务",
                handler=handler,
                tools_schema=[],
                max_turns=3,
                verbose=False,
            )
        )

    assert len(client.calls) == 1
    assert handler.echo_calls == []
    assert len(client.responses) == 1