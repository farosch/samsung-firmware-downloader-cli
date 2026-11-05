"""Discover Samsung US support firmware through the public support JSON APIs.

Flow: product-picker branches -> keyword (branch/subcategory name or typed text)
-> model search -> firmware entries from each model's product detail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, TextIO

from .progress import ProgressBar

try:
    # Makes input() handle arrow keys and line editing instead of echoing escape codes.
    import readline  # noqa: F401
except ImportError:  # Windows has no readline module.
    pass

SITE = "https://www.samsung.com/us"
PICKER_URL = f"{SITE}/api/search/es_search/support/product_picker.json"
SEARCH_URL = f"{SITE}/support/search/es_search/models.json"
TAXONOMY_URL = f"{SITE}/api/search/es_search/support/contact_search/downloads.json"
DETAIL_URL = f"{SITE}/api/support/product/detail/{{model}}.json"
FIRMWARE_HOSTS = {"org.downloadcenter.samsung.com", "downloadcenter.samsung.com"}
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
MAX_JSON_BYTES = 32 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class Category:
    name: str
    children: tuple["Category", ...] = field(default_factory=tuple)
    code: str = ""


@dataclass(frozen=True)
class Model:
    name: str
    display_name: str


@dataclass(frozen=True)
class Firmware:
    model: str
    title: str
    version: str
    size: str
    filename: str
    url: str


def fetch_json(url: str):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise ValueError(f"{url}: expected HTTP 200, got {response.status}")
        body = response.read(MAX_JSON_BYTES + 1)
    if len(body) > MAX_JSON_BYTES:
        raise ValueError(f"{url}: response exceeds {MAX_JSON_BYTES} bytes")
    return json.loads(body)


def _category(node: dict) -> Category:
    return Category(
        name=str(node.get("name", "")).strip(),
        children=tuple(_category(child) for child in node.get("child") or [] if isinstance(child, dict)),
        code=str(node.get("id", "")).strip(),
    )


def parse_picker(payload) -> list[Category]:
    nodes = payload.get("response") if isinstance(payload, dict) else payload
    if not isinstance(nodes, list):
        raise ValueError("unexpected product picker payload")
    return [_category(node) for node in nodes if isinstance(node, dict) and node.get("name")]


def search_models(keyword: str) -> list[Model]:
    payload = fetch_json(f"{SEARCH_URL}?{urllib.parse.urlencode({'keyword': keyword})}")
    if not isinstance(payload, list):
        raise ValueError("unexpected model search payload")
    models: dict[str, Model] = {}
    for item in payload:
        if isinstance(item, dict) and item.get("prdMdlName"):
            name = str(item["prdMdlName"])
            models.setdefault(name, Model(name, str(item.get("displayName") or name)))
    return list(models.values())


def _leaf_labels(node: dict, labels: list[str]) -> None:
    children = [child for child in node.get("child") or [] if isinstance(child, dict)]
    if children:
        for child in children:
            _leaf_labels(child, labels)
        return
    label = str(node.get("supportLabel") or "").strip()
    # Series labels such as "DW80N3030 Series" search better without the suffix.
    if label.endswith(" Series"):
        label = label[: -len(" Series")].strip()
    if label:
        labels.append(label)


def taxonomy_labels(code: str) -> list[str]:
    """Product labels under a category code. The taxonomy is not capped at 10 results."""
    query = urllib.parse.urlencode({"taxonomyCode": code, "taxonomyFromLvl": 1, "taxonomyToLvl": 5})
    payload = fetch_json(f"{TAXONOMY_URL}?{query}")
    nodes = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(nodes, list):
        raise ValueError("unexpected taxonomy payload")
    labels: list[str] = []
    for node in nodes:
        if isinstance(node, dict):
            _leaf_labels(node, labels)
    return list(dict.fromkeys(labels))


def search_labels(labels: list[str]) -> list[Model]:
    """Search each label and merge the results, since one search returns at most 10 models."""
    models: dict[str, Model] = {}
    for label in labels:
        for model in search_models(label):
            models.setdefault(model.name, model)
    return list(models.values())


def validated_url(url) -> str | None:
    if not isinstance(url, str):
        return None
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in FIRMWARE_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        return None
    return url


def firmware_for(model: Model) -> list[Firmware]:
    try:
        payload = fetch_json(DETAIL_URL.format(model=urllib.parse.quote(model.name, safe="")))
    except urllib.error.HTTPError as error:
        # Many listed models have no product detail page; that means no firmware, not a failed scan.
        if error.code == 404:
            return []
        raise
    if not isinstance(payload, list):
        return []
    found: dict[str, Firmware] = {}
    for variant in payload:
        downloads = variant.get("downloads") if isinstance(variant, dict) else None
        for entries in (downloads or {}).values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("typeCode") != "FM":
                    continue
                url = validated_url(entry.get("downloadUrl"))
                if url is None or url in found:
                    continue
                found[url] = Firmware(
                    model=model.name,
                    title=str(entry.get("fileName") or ""),
                    version=str(entry.get("version") or ""),
                    size=str(entry.get("fileSize") or ""),
                    filename=str(entry.get("stdFileName") or Path(urllib.parse.urlparse(url).path).name),
                    url=url,
                )
    return list(found.values())


def download(firmware: Firmware, directory: Path, status: TextIO | None = None) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", firmware.filename) or firmware.filename.startswith("."):
        raise ValueError(f"unsafe firmware filename: {firmware.filename!r}")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / firmware.filename
    if target.exists():
        print(f"Already present: {target}", flush=True)
        return target
    print(f"Downloading {firmware.filename} ({firmware.size or 'unknown size'})", flush=True)
    temporary: Path | None = None
    bar: ProgressBar | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=directory, prefix=firmware.filename + ".", suffix=".part", delete=False
        ) as output:
            temporary = Path(output.name)
            request = urllib.request.Request(firmware.url, headers={**HEADERS, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise ValueError(f"{firmware.filename}: expected HTTP 200, got {response.status}")
                declared = response.headers.get("Content-Length")
                total = int(declared) if declared and declared.isdigit() else None
                if status is not None:
                    bar = ProgressBar(status, total)
                received = 0
                while chunk := response.read(CHUNK_SIZE):
                    received += len(chunk)
                    output.write(chunk)
                    if bar is not None:
                        bar.update(received)
            if bar is not None:
                bar.finish()
            if declared is not None and int(declared) != received:
                raise ValueError(f"{firmware.filename}: received {received} bytes, expected {declared}")
        # NamedTemporaryFile is created 0600; publish with normal read permissions.
        temporary.chmod(0o644)
        # Hard-link so an existing target is never replaced.
        target.hardlink_to(temporary)
        temporary.unlink()
        temporary = None
        print(f"Downloaded: {target}", flush=True)
        return target
    finally:
        if bar is not None:
            bar.finish()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def pick_keyword(tree: list[Category], ask: Callable[[str], str],
                 show: Callable[[str], None]) -> tuple[str, str] | None:
    """Return (keyword, taxonomy code); the code is "" for typed keywords."""
    show("Branches:")
    for number, branch in enumerate(tree, 1):
        show(f"  {number}. {branch.name} ({len(branch.children)} subcategories)")
    answer = ask("Branch number, or keyword to search (blank to quit): ").strip()
    if not answer:
        return None
    if not answer.isdigit() or not 1 <= int(answer) <= len(tree):
        return answer, ""
    branch = tree[int(answer) - 1]
    if not branch.children:
        return branch.name, branch.code
    show(f"Subcategories of {branch.name}:")
    for number, child in enumerate(branch.children, 1):
        show(f"  {number}. {child.name}")
    choice = ask("Subcategory number (blank for the whole branch): ").strip()
    if not choice:
        return branch.name, branch.code
    if choice.isdigit() and 1 <= int(choice) <= len(branch.children):
        child = branch.children[int(choice) - 1]
        return child.name, child.code
    show("Invalid subcategory.")
    return None


def run(keyword: str | None, ask: Callable[[str], str], show: Callable[[str], None], directory: Path) -> int:
    code = ""
    if keyword is None:
        selection = pick_keyword(parse_picker(fetch_json(PICKER_URL)), ask, show)
        if not selection:
            return 0
        keyword, code = selection
    labels = taxonomy_labels(code) if code else []
    if labels:
        show(f"Searching {len(labels)} product labels under {keyword!r}...")
        models = search_labels(labels)
    else:
        models = search_models(keyword)
    if not models:
        show(f"No models found for {keyword!r}.")
        return 0
    show(f"Models for {keyword!r}:")
    for number, model in enumerate(models, 1):
        show(f"  {number}. {model.display_name} [{model.name}]")
    firmware: list[Firmware] = []
    for model in models:
        firmware.extend(firmware_for(model))
    if not firmware:
        show("No firmware published for these models.")
        return 0
    show("Firmware:")
    for number, item in enumerate(firmware, 1):
        show(f"  {number}. [{item.model}] {item.filename} v{item.version} {item.size}".rstrip())
    selection = ask("Firmware numbers to download, comma-separated (blank to skip): ").strip()
    if not selection:
        return 0
    chosen = set()
    for part in selection.split(","):
        part = part.strip()
        if not part.isdigit() or not 1 <= int(part) <= len(firmware):
            raise ValueError(f"invalid firmware number: {part!r}")
        chosen.add(int(part))
    for number in sorted(chosen):
        download(firmware[number - 1], directory, status=sys.stdout if sys.stdout.isatty() else None)
    return 0


def main(argv: list[str] | None = None, ask: Callable[[str], str] = input,
         show: Callable[[str], None] = print) -> int:
    parser = argparse.ArgumentParser(prog="samsung-firmware-downloader", description=__doc__)
    parser.add_argument("--keyword", help="skip the branch menu and search this keyword")
    parser.add_argument("--directory", type=Path, default=Path("firmware"),
                        help="download directory (default: ./firmware)")
    args = parser.parse_args(argv)
    try:
        return run(args.keyword, ask, show, args.directory)
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled; incomplete download removed.", file=sys.stderr)
        return 130
