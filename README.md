# samsung-firmware-downloader-cli

Interactive command-line tool that searches Samsung's US support site and lists
the firmware it publishes for matching models. It covers all support branches
(phones, TVs, appliances, computing, and more), not only TVs.

## Usage

```sh
python3 samsung-firmware-downloader.py                  # branch menu, then subcategory or keyword
python3 samsung-firmware-downloader.py --keyword HW-Q800F
python3 samsung-firmware-downloader.py --keyword soundbar --directory ~/firmware
```

1. Pick a branch number, or type a keyword (blank quits).
2. Optionally pick a subcategory, which is searched by name.
3. Firmware for each matching model is listed. Enter comma-separated numbers to
   download, or leave blank to skip.

Downloads go to `./firmware/` by default and are never overwritten.

Requires Python 3.10 or newer. It has no third-party dependencies.

## Limits

- Samsung publishes firmware for only some models. Most TV and phone models
  returned no firmware in the probes so far (see [TODO.md](TODO.md)).
- Keyword searches return at most 10 models.
- Downloads are checked only against the server's `Content-Length`; no SHA256 is
  pinned for discovered files.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The tests are offline; all HTTP calls are mocked.

See [DEVELOP.md](DEVELOP.md) for how the lookup works.
