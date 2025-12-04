# ruff: noqa: T201
from pathlib import Path

import requests

URL = "https://bibliotheek.be/library-search/autocomplete?q=%20"
OUTPUT_FILE = "libraries.md"

print("Fetching libraries from:", URL)
response = requests.get(URL, timeout=10)
response.raise_for_status()
data = response.json()

labels = sorted([entry["label"] + "  " for entry in data], key=str.casefold)

print("Writing libraries to:", OUTPUT_FILE)
preamble = (
    "# List of Libraries\n\n"
    "This file contains the list of libraries that are supported by bibliotheek.be.\n"
    "You can use the search function in your browser to find a particular library or city.\n"
    "A more up-to-date list might be available at <https://bibliotheek.be/bibliotheken>.\n\n"
)
Path(OUTPUT_FILE).write_text(preamble + "\n".join(labels) + "\n", encoding="utf-8")
