# mijnbib

Python API voor (mijn.) bibliotheek.be

Met deze Python library kan je jouw ontleende items, reservaties en
accountinfo opvragen indien je een account hebt op <https://bibliotheek.be>.

## Installatie

Installeer via:

    pip install mijnbib

## Gebruik

Bijvoorbeeld, het opvragen van je ontleende items kan als volgt (na installatie):

    from mijnbib import MijnBibliotheek

    city = "gent"           # jouw gemeente of stad
    username = "johndoe"
    password = "12345678"
    account_id = "12345"    # zie het getal in de URL, of via mb.get_accounts()

    mb = MijnBibliotheek(username, password, city)
    loans = mb.get_loans(account_id)
    print(loans)

Voor meer voorbeelden, zie de code in de folder `examples`.
Daarin wordt ook `pprint` gebruikt voor een meer leesbare output.

## Opmerkingen

Deze Python API haalt zijn gegevens via webscraping van de bibliotheek.be website.
Daardoor is ze afhankelijk van de structuur van de website. Bij een wijziging aan
de structuur van de website is het dus heel waarschijnlijk dat alle of bepaalde
functionaliteit plots niet meer werkt.

In dat geval is het wachten tot deze Python library geupdate is om met de nieuwe
structuur om te gaan.

## Alternatieven

De Home Assistant plugin <https://github.com/myTselection/bibliotheek_be> scraped
op een gelijkaardige manier de bibliotheek.be website.

## Development

To install all dependecies for development, install (in a virtualenv) via:

    pip install -e .[dev]      # 'dev' is defined in pyproject.toml

Running the tests and applying code formatting can be done via:

    make test
    make black

To work around the challenge of testing a web scraper, the following *snapshot
testing* approach can be used to get some confidence when applying refactoring:

1. Create a file `test_config.py` in the project root folder, and make it contain
  the `city`, `username`, `password` and and `account_id` (see the next file for
  expected variable naming and format)
2. Run `python tests/save_testref.py` to capture and store the current output
   (a couple of files will be created)
4. Perform refactoring as needed
5. Run `pytest tests/tst_mijnbibliotheek.py` (note: it's `pytest` here!) to check
   if the output still matches the earlier captured output

Creating a distribution archive:

    make clean
    make build
