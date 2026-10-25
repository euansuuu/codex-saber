import importlib.util
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/saber-companion"
PET = PLUGIN / "pets/saber-knight"
spec = importlib.util.spec_from_file_location("build_pet", ROOT / "tools/build_pet.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class LocalPackageTests(unittest.TestCase):
    def test_marketplace_resolves_packaged_plugin(self):
        market = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        entry = market["plugins"][0]
        path = (ROOT / entry["source"]["path"]).resolve()
        self.assertTrue(path.is_relative_to(ROOT))
        manifest = json.loads((path / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual({p.parent.name for p in (path / "skills").glob("*/SKILL.md")},
                         {"saber", "saber-setup"})

    def test_native_sheet_has_complete_frames_and_clear_gutters(self):
        layout = json.loads((PET / "animation.json").read_text(encoding="utf-8"))
        manifest = json.loads((PET / "pet.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["spriteVersionNumber"], layout["version"])
        with Image.open(PET / manifest["spritesheetPath"]) as sheet:
            self.assertEqual(sheet.size, (1536, 1872))
            self.assertEqual(sheet.mode, "RGBA")
            self.assertEqual([len(a["durations"]) for a in layout["animations"]],
                             [6, 8, 8, 4, 5, 8, 6, 6, 6])
            for animation in layout["animations"]:
                row = animation["row"]
                for column in range(8):
                    cell = sheet.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208))
                    bounds = cell.getchannel("A").getbbox()
                    if column >= len(animation["durations"]):
                        self.assertIsNone(bounds)
                    else:
                        self.assertIsNotNone(bounds)
                        self.assertGreaterEqual(bounds[0], 8)
                        self.assertGreaterEqual(bounds[1], 8)
                        self.assertLessEqual(bounds[2], 184)
                        self.assertLessEqual(bounds[3], 200)

    def test_builder_rejects_opaque_art(self):
        layout = json.loads((PET / "animation.json").read_text(encoding="utf-8"))
        sources = [Image.new("RGBA", (atlas["columns"] * 100, atlas["rows"] * 100), "white")
                   for atlas in layout["sources"]]
        with self.assertRaises(ValueError):
            builder.pack_sheet(sources, layout)

    def test_builder_reproduces_sheet_with_distinct_original_actions(self):
        layout = json.loads((PET / "animation.json").read_text(encoding="utf-8"))
        with ExitStack() as stack:
            sources = [stack.enter_context(Image.open(PLUGIN / "assets" / atlas["path"]))
                       for atlas in layout["sources"]]
            rebuilt = builder.pack_sheet(sources, layout)
            packaged = stack.enter_context(Image.open(PET / "spritesheet.png"))
            self.assertEqual(rebuilt.tobytes(), packaged.tobytes())
        for state in ("idle", "waving", "failed", "waiting", "running", "review"):
            animation = next(a for a in layout["animations"] if a["state"] == state)
            row = animation["row"]
            frames = {rebuilt.crop((c * 192, row * 208, (c + 1) * 192, (row + 1) * 208)).tobytes()
                      for c in range(len(animation["durations"]))}
            self.assertGreaterEqual(len(frames), 4, state)
        running = next(a for a in layout["animations"] if a["state"] == "running")
        self.assertTrue(set(running["poses"]) & set(range(20, 24)), "Missing sword execution")
        self.assertTrue(set(running["poses"]) & set(range(24, 28)), "Missing search screens")
        used = {pose for a in layout["animations"] for pose in a["poses"]}
        self.assertTrue(set(range(12, 36)) <= used, "An original-design keyframe is never played")

    def test_builder_rejects_missing_keyframes(self):
        layout = json.loads((PET / "animation.json").read_text(encoding="utf-8"))
        with ExitStack() as stack:
            sources = [stack.enter_context(Image.open(PLUGIN / "assets" / atlas["path"]))
                       for atlas in layout["sources"]]
            sources[-1] = sources[-1].copy()
            width, height = sources[-1].size
            sources[-1].paste((0, 0, 0, 0), (round(width / 2), round(height / 2), width, height))
            with self.assertRaisesRegex(ValueError, "Missing required pose"):
                builder.pack_sheet(sources, layout)

    def test_pet_install_is_idempotent_and_preserves_edits(self):
        with tempfile.TemporaryDirectory(prefix="saber-pet-") as directory:
            command = ["powershell.exe", "-NoProfile", "-File", str(PLUGIN / "scripts/install-pet.ps1"),
                       "-CodexDirectory", directory]
            for _ in range(2):
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            target = Path(directory) / "pets/saber-knight/pet.json"
            self.assertEqual(target.read_bytes(), (PET / "pet.json").read_bytes())
            changed = target.read_bytes() + b"\n"
            target.write_bytes(changed)
            outcome = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(outcome.returncode, 0)
            self.assertEqual(target.read_bytes(), changed)

    def test_pet_upgrade_backs_up_old_files_before_replacing(self):
        with tempfile.TemporaryDirectory(prefix="saber-upgrade-") as directory:
            target = Path(directory) / "pets/saber-knight"
            target.mkdir(parents=True)
            old = {"pet.json": b'{"displayName":"my old Saber"}',
                   "spritesheet.png": b"previous or customized sheet"}
            for name, contents in old.items():
                (target / name).write_bytes(contents)
            command = ["powershell.exe", "-NoProfile", "-File", str(PLUGIN / "scripts/install-pet.ps1"),
                       "-CodexDirectory", directory, "-Upgrade"]
            for _ in range(2):
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            backups = list((Path(directory) / "pets-backups/saber-knight").iterdir())
            self.assertEqual(len(backups), 1, "Unchanged installs should not create another backup")
            for name, contents in old.items():
                self.assertEqual((backups[0] / name).read_bytes(), contents)
                self.assertEqual((target / name).read_bytes(), (PET / name).read_bytes())

    def test_install_reports_cloud_migration_instead_of_claiming_refresh_is_enough(self):
        with tempfile.TemporaryDirectory(prefix="saber-cloud-") as directory:
            state = {"electron-persisted-atom-state": {
                "migrated-cloud-pet-ids-v1": {"test-account": {"custom:saber-knight": "pet_test"}}}}
            (Path(directory) / ".codex-global-state.json").write_text(json.dumps(state), encoding="utf-8")
            command = ["powershell.exe", "-NoProfile", "-File", str(PLUGIN / "scripts/install-pet.ps1"),
                       "-CodexDirectory", directory]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Refresh does not replace cloud artwork", result.stdout)
            self.assertIn("saber-companion:saber-setup", result.stdout)
            self.assertEqual(json.loads((Path(directory) / ".codex-global-state.json").read_text()), state)

    def test_codex_installs_local_plugin_in_isolated_profile(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is needed to run the installed Codex CLI")
        cli = Path(node).parent / "node_modules/@openai/codex/bin/codex.js"
        self.assertTrue(cli.is_file(), "Expected the existing npm Codex installation")
        with tempfile.TemporaryDirectory(prefix="saber-codex-") as directory:
            environment = dict(os.environ, CODEX_HOME=directory)

            def run(*arguments):
                result = subprocess.run([node, str(cli), *arguments], env=environment, cwd=ROOT,
                                        capture_output=True, text=True, encoding="utf-8", timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)

            market = run("plugin", "marketplace", "add", str(ROOT), "--json")
            self.assertEqual(market["marketplaceName"], "saber-local")
            installed = run("plugin", "add", "saber-companion@saber-local", "--json")
            self.assertEqual(installed["pluginId"], "saber-companion@saber-local")
            cached = Path(installed["installedPath"])
            self.assertTrue((cached / "skills/saber/SKILL.md").is_file())
            self.assertEqual((cached / "pets/saber-knight/spritesheet.png").read_bytes(),
                             (PET / "spritesheet.png").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
