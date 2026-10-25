"""Pack generated keyframes into the native Codex v1 animation sheet."""
from contextlib import ExitStack
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "plugins/saber-companion/pets/saber-knight"


def pack_sheet(sources, layout):
    if len(sources) != len(layout["sources"]):
        raise ValueError("Source image and atlas counts differ.")
    poses = []
    for source, atlas in zip(sources, layout["sources"]):
        if source.mode != "RGBA" or source.getextrema()[3] != (0, 255):
            raise ValueError("Source needs genuine transparent and opaque RGBA pixels.")
        width, height = source.size
        columns, rows = atlas["columns"], atlas["rows"]
        if min(width / columns, height / rows) < 96 or abs(width / height / (columns / rows) - 1) > .05:
            raise ValueError("Source must match its readable equal-cell atlas grid.")
        for index in range(columns * rows):
            column, row = index % columns, index // columns
            pose = source.crop((round(column * width / columns), round(row * height / rows),
                                round((column + 1) * width / columns), round((row + 1) * height / rows)))
            bounds = pose.getchannel("A").point(lambda alpha: 255 if alpha >= 32 else 0).getbbox()
            if bounds is None:
                raise ValueError(f"Missing required pose: {atlas['path']} cell {index}")
            pose = pose.crop(bounds)
            # Normalize cell sizes before applying one shared character scale.
            normalize = 360 / (width / columns)
            poses.append(pose.resize((max(1, round(pose.width * normalize)),
                                      max(1, round(pose.height * normalize))), Image.Resampling.LANCZOS))
    scale = min(156 / max(p.width for p in poses), 170 / max(p.height for p in poses))
    poses = [p.resize((max(1, round(p.width * scale)), max(1, round(p.height * scale))),
                      Image.Resampling.LANCZOS) for p in poses]
    sheet = Image.new("RGBA", (layout["width"], layout["height"]))
    for animation in layout["animations"]:
        row = animation["row"]
        if len(animation["poses"]) != len(animation["durations"]):
            raise ValueError("Pose and duration counts differ.")
        # shortcut: held keyframes; draw in-betweens when smoother motion is needed.
        for column, pose_index in enumerate(animation["poses"]):
            if not 0 <= pose_index < len(poses):
                raise ValueError(f"Unknown pose index: {pose_index}")
            frame = poses[pose_index]
            offset_y = [0, -6, -14, -6, 0][column] if animation["state"] == "jumping" else 0
            x = column * layout["cellWidth"] + (layout["cellWidth"] - frame.width) // 2
            y = row * layout["cellHeight"] + 194 - frame.height + offset_y
            sheet.alpha_composite(
                frame, (x, y),
            )
    return sheet


if __name__ == "__main__":
    layout = json.loads((PET / "animation.json").read_text(encoding="utf-8"))
    with ExitStack() as stack:
        sources = [stack.enter_context(Image.open(ROOT / "plugins/saber-companion/assets" / atlas["path"]))
                   for atlas in layout["sources"]]
        sheet = pack_sheet(sources, layout)
    target = PET / "spritesheet.png"
    sheet.save(target)
    print(f"Packed {sum(len(a['durations']) for a in layout['animations'])} frames: {target}")
