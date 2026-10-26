"""Export the existing artwork for the codex-pet.org uploader."""
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "plugins/saber-companion/pets/saber-knight"
SLUG = "saber-artoria"


def package_gallery(output_directory):
    output = Path(output_directory)
    directory = output / SLUG
    manifest = json.loads((PET / "pet.json").read_text(encoding="utf-8"))
    with Image.open(PET / manifest["spritesheetPath"]) as source:
        if source.mode != "RGBA" or source.size != (1536, 1872) or source.getextrema()[3] != (0, 255):
            raise ValueError("The gallery package requires the complete transparent v1 sheet.")
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "spritesheet.webp"
        source.save(target, format="WEBP", lossless=True, exact=True, method=6)
        with Image.open(target) as encoded:
            if encoded.convert("RGBA").tobytes() != source.tobytes():
                raise ValueError("WebP export changed the artwork pixels.")
    manifest.update(id=SLUG, spritesheetPath="spritesheet.webp",
                    description="Saber 骑士助手，包含召唤问候、挥剑与光屏检索、喝茶待机、举剑庆祝及异常求助等九种动作。")
    (directory / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = output / f"{SLUG}.codex-pet.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        for name in ("pet.json", "spritesheet.webp"):
            package.write(directory / name, arcname=name)
    return archive


if __name__ == "__main__":
    archive = package_gallery(ROOT / "output/gallery")
    print(f"Upload files: {archive.parent / SLUG}")
    print(f"Package: {archive}")
    print("Local export only: rebuilding does not update the public gallery page.")
