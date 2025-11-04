from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ImageRole(str, Enum):
    source = "source"
    background_removed = "background_removed"
    enhanced = "enhanced"
    aligned = "aligned"
    depth_map = "depth_map"


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class ImageRef(BaseModel):
    id: str = Field(description="uuid4")
    path: str = Field(description="relative path inside DATA_DIR or s3 uri")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    mime_type: str = Field(pattern="^image/")
    checksum_sha256: str = Field(min_length=64, max_length=64)
    role: ImageRole = ImageRole.source
    has_ruler: bool = False
    ruler_length_cm: Optional[float] = Field(default=None, gt=0)
    ruler_bbox: Optional[BoundingBox] = None
    exif_removed: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GarmentMeasurements(BaseModel):
    chest_cm: Optional[float] = Field(default=None, gt=0)
    waist_cm: Optional[float] = Field(default=None, gt=0)
    hips_cm: Optional[float] = Field(default=None, gt=0)
    length_cm: Optional[float] = Field(default=None, gt=0)
    sleeve_cm: Optional[float] = Field(default=None, gt=0)
    shoulder_cm: Optional[float] = Field(default=None, gt=0)
    inseam_cm: Optional[float] = Field(default=None, gt=0)
    scale_ppm: Optional[float] = Field(default=None, gt=0, description="pixels per millimeter")


class ItemMetadata(BaseModel):
    item_id: str
    user_id: str
    category: str = Field(description="e.g. tshirt, hoodie, pants, dress")
    size_system: Optional[str] = Field(default="INT", description="INT|EU|US|RU ...")
    measurements: GarmentMeasurements = Field(default_factory=GarmentMeasurements)
    source_images: List[ImageRef] = Field(default_factory=list)
    processed_images: List[ImageRef] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


