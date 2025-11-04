from __future__ import annotations

import hashlib
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image

from bot.config import get_settings, ensure_data_dirs


@dataclass
class ItemCard:
    item_id: str
    title: str
    thumb_path: Path


def _user_items_dir(user_id: str) -> Path:
    settings = get_settings()
    ensure_data_dirs(settings)
    return Path(settings.DATA_DIR) / "items" / str(user_id)


def list_user_items(user_id: str) -> List[ItemCard]:
    base = _user_items_dir(user_id)
    if not base.exists():
        return []
    cards: List[ItemCard] = []
    for item_dir in sorted(base.iterdir()):
        if not item_dir.is_dir():
            continue
        thumb = item_dir / "thumb.jpg"
        title_file = item_dir / "title.txt"
        title = title_file.read_text(encoding="utf-8").strip() if title_file.exists() else "Вещь"
        if thumb.exists():
            cards.append(ItemCard(item_id=item_dir.name, title=title, thumb_path=thumb))
    return cards


def save_item_photo(user_id: str, photo_bytes: bytes, suggested_title: str | None = None) -> str:
    """
    Save uploaded item photo and produce a thumbnail. Returns item_id.
    """
    item_id = str(uuid.uuid4())
    item_dir = _user_items_dir(user_id) / item_id
    item_dir.mkdir(parents=True, exist_ok=True)

    # Save original
    orig_path = item_dir / "source.jpg"
    with open(orig_path, "wb") as f:
        f.write(photo_bytes)

    # Compute checksum
    checksum = hashlib.sha256(photo_bytes).hexdigest()
    (item_dir / "checksum.sha256").write_text(checksum, encoding="utf-8")

    # Create thumbnail
    thumb_path = item_dir / "thumb.jpg"
    try:
        with Image.open(orig_path) as im:
            im = im.convert("RGB")
            im.thumbnail((512, 512))
            im.save(thumb_path, format="JPEG", quality=88)
    except Exception:
        # Fallback: copy original if PIL fails
        thumb_path.write_bytes(orig_path.read_bytes())

    title = suggested_title or "Вещь"
    (item_dir / "title.txt").write_text(title, encoding="utf-8")

    return item_id


