import pytest

@pytest.fixture
def prepared_file(tmp_path):
    file_path = tmp_path / "prepared.txt"
    file_path.write_text("准备好的数据", encoding="utf-8")
    print("\n1、准备：创建文件")

    try:
        yield file_path
    finally:
        file_path.unlink(missing_ok=True)
        print("\n3、清理：删除文件")
        assert not file_path.exists()

def test_prepared_file_content(prepared_file):
    print("\n2、执行：读取并检查文件")

    assert prepared_file.read_text(encoding="utf-8") == "准备好的数据"