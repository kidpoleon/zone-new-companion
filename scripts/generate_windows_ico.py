from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def generate_windows_icon() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    icon_dir = repo_root / "zone_new_companion" / "icon"
    icon_dir.mkdir(parents=True, exist_ok=True)

    bg = (37, 48, 70, 255)
    fg = (0, 223, 255, 255)
    accent = (154, 170, 200, 255)

    def draw_icon(size: int) -> Image.Image:
        img = Image.new("RGBA", (size, size), bg)
        draw = ImageDraw.Draw(img)
        margin = int(size * 0.12)

        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=int(size * 0.18),
            outline=fg,
            width=max(2, size // 32),
        )

        stroke = max(6, size // 10)
        y1 = int(size * 0.25)
        y2 = int(size * 0.75)
        x1 = int(size * 0.30)
        x2 = int(size * 0.70)
        draw.line([x1, y1, x2, y1], fill=fg, width=stroke)
        draw.line([x1, y1, x2, y2], fill=fg, width=stroke)
        draw.line([x2, y2, x1, y2], fill=fg, width=stroke)

        r = max(3, size // 24)
        cx, cy = int(size * 0.80), int(size * 0.20)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)
        return img

    ico_path = icon_dir / "app.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]
    images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])


if __name__ == "__main__":
    generate_windows_icon()
