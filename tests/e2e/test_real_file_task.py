import os
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.mark.e2e
@pytest.mark.real_model
@pytest.mark.skipif(
    os.environ.get("RUN_REAL_MODEL_E2E") != "1",
    reason="需要显式开启真实模型 E2E",
)
def test_real_model_creates_utf8_file():
    api = pytest.importorskip("playwright.sync_api")

    project_root = Path(__file__).resolve().parents[2]
    run_id = uuid4().hex

    data_dir = project_root / "work" / "e2e-runs" / run_id
    report_dir = project_root / "reports" / "e2e" / run_id
    data_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)

    target = data_dir / "result.txt"
    expected = f"你好，GenericAgent；运行标记：{run_id}"

    assert not target.exists()

    task = (
        f"请仅创建文件：{target}\n"
        f"使用UTF-8编码，正文必须是：\n{expected}\n"
        "允许末尾换行。不要修改其他文件或记忆，"
        "不要启动长期任务。完成后结束。"
    )

    with api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True,
        )
        page = context.new_page()
        submitted = False

        try:
            page.goto(
                "http://127.0.0.1:8502",
                wait_until="domcontentloaded",
            )

            chat_input = page.get_by_placeholder(
                "any task?", exact=True
            )
            api.expect(chat_input).to_be_editable(timeout=30_000)

            running = page.locator(".ga-run-badge")
            api.expect(running).to_be_hidden()

            chat_input.fill(task)
            chat_input.press("Enter")
            submitted = True

            # 先确认开始，避免一开始没有状态就误判完成
            api.expect(running).to_be_visible(timeout=20_000)
            api.expect(running).to_be_hidden(timeout=120_000)

            assert target.is_file(), f"目标文件未创建：{target}"

            actual = target.read_text(encoding="utf-8")
            assert actual.rstrip("\r\n") == expected

            page.screenshot(
                path=str(report_dir / "success.png"),
                full_page=True,
            )

        except Exception:
            # 失败时尝试停止仍在运行的任务
            if submitted:
                try:
                    stop_button = page.get_by_role(
                        "button", name="强行停止任务", exact=True
                    )
                    if stop_button.is_visible():
                        stop_button.click(timeout=5_000)
                except Exception:
                    pass

            try:
                page.screenshot(
                    path=str(report_dir / "failure.png"),
                    full_page=True,
                )
            except Exception:
                pass

            raise

        finally:
            try:
                context.tracing.stop(
                    path=str(report_dir / "trace.zip")
                )
            finally:
                browser.close()