import pytest

from agent_loop import BaseHandler

@pytest.fixture
def handler():
    return BaseHandler()