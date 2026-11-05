# Development

## Layout

- `samsung_firmware/catalog.py`: all discovery, parsing, prompting, and download logic.
- `samsung_firmware/progress.py`: download status line (`ProgressBar`, formatting helpers).
  Redraws use `\r` plus `ESC[2K`, throttled to 0.1 s; `finish()` ends the line and is idempotent.
  The bar is drawn only when stdout is a TTY.
- `samsung-firmware-downloader.py`: thin entry script; the `pyproject.toml` script
  points at the same `main`.
- `.github/workflows/release.yml`: tests, version bump, PyInstaller builds, and GitHub
  release on every push to `main`. See [Releases](#releases).
- `tests/test_catalog.py`, `tests/test_progress.py`: offline unit tests.
  Run with `python3 -m unittest discover -s tests -v`.

## Lookup flow

1. `GET /us/api/search/es_search/support/product_picker.json` returns the category
   tree (`response` list of nodes with `id`, `name` and `child`). Leaves have no model
   codes; each node's `id` is its taxonomy code.
2. For a chosen branch or subcategory, `GET /us/api/search/es_search/support/contact_search/downloads.json?taxonomyCode=<id>&taxonomyFromLvl=1&taxonomyToLvl=5`
   returns the uncapped product tree. The `supportLabel` of each leaf (with any
   trailing ` Series` removed) is a product label. Labels that are empty are skipped,
   and duplicates are removed.
3. Each label is searched with `GET /us/support/search/es_search/models.json?keyword=<label>`.
   This returns records with `prdMdlName` (the model code) and `displayName`. The
   search returns at most 10 records, so the results of all labels are merged and
   deduplicated by model code. `parentModel` holds category codes, not models, and
   is not used. If the taxonomy has no labels, the subcategory name is searched.
4. Typed keywords and `--keyword` have no taxonomy node, so they run one capped search.
5. `GET /us/api/support/product/detail/<prdMdlName>.json` returns variants. Each
   variant's `downloads` maps categories to entries; entries with `typeCode` `FM`
   carry `downloadUrl`, `fileName`, `version`, `fileSize`, and `stdFileName`.
6. Only HTTPS URLs on `org.downloadcenter.samsung.com` or
   `downloadcenter.samsung.com` are accepted.

## Control flow

`run()` loops. Each pass picks a branch/subcategory or keyword (`pick_keyword`),
then `browse()` searches, lists firmware, and downloads the chosen items. Blank
answers at the firmware prompt return to the menu, and a blank menu answer quits.
Per-download errors and invalid firmware numbers are reported and re-prompted, not raised.

## Download safety

- Filenames must match `[A-Za-z0-9._-]+` and must not start with `.`.
- Data goes to a `.part` temp file (mode 0644 before publish), then is
  hard-linked to the target, so an existing file is never replaced.
- Length is checked against `Content-Length` when the server sends it.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Releases

`.github/workflows/release.yml` runs on every push to `main`, which includes merged PRs.
It runs in four jobs:

1. `test`: `python3 -m unittest discover -s tests`. A failure stops the release.
2. `version`: finds the latest `vX.Y.Z` tag, ignoring pre-release tags such as `v1.0.0-rc1`.
   It bumps the patch number by default. Label the PR `release:minor` or `release:major`
   to bump those parts instead. With no release tag yet, the first release is `v0.1.0`.
   The job fails if the computed tag already exists.
3. `build`: a matrix over `ubuntu-latest`, `macos-latest`, and `windows-latest`. Each job
   writes the version into `samsung_firmware/__init__.py` and `pyproject.toml`, builds a
   one-file binary with PyInstaller, runs `--version` and `--help` as a smoke test, and
   uploads it as an artifact.
4. `release`: creates the `vX.Y.Z` tag at the merge commit and a GitHub release with all
   binaries attached and generated notes.

The git tag is the source of truth for the version. The workflow does not commit a version
bump back to `main`, so the `version` value in the source stays `0.1.0` and the binaries
carry the released version. Releases run one at a time (`concurrency: release`).

To check the workflow without publishing, run `actionlint .github/workflows/release.yml`.
To check the build locally, copy the repo, run the same `sed` stamp, and run
`python3 -m PyInstaller --onefile --name samsung-firmware-downloader samsung-firmware-downloader.py`.

Known gaps: the macOS binary is arm64 only (Intel Macs must run from source), and the
binaries are not code-signed or notarized.

## Live check

Verify against the live site with a keyword such as `HW-Q800F` and a small file
(for example the `Firmware_Upgrade_Instruction.pdf` entry), then delete the
download.
