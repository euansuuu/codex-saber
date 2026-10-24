"""Assemble generated poses into a Codex v1 animation sheet."""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "plugins/saber-companion/pets/saber-knight"


def pack_sheet(source, layout):
    if source.mode != "RGBA" or source.getextrema()[3] != (0, 255):
        raise ValueError("Source needs genuine transparent and opaque RGBA pixels.")
    width, height = source.size
    if width < 96 or height < 128 or abs(width / height / 0.75 - 1) > 0.05:
        raise ValueError("Source must be a readable 3 by 4 pose atlas.")
    poses = []
    for index in range(12):
        column, row = index % 3, index // 3
        pose = source.crop((round(column * width / 3), round(row * height / 4),
                            round((column + 1) * width / 3), round((row + 1) * height / 4)))
        bounds = pose.getchannel("A").point(lambda alpha: 255 if alpha >= 32 else 0).getbbox()
        if bounds is None:
            raise ValueError(f"Missing required pose: {index}")
        poses.append(pose.crop(bounds))
    scale = min(156 / max(p.width for p in poses), 170 / max(p.height for p in poses))
    poses = [p.resize((max(1, round(p.width * scale)), max(1, round(p.height * scale))),
                      Image.Resampling.LANCZOS) for p in poses]
    sheet = Image.new("RGBA", (layout["width"], layout["height"]))
    for animation in layout["animations"]:
        row = animation["row"]
        if len(animation["poses"]) != len(animation["durations"]):
            raise ValueError("Pose and duration counts differ.")
        for column, pose_index in enumerate(animation["poses"]):
            frame = poses[pose_index]
            phase = column / len(animation["poses"]) * math.tau
            offset_y = round(math.sin(phase) * 2)
            if animation["state"] == "jumping":
                offset_y = [0, -6, -14, -6, 0][column]
            elif animation["state"] == "failed":
                frame = frame.rotate(math.sin(phase) * 2, Image.Resampling.BICUBIC, expand=True)
            # shortcut: pose swaps and small transforms; use drawn in-betweens for richer motion.
            x = column * layout["cellWidth"] + (layout["cellWidth"] - frame.width) // 2
            y = row * layout["cellHeight"] + 194 - frame.height + offset_y
            sheet.alpha_composite(
                frame, (x, y),
            )
    return sheet


if __name__ == "__main__":
    layout = json.loads((PET / "animation.json").read_text(encoding="utf-8"))
    source_path = ROOT / "plugins/saber-companion/assets/saber-poses-source.png"
    with Image.open(source_path) as source:
        sheet = pack_sheet(source, layout)
    target = PET / "spritesheet.png"
    sheet.save(target)
    print(f"Packed {sum(len(a['durations']) for a in layout['animations'])} frames: {target}")
