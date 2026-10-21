# ruff: noqa: T201, T203  # ignore print statements
"""Provides a command line interface for this package.

Run as `mijnbib` (installed script) or `python -m mijnbib` (see `__main__.py`).
"""

import argparse
import configparser
import logging
import pprint as pp
import sys

from mijnbib import AuthenticationError, MijnbibError, MijnBibliotheek, __version__
from mijnbib.const import CONFIG_FILE


def _do_login(args: argparse.Namespace):
    print("Trying to log in ...")
    print(f"Username : {args.username}")

    mb = MijnBibliotheek(args.username, args.password, args.city)
    try:
        mb.login()
    except AuthenticationError as e:
        print(str(e))
    print(f"Logged in: {mb._logged_in}")


def _connect(
    args: argparse.Namespace, what: str, show_account: bool = False
) -> MijnBibliotheek:
    print(f"Retrieving {what} ...")
    print(f"Username : {args.username}")
    if show_account:
        print(f"Account  : {args.accountid}")
    return MijnBibliotheek(args.username, args.password, args.city)


def _do_all(args: argparse.Namespace):
    pp.pprint(_connect(args, "all information").get_all_info())


def _do_accounts(args: argparse.Namespace):
    pp.pprint(_connect(args, "accounts").get_accounts())


def _do_loans(args: argparse.Namespace):
    mb = _connect(args, "loans", show_account=True)
    pp.pprint(mb.get_loans(args.accountid))


def _do_reservations(args: argparse.Namespace):
    mb = _connect(args, "reservations", show_account=True)
    pp.pprint(mb.get_reservations(args.accountid))


def main():
    # common parser, see https://stackoverflow.com/a/33646419/50899
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-u", "--username")
    common_parser.add_argument("-p", "--password")
    common_parser.add_argument("-c", "--city")
    common_parser.add_argument("-a", "--accountid")

    parser = argparse.ArgumentParser(
        prog="mijnbib",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Interact with bibliotheek.be website, e.g. to retrieve loans, "
            "reservations or accounts.\n\n"
            "Specify the required authentication parameters (username, password, ...) \n"
            "as a parameter of the subcommando. See the help of a subcommando for all \n"
            "parameters, e.g. `mijnbib --help all`\n"
            "More convenient is creating a `mijnbib.ini` file containing the parameters:\n"
            "   [DEFAULT]\n"
            "   username = john\n"
            "   password = 123456\n"
            "   accountid = 456"
        ),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    # Add values from ini file as default values. Must be done before the
    # subparsers are created, since they copy the defaults of their parent.
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    common_parser.set_defaults(**config.defaults())

    subparsers = parser.add_subparsers(required=True)

    def add_subcommand(name, help_, func, needs_account=False):
        subparser = subparsers.add_parser(name, parents=[common_parser], help=help_)
        subparser.set_defaults(func=func, needs_account=needs_account)

    add_subcommand("all", "retrieve all information for all accounts", _do_all)
    add_subcommand("accounts", "retrieve accounts", _do_accounts)
    add_subcommand("loans", "retrieve loans for account id", _do_loans, needs_account=True)
    add_subcommand(
        "reservations",
        "retrieve reservations for account id",
        _do_reservations,
        needs_account=True,
    )
    add_subcommand("login", "just log in, and report if success or not", _do_login)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(levelname)-7s %(message)s")
        logging.getLogger().setLevel(logging.DEBUG)

    required = ["username", "password"] + (["accountid"] if args.needs_account else [])
    for r in required:
        if getattr(args, r) is None:
            # prints usage + message to stderr and exits with status 2
            parser.error(
                f"Parameter '{r}' is required. "
                f"Either specify as an argument, or in file '{CONFIG_FILE}'"
            )

    # call the appropriate subcommand
    try:
        args.func(args)
    except MijnbibError as e:
        if args.verbose:
            raise  # show full traceback when debugging
        print(f"Error: {e} ({type(e).__name__})", file=sys.stderr)
        sys.exit(1)
