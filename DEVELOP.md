# Development

## Layout

- `samsung_firmware/catalog.py`: all discovery, parsing, prompting, and download logic.
- `samsung-firmware-downloader.py`: thin entry script; the `pyproject.toml` script
  points at the same `main`.
- `tests/test_catalog.py`: offline unit tests.

## Lookup flow

1. `GET /us/api/search/es_search/support/product_picker.json` returns the category
   tree (`response` list of nodes with `name` and `child`). Leaves have no model codes.
2. `GET /us/support/search/es_search/models.json?keyword=...` returns records with
   `prdMdlName` (the model code) and `displayName`. `parentModel` holds category
   codes, not models, and is not used.
3. `GET /us/api/support/product/detail/<prdMdlName>.json` returns variants. Each
   variant's `downloads` maps categories to entries; entries with `typeCode` `FM`
   carry `downloadUrl`, `fileName`, `version`, `fileSize`, and `stdFileName`.
4. Only HTTPS URLs on `org.downloadcenter.samsung.com` or
   `downloadcenter.samsung.com` are accepted.

## Download safety

- Filenames must match `[A-Za-z0-9._-]+` and must not start with `.`.
- Data goes to a `.part` temp file (mode 0644 before publish), then is
  hard-linked to the target, so an existing file is never replaced.
- Length is checked against `Content-Length` when the server sends it.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Live check

Verify against the live site with a keyword such as `HW-Q800F` and a small file
(for example the `Firmware_Upgrade_Instruction.pdf` entry), then delete the
download.
