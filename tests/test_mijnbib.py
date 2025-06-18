import importlib.metadata
import subprocess


def test_mijnbib_available_imports():
    import mijnbib

    # make sure we don't expose too few, or too much
    imps = [i for i in dir(mijnbib) if not i.startswith("__")]
    assert set(imps) == set(
        [
            "MijnBibliotheek",
            "Loan",
            "Reservation",
            "Account",
            "ItemAccessError",
            "AuthenticationError",
            "CanNotConnectError",
            "ExtendLoanError",
            "IncompatibleSourceError",
            "MijnbibError",
            "TemporarySiteError",
            # things we actually don't want to have exported
            "const",
            "errors",
            "mijnbibliotheek",
            "parsers",
            "models",
            "login_handlers",
            "importlib",
        ]
    )


def test_cli():
    cproc = subprocess.run(["mijnbib", "--version"], capture_output=True, text=True)  # noqa: S607
    ver = importlib.metadata.version("mijnbib")  # from pyproject.toml file
    assert f"mijnbib {ver}" in cproc.stdout
    assert cproc.returncode == 0

    cproc = subprocess.run(["mijnbib", "--help"])  # noqa: S607
    assert cproc.returncode == 0
