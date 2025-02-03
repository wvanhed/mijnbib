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
    cproc = subprocess.run(["mijnbib", "--version"])  # noqa: S603, S607
    assert cproc.returncode == 0

    cproc = subprocess.run(["mijnbib", "--help"])  # noqa: S603, S607
    assert cproc.returncode == 0
