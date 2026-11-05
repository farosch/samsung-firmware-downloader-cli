import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from samsung_firmware import catalog  # noqa: E402
from samsung_firmware.catalog import Firmware, Model  # noqa: E402

PICKER = {
    "response": [
        {"name": "HOME APPLIANCES", "child": [{"name": "Dishwashers"}, {"name": "Washers"}]},
        {"name": "SMART HOME", "child": []},
    ]
}
FM_URL = "https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx?CDSite=US&VPath=FM/1/Firmware_USB.zip"
DETAIL = [
    {
        "downloads": {
            "Firmware": [
                {"typeCode": "FM", "fileName": "Upgrade File", "version": "1102", "fileSize": "1 MB",
                 "stdFileName": "Firmware_USB.zip", "downloadUrl": FM_URL},
                {"typeCode": "FM", "fileName": "Bad host", "stdFileName": "x.zip",
                 "downloadUrl": "https://example.com/Firmware.zip"},
                {"typeCode": "FM", "fileName": "Plain http", "stdFileName": "y.zip",
                 "downloadUrl": "http://org.downloadcenter.samsung.com/y.zip"},
            ],
            "Software": [{"typeCode": "SW", "downloadUrl": FM_URL}],
        }
    }
]


class Response(io.BytesIO):
    status = 200

    def __init__(self, data: bytes, length: int | None = None):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data) if length is None else length)}


def fake_fetch(url):
    if url == catalog.PICKER_URL:
        return PICKER
    if url.startswith(catalog.SEARCH_URL):
        return [{"prdMdlName": "HW-Q800F", "displayName": "Soundbar"}]
    return DETAIL


class ParsingTests(unittest.TestCase):
    def test_parse_picker_builds_branches_and_children(self):
        tree = catalog.parse_picker(PICKER)
        self.assertEqual([b.name for b in tree], ["HOME APPLIANCES", "SMART HOME"])
        self.assertEqual([c.name for c in tree[0].children], ["Dishwashers", "Washers"])
        self.assertEqual(tree[1].children, ())

    def test_parse_picker_rejects_unexpected_payload(self):
        with self.assertRaises(ValueError):
            catalog.parse_picker({"other": 1})

    def test_validated_url_accepts_only_https_samsung_download_hosts(self):
        self.assertEqual(catalog.validated_url(FM_URL), FM_URL)
        self.assertIsNone(catalog.validated_url("https://example.com/Firmware.zip"))
        self.assertIsNone(catalog.validated_url("http://org.downloadcenter.samsung.com/y.zip"))
        self.assertIsNone(catalog.validated_url("https://user@org.downloadcenter.samsung.com/y.zip"))
        self.assertIsNone(catalog.validated_url(None))


class DiscoveryTests(unittest.TestCase):
    def test_search_models_deduplicates_by_model_code(self):
        payload = [
            {"prdMdlName": "HW-Q800F", "displayName": "Soundbar"},
            {"prdMdlName": "HW-Q800F", "displayName": "Soundbar again"},
            {"displayName": "no code"},
        ]
        with patch.object(catalog, "fetch_json", return_value=payload):
            models = catalog.search_models("soundbar")
        self.assertEqual(models, [Model("HW-Q800F", "Soundbar")])

    def test_firmware_for_keeps_only_valid_firmware_entries_once(self):
        with patch.object(catalog, "fetch_json", return_value=DETAIL):
            items = catalog.firmware_for(Model("HW-Q800F", "Soundbar"))
        self.assertEqual(
            items,
            [Firmware("HW-Q800F", "Upgrade File", "1102", "1 MB", "Firmware_USB.zip", FM_URL)],
        )


class InteractiveTests(unittest.TestCase):
    def run_main(self, answers, argv=None, fetch=None):
        output = []
        answers = iter(answers)
        with patch.object(catalog, "fetch_json", side_effect=fetch or fake_fetch):
            code = catalog.main(argv or [], ask=lambda prompt: next(answers), show=output.append)
        return code, "\n".join(output)

    def test_branch_then_subcategory_lists_firmware_without_download(self):
        code, text = self.run_main(["1", "2", ""])
        self.assertEqual(code, 0)
        self.assertIn("Washers", text)
        self.assertIn("Firmware_USB.zip", text)

    def test_keyword_skips_branch_menu(self):
        seen = []

        def fetch(url):
            seen.append(url)
            return fake_fetch(url)

        code, text = self.run_main([""], argv=["--keyword", "soundbar"], fetch=fetch)
        self.assertEqual(code, 0)
        self.assertNotIn(catalog.PICKER_URL, seen)
        self.assertIn("keyword=soundbar", seen[0])
        self.assertIn("Firmware_USB.zip", text)

    def test_blank_branch_answer_quits_without_model_search(self):
        seen = []

        def fetch(url):
            seen.append(url)
            return fake_fetch(url)

        code, text = self.run_main([""], fetch=fetch)
        self.assertEqual(code, 0)
        self.assertEqual(seen, [catalog.PICKER_URL])
        self.assertIn("Branches:", text)

    def test_out_of_range_firmware_number_fails_without_downloading(self):
        code, _ = self.run_main(["9"], argv=["--keyword", "soundbar"])
        self.assertEqual(code, 1)


class DownloadTests(unittest.TestCase):
    def test_download_writes_verified_length_and_skips_existing(self):
        firmware = Firmware("HW-Q800F", "Upgrade File", "1102", "1 MB", "Firmware_USB.zip", FM_URL)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(catalog.urllib.request, "urlopen", return_value=Response(b"abc")):
            with contextlib.redirect_stdout(io.StringIO()):
                target = catalog.download(firmware, Path(directory))
                self.assertEqual(target.read_bytes(), b"abc")
                again = catalog.download(firmware, Path(directory))
            self.assertEqual(again, target)

    def test_download_rejects_length_mismatch_and_leaves_no_part_file(self):
        firmware = Firmware("HW-Q800F", "Upgrade File", "1102", "1 MB", "Firmware_USB.zip", FM_URL)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(catalog.urllib.request, "urlopen", return_value=Response(b"abc", length=10)):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                catalog.download(firmware, Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_download_rejects_unsafe_filenames(self):
        firmware = Firmware("M", "t", "", "", "../evil.zip", FM_URL)
        with self.assertRaises(ValueError):
            catalog.download(firmware, Path("/tmp"))


if __name__ == "__main__":
    unittest.main()
