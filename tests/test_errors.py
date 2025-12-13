import pytest

from mijnbib.errors import IncompatibleSourceError


def test_incompatiblesourceerror():
    with pytest.raises(IncompatibleSourceError) as e:
        raise IncompatibleSourceError("message", "some source text")
    assert str(e.value) == "message"
    assert e.value.html_body == "some source text"
