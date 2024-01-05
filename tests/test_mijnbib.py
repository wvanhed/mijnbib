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
            "errors",
            "mijnbibliotheek",
            "parsers",
            "models",
            "login_handlers",
            "importlib",
        ]
    )
