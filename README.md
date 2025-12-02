# mijnbib

Python API for bibliotheek.be (formerly mijn.bibliotheek.be)

With this Python library you can retrieve your borrowed items, reservations and
account information if you have an account on <https://bibliotheek.be>, the
Flemish & Brussels public library network. You can also extend loans.

This API allows you to show and extend your loans (or loans from multiple accounts
in your family) in your own coding projects, such as a small desktop or web
application.

A list of supported libraries can be found in [libraries.md](./libraries.md).

## Installation

Install via:

    pip install mijnbib

Or, to force an upgrade:

    pip install --upgrade mijnbib

## Usage

For example, retrieving your borrowed items can be done as follows (after installation):

    from mijnbib import MijnBibliotheek

    username = "johndoe"
    password = "12345678"
    account_id = "123"  # see the number in the URL, or via mb.get_accounts()

    mb = MijnBibliotheek(username, password)
    loans = mb.get_loans(account_id)
    print(loans)

For a more readable version, use `pprint()`:

    import pprint
    pprint.pprint([l for l in loans])

    [Loan(title='Erebus',
      loan_from=datetime.date(2023, 11, 25),
      loan_till=datetime.date(2023, 12, 23),
      author='Palin, Michael',
      type='Boek',
      extendable=True,
      extend_url='https://gent.bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123/uitleningen/verlengen?loan-ids=789',
      extend_id='789',
      branchname='Gent Hoofdbibliotheek',
      id='456789',
      url='https://gent.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C456789',
      cover_url='https://webservices.bibliotheek.be/index.php?func=cover&ISBN=9789000359325&VLACCnr=10157217&CDR=&EAN=&ISMN=&EBS=&coversize=medium',
      account_id='123'
      )]

For more examples, see the code in the `examples` folder.
It also uses `asdict` for conversion to a dictionary.

## Command-line interface

You can call the module from the command-line as follows:

    python -m mijnbib loans
    python -m mijnbib --version

Or, directly via the CLI command:

    mijnbib loans

The `--help` option shows all available options

    $ mijnbib --help
    usage: mijnbib [-h] [-V] [-v] {all,accounts,loans,reservations,login} ...

    Interact with bibliotheek.be website, e.g. to retrieve loans, reservations
    or accounts.

    Specify the required authentication parameters (username, password, ...) 
    as a parameter of the subcommando. See the help of a subcommando for all 
    parameters, e.g. `mijnbib --help all`
    More convenient is creating a `mijnbib.ini` file containing the parameters:
    [DEFAULT]
    username = john
    password = 123456
    accountid = 456

    positional arguments:
    {all,accounts,loans,reservations,login}
        all                 retrieve all information for all accounts
        accounts            retrieve accounts
        loans               retrieve loans for account id
        reservations        retrieve reservations for account id
        login               just log in, and report if success or not

    options:
    -h, --help            show this help message and exit
    -V, --version         show program's version number and exit
    -v, --verbose         show debug logging

## Notes

- **Error handling**. Depending on the application, it may be advisable to
  provide error handling. The `errors.py` file contains the list of
  Mijnbib-specific exceptions. The docstrings of the public methods contain
  the errors that can occur. For example:

        from mijnbib import AuthenticationError, MijnbibError, MijnBibliotheek

        mb = MijnBibliotheek(username, password)
        try:
            accounts = mb.get_accounts()
        except AuthenticationError as e:
            print(e)  # wrong credentials
        except MijnbibError as e:
            print(e)  # any other custom mijnbib error

- **Compatibility with bibliotheek.be** - This Python API retrieves its data
  via web scraping of the bibliotheek.be website.
  Therefore it depends on the structure of the website. When the structure of
  the website changes, it is very likely that all or certain functionality
  will suddenly stop working.  
  In that case, you have to wait until this Python library is updated to deal
  with the new structure.  
  Provide a try/except wrapper, where you either catch `MijnbibError`, or the
  more specific `IncompatibleSourceError`.

## Alternatives

The Home Assistant plugin <https://github.com/myTselection/bibliotheek_be> scrapes
the bibliotheek.be website in a similar way.

## Development

This project uses `uv`. If needed, install first via, e.g.

    curl -LsSf https://astral.sh/uv/install.sh | sh

To install all dependencies for development:

    make init

If all is good, the following should print `mijnbib <version>`:

    uv run mijnbib --version

Note: This works because mijnbib is installed as a cli script via the
`project.scripts` entry in `pyproject.toml`, with `uv run` taking care of
activating the virtual environment before running the command.

You need `make` as well. For installation on Windows, see the options at
<https://stackoverflow.com/a/32127632/50899>

Running the tests, applying linting and code formatting can be done via:

    make test
    make lint
    make format

To work around the challenge of testing a web scraper, the following *snapshot
testing* approach can be used to get some confidence when applying refactoring:

1. Create a file `mijnbib.ini` in the project root folder, and make it contain
   a section `[DEFAULT]` holding the following parameters: `username`,
   `password` and `account_id`
2. Run `python tests/save_testref.py` to capture and store the current output
   (a couple of files will be created)
3. Perform refactoring as needed
4. Run `pytest tests/tst_mijnbibliotheek.py` (note: it's `pytest` here!) to check
   if the output still matches the earlier captured output

Creating a distribution archive:

    make clean
    make build
