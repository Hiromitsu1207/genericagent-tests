import pytest
from agent_loop import BaseHandler, exhaust, StepOutcome

class RecordingHandler(BaseHandler):
    def do_echo(self, args, response):
        self.received_args = args.copy()
        self.received_response = response

        self.tool_outcome = StepOutcome(
            data="工具执行结果",
            next_prompt="继续下一步",
            should_exit=False,
        )
        return self.tool_outcome

    def do_crash(self, args, response):
        raise RuntimeError("测试工具执行失败")

def test_dispatch_calls_matching_tool():
    handler = RecordingHandler()
    response = object()
    args = {"text":"你好"}

    outcome = exhaust(
        handler.dispatch(
            "echo",
            args,
            response,
            index=1,
            tool_num=3,
        )
    )
    assert handler.received_args=={
        "text":"你好",
        "_index":1,
        "_tool_num":3,
    }
    assert handler.received_response is response
    assert outcome is handler.tool_outcome

def test_unknown_tool_returns_feedbacks(handler):
    outcome = exhaust(
        handler.dispatch("tool_that_does_not_exist", {}, None)
    )

    assert "未知工具" in outcome.next_prompt
    assert outcome.should_exit is False
    # assert outcome.should_exit is True

def test_dispatch_propagates_tool_error():
    handler = RecordingHandler()

    with pytest.raises(
        RuntimeError,
        match="测试工具执行失败",
    ):
        exhaust(
            handler.dispatch("crash", {}, None)
        )


@pytest.mark.parametrize(
    "tool_name",
    [
        pytest.param("missing_tool_xyz", id="plain-name"),
        pytest.param("missing_tool_123", id="with-digits"),
        pytest.param("missing_tool_中文", id="with-chinese"),
    ],
)
def test_unknown_tool_feedback_contains_tool_name(handler, tool_name):
    outcome = exhaust(
        handler.dispatch(tool_name, {}, None)
    )

    assert tool_name in outcome.next_prompt

@pytest.mark.parametrize(
    "args, expected_prompt",
    [
        pytest.param(
        {"msg":"Json格式错误"},
        "Json格式错误",
        id="custom-message",
        ),
        pytest.param(
            {},
            "bad_json",
            id="default-message",
        ),
        pytest.param(
            {"msg":""},
            "",
            id="empty-message",
        ),
    ],
)

def test_bad_json_returns_feedback(handler, args, expected_prompt):
    outcome = exhaust(
        handler.dispatch("bad_json", args, None)
    )

    assert outcome.next_prompt == expected_prompt
    assert outcome.data is None
    assert outcome.should_exit is False
