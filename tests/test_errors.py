from mijnbib.errors import CanNotConnectError, IncompatibleSourceError


def test_incompatiblesourceerror():
    try:
        raise IncompatibleSourceError("message", "some source text")
    except IncompatibleSourceError as e:
        assert str(e) == "message"
        assert e.html_body == "some source text"


def test_connotconnecterror():
    try:
        raise CanNotConnectError("message", "some url")
    except CanNotConnectError as e:
        assert str(e) == "message"
        assert e.url == "some url"
