# ruff: noqa: T201, T203  # ignore print statements
"""Provides a command line interface for this package.

A __main__.py file is executed when the package itself is invoked directly from
the command line using the -m flag, that is:
    python -m mijnbib
"""

import argparse
import configparser
import logging
import pprint as pp
import sys

from mijnbib import AuthenticationError, MijnBibliotheek, __version__

CONFIG_FILE = "mijnbib.ini"


def _do_login(args: argparse.Namespace):
    print("Trying to log in ...")
    print(f"Username : {args.username}")

    mb = MijnBibliotheek(args.username, args.password, args.city)
    try:
        mb.login()
    except AuthenticationError as e:
        print(str(e))
    print(f"Logged in: {mb._logged_in}")


def _do_all(args: argparse.Namespace):
    print("Retrieving all information ...")
    print(f"Username : {args.username}")

    mb = MijnBibliotheek(args.username, args.password, args.city)
    result = mb.get_all_info()
    pp.pprint(result)


def _do_accounts(args: argparse.Namespace):
    print("Retrieving accounts ...")
    print(f"Username : {args.username}")

    mb = MijnBibliotheek(args.username, args.password, args.city)
    result = mb.get_accounts()
    pp.pprint(result)


def _do_loans(args: argparse.Namespace):
    print("Retrieving loans ...")
    print(f"Username : {args.username}")
    print(f"Account  : {args.accountid}")

    mb = MijnBibliotheek(args.username, args.password, args.city)
    result = mb.get_loans(args.accountid)
    pp.pprint(result)


def _do_reservations(args: argparse.Namespace):
    print("Retrieving reservations ...")
    print(f"Username : {args.username}")
    print(f"Account  : {args.accountid}")

    mb = MijnBibliotheek(args.username, args.password, args.city)
    result = mb.get_reservations(args.accountid)
    pp.pprint(result)


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
        version="%(prog)s {version}".format(version=__version__),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    subparsers = parser.add_subparsers(required=True)
    parser_all = subparsers.add_parser(
        "all", parents=[common_parser], help="retrieve all information for all accounts"
    )
    parser_all.set_defaults(func=_do_all)
    parser_all = subparsers.add_parser(
        "accounts", parents=[common_parser], help="retrieve accounts"
    )
    parser_all.set_defaults(func=_do_accounts)
    parser_all = subparsers.add_parser(
        "loans", parents=[common_parser], help="retrieve loans for account id"
    )
    parser_all.set_defaults(func=_do_loans)
    parser_all = subparsers.add_parser(
        "reservations", parents=[common_parser], help="retrieve reservations for account id"
    )
    parser_all.set_defaults(func=_do_reservations)
    parser_all = subparsers.add_parser(
        "login", parents=[common_parser], help="just log in, and report if success or not"
    )
    parser_all.set_defaults(func=_do_login)

    # Add values from ini file as default values
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    common_parser.set_defaults(**config.defaults())

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(levelname)-7s %(message)s")
        logging.getLogger().setLevel(logging.DEBUG)

    required = ["username", "password"]
    for r in required:
        if getattr(args, r) is None:
            print(
                f"Parameter '{r}' is required. "
                f"Either specify as an argument, or in file '{CONFIG_FILE}'"
            )
            sys.exit(-1)

    # call the appropriate subcommand
    args.func(args)


if __name__ == "__main__":
    main()
