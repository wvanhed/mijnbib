import pytest

from mijnbib.errors import CanNotConnectError, IncompatibleSourceError


def test_incompatiblesourceerror():
    with pytest.raises(IncompatibleSourceError) as e:
        raise IncompatibleSourceError("message", "some source text")
    assert str(e.value) == "message"
    assert e.value.html_body == "some source text"


def test_cannotconnecterror():
    with pytest.raises(CanNotConnectError) as e:
        raise CanNotConnectError("message", "some url")
    assert str(e.value) == "message"
    assert e.value.url == "some url"
