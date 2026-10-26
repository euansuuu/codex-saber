import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_gallery", ROOT / "tools/package_gallery.py")
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)


class GalleryPackageTests(unittest.TestCase):
    def test_package_has_installer_files_and_preserves_every_pixel(self):
        with tempfile.TemporaryDirectory(prefix="saber-gallery-") as temporary:
            archive = gallery.package_gallery(temporary)
            with ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), {"pet.json", "spritesheet.webp"})
                manifest = json.loads(package.read("pet.json"))
                self.assertEqual(manifest["id"], "saber-artoria")
                self.assertEqual(manifest["spritesheetPath"], "spritesheet.webp")
                self.assertEqual(manifest["spriteVersionNumber"], 1)
                self.assertEqual(package.read("spritesheet.webp"),
                                 (Path(temporary) / "saber-artoria/spritesheet.webp").read_bytes())
            with Image.open(gallery.PET / "spritesheet.png") as source, \
                    Image.open(Path(temporary) / "saber-artoria/spritesheet.webp") as exported:
                self.assertEqual(source.size, exported.size)
                self.assertEqual(source.tobytes(), exported.convert("RGBA").tobytes())

    def test_opaque_source_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory(prefix="saber-gallery-invalid-") as temporary:
            source = Path(temporary)
            (source / "pet.json").write_text('{"spritesheetPath":"spritesheet.png"}')
            Image.new("RGBA", (1536, 1872), "white").save(source / "spritesheet.png")
            with patch.object(gallery, "PET", source), self.assertRaises(ValueError):
                gallery.package_gallery(source / "export")
            self.assertFalse((source / "export").exists())
