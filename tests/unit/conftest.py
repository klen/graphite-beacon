import pytest

from graphite_beacon.core import Reactor


@pytest.fixture
def reactor():
    return Reactor(history_size='40m')
