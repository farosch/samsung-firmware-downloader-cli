# samsung-firmware-downloader-cli

Interactive command-line tool that searches Samsung's US support site and lists
the firmware it publishes for matching models. It covers all support branches
(phones, TVs, appliances, computing, and more).

## Usage

Prebuilt binaries for Linux, macOS (Apple Silicon), and Windows are attached to each
[GitHub release](https://github.com/farosch/samsung-firmware-downloader-cli/releases).
Run `./samsung-firmware-downloader-linux-x86_64 --version` to see which release you have.
The binaries are not code-signed, so macOS Gatekeeper and Windows SmartScreen may warn
on first run.

Or run from source:

```sh
python3 samsung-firmware-downloader.py                  # branch menu, then subcategory or keyword
python3 samsung-firmware-downloader.py --keyword HW-Q800F
python3 samsung-firmware-downloader.py --keyword soundbar --directory ~/firmware
```

1. Pick a branch number, or type a keyword (blank quits).
2. Optionally pick a subcategory. Its products are collected from the category
   tree, and each product label is searched and the results are merged. A whole
   branch can take a minute because each label is one request.
3. Firmware for each matching model is listed (models without firmware are left out).
   Enter comma-separated numbers to download. The script then returns to the branch
   menu, so you can pick another branch or keyword. Leave the firmware prompt blank to
   go back to the menu, and leave the menu blank to quit. A failed download or an invalid
   number is reported, and you are asked again. `--keyword` starts at the search instead of
   the branch menu, and the script still returns to the menu afterwards.

Downloads go to `./firmware/` by default and are never overwritten. In a terminal, each
download shows a status line with a progress bar, percent, bytes, speed, and ETA
(the ETA needs a `Content-Length` from the server).

Requires Python 3.10 or newer. It has no third-party dependencies.

## Limits

- Samsung publishes firmware for only some models. Most TV and phone models
  returned no firmware in the probes so far (see [TODO.md](TODO.md)).
- A single keyword search returns at most 10 models. Branch and subcategory
  selections avoid this by searching every product label, but a typed keyword
  or `--keyword` is still limited to 10 models.
- Label searches are fuzzy, so a list can include models from other products.
- Downloads are checked only against the server's `Content-Length`; no SHA256 is
  pinned for discovered files.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The tests are offline; all HTTP calls are mocked.

See [DEVELOP.md](DEVELOP.md) for how the lookup works.
