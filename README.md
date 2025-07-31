# mijnbib

Python API voor bibliotheek.be (voorheen mijn.bibliotheek.be)

Met deze Python library kan je jouw ontleende items, reservaties en
accountinfo opvragen indien je een account hebt op <https://bibliotheek.be>.

## Installatie

Installeer via:

    pip install mijnbib

Of, om een ugrade af te dwingen:

    pip install --upgrade mijnbib

## Gebruik

Bijvoorbeeld, het opvragen van je ontleende items kan als volgt (na installatie):

    from mijnbib import MijnBibliotheek

    username = "johndoe"
    password = "12345678"
    account_id = "123"  # zie het getal in de URL, of via mb.get_accounts()

    mb = MijnBibliotheek(username, password)
    loans = mb.get_loans(account_id)
    print(loans)

Voor een meer leesbare versie, gebruik `pprint()`:

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

Voor meer voorbeelden, zie de code in de folder `examples`.
Daarin wordt ook `asdict` gebruikt voor conversie naar een dictionary.

## Command-line interface

Via de command-line kan je de module als volgt aanroepen:

    python -m mijnbib loans
    python -m mijnbib --version

Of, rechtstreeks via:

    mijnbib loans

De optie `--help` toont alle beschikbare opties

    $ mijnbib --help
    usage: mijnbib [-h] [-V] [-v] {all,accounts,loans,reservations,login} ...

    Interact with bibliotheek.be website, e.g. to retrieve loans, reservations or accounts.

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

## Opmerkingen

- **Authenticatie**. Inloggen bij de bibliotheek.be website gebeurt standaard
  via een webformulier. Het is ook mogelijk om de `oauth` manier te gebruiken;
  maar dit is nog experimenteel.

        mb = MijnBibliotheek(username, password, login_by="oauth")
        accounts = mb.get_accounts()

- **Foutafhandeling**. Afhankelijk van de toepassing, kan het aangeraden zijn om
  foutafhandeling te voorzien. Het bestand `errors.py` bevat de lijst van
  Mijnbib-specifieke exceptions. De docstrings van de publieke methods bevatten
  de errors die kunnen optreden. Bijvoorbeeld:

        from mijnbib import AuthenticationError, MijnbibError, MijnBibliotheek

        mb = MijnBibliotheek(username, password)
        try:
            accounts = mb.get_accounts()
        except AuthenticationError as e:
            print(e)  # wrong credentials
        except MijnbibError as e:
            print(e)  # any other custom mijnbib error

- **Compatibiliteit met bibliotheek.be** - Deze Python API haalt zijn gegevens
  via webscraping van de bibliotheek.be website.
  Daardoor is ze afhankelijk van de structuur van de website. Bij een wijziging aan
  de structuur van de website is het dus heel waarschijnlijk dat alle of bepaalde
  functionaliteit plots niet meer werkt.  
  In dat geval is het wachten tot deze Python library geupdate is om met de nieuwe
  structuur om te gaan.  
  Voorzie een try/except wrapper, waarbij je ofwel `MijnbibError` opvangt, of de
  meer specifieke `IncompatibleSourceError`.

## Alternatieven

De Home Assistant plugin <https://github.com/myTselection/bibliotheek_be> scraped
op een gelijkaardige manier de bibliotheek.be website.

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
