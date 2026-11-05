# Development

## Layout

- `samsung_firmware/catalog.py`: all discovery, parsing, prompting, and download logic.
- `samsung-firmware-downloader.py`: thin entry script; the `pyproject.toml` script
  points at the same `main`.
- `tests/test_catalog.py`: offline unit tests.

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
