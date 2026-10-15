"""Shrinks the card art for the game: `frontend/src/assets/cards/NN.webp` (the
designer's full-size exports, kept out of Git) -> `frontend/src/assets/cards/web/NN.webp`
(800 px wide, lossy WebP quality 82; what the app imports).

Usage: python tools/optimize_card_images.py [source_dir] [target_dir]
"""

import sys
from pathlib import Path

from PIL import Image

WIDTH = 800
QUALITY = 82


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("frontend/src/assets/cards")
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else source / "web"
    target.mkdir(parents=True, exist_ok=True)
    total_in = total_out = count = 0
    for path in sorted(source.glob("[0-9]*.webp")):
        image = Image.open(path).convert("RGB")
        height = round(image.height * WIDTH / image.width)
        image = image.resize((WIDTH, height), Image.LANCZOS)
        out = target / path.name
        image.save(out, "WEBP", quality=QUALITY, method=6)
        total_in += path.stat().st_size
        total_out += out.stat().st_size
        count += 1
    print(f"{count} cards: {total_in // 1024} KB -> {total_out // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
