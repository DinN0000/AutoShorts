"""FFmpeg filter builder and edit configuration."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class EditConfig:
    speed_factor: float = 1.0
    flip_horizontal: bool = False
    crop_percent: float = 0.0
    color_brightness: float = 0.0
    color_contrast: float = 1.0
    color_saturation: float = 1.0
    zoom_factor: float = 1.0

    def visual_changes(self) -> list[str]:
        """Returns list of change names based on non-default values."""
        changes: list[str] = []
        if self.speed_factor != 1.0:
            changes.append("speed")
        if self.flip_horizontal:
            changes.append("flip")
        if self.crop_percent != 0.0:
            changes.append("crop")
        if (
            self.color_brightness != 0.0
            or self.color_contrast != 1.0
            or self.color_saturation != 1.0
        ):
            changes.append("color")
        if self.zoom_factor != 1.0:
            changes.append("zoom")
        return changes

    @classmethod
    def random_strong(cls) -> EditConfig:
        """Random config with strong transformations."""
        return cls(
            speed_factor=random.uniform(0.5, 2.0),
            flip_horizontal=random.choice([True, False]),
            crop_percent=random.uniform(0.05, 0.2),
            color_brightness=random.uniform(-0.3, 0.3),
            color_contrast=random.uniform(0.7, 1.5),
            color_saturation=random.uniform(0.5, 1.5),
            zoom_factor=random.uniform(1.0, 1.5),
        )


def build_ffmpeg_filters(config: EditConfig) -> str:
    """Build a comma-joined string of FFmpeg video filters from config."""
    filters: list[str] = []

    if config.speed_factor != 1.0:
        pts = 1.0 / config.speed_factor
        filters.append(f"setpts={pts}*PTS")

    if config.flip_horizontal:
        filters.append("hflip")

    if config.crop_percent != 0.0:
        pct = 1 - config.crop_percent
        filters.append(f"crop=iw*{pct}:ih*{pct}")

    if (
        config.color_brightness != 0.0
        or config.color_contrast != 1.0
        or config.color_saturation != 1.0
    ):
        filters.append(
            f"eq=brightness={config.color_brightness}"
            f":contrast={config.color_contrast}"
            f":saturation={config.color_saturation}"
        )

    if config.zoom_factor != 1.0:
        filters.append(
            f"zoompan=z={config.zoom_factor}:d=1:s=1080x1920"
        )

    return ",".join(filters)
