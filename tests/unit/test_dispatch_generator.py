from agent_loop import BaseHandler, StepOutcome, exhaust

class ProgressHandler(BaseHandler):
    def do_progress(self, args, response):
        yield "开始执行\n"
        yield "执行完成\n"

        return StepOutcome(
            data="任务结果",
            next_prompt="继续",
            should_exit=False,
        )

def test_dispatch_forwards_progress_and_final_result():
    handler = ProgressHandler()

    generator = handler.dispatch("progress", {}, None)

    assert next(generator) == "开始执行\n"
    assert next(generator) == "执行完成\n"

    outcome = exhaust(generator)

    assert outcome.data == "任务结果"
    assert outcome.next_prompt == "继续"
    assert outcome.should_exit is False