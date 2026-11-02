import pytest

@pytest.mark.parametrize("content", ["第一组数据", "第二组数据"])
def test_temporary_workspace(tmp_path, content):
    # 每个测试项都有自己的临时目录
    file_path = tmp_path / "sample.txt"

    # 开始时不应存在其他测试留下的同名文件
    assert not file_path.exists()

    # 在当前测试的目录中准备数据
    file_path.write_text(content, encoding="utf-8")

    assert file_path.read_text(encoding="utf-8") == content

    print(f"本次临时文件：{file_path}")