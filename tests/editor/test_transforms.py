"""Tests for editor transforms module."""

from autoshorts.editor.transforms import EditConfig, build_ffmpeg_filters


def test_build_filters_with_all_transforms():
    config = EditConfig(
        speed_factor=2.0,
        flip_horizontal=True,
        crop_percent=0.1,
        color_brightness=0.2,
        color_contrast=1.3,
        color_saturation=0.8,
        zoom_factor=1.2,
    )
    result = build_ffmpeg_filters(config)
    assert "setpts=" in result
    assert "hflip" in result
    assert "crop=" in result
    assert "eq=" in result
    assert "brightness=" in result
    assert "contrast=" in result
    assert "saturation=" in result
    assert "zoompan=" in result


def test_build_filters_minimal():
    config = EditConfig(speed_factor=1.0)
    result = build_ffmpeg_filters(config)
    assert "setpts" not in result


def test_edit_config_visual_changes_list():
    config = EditConfig(
        speed_factor=1.5,
        flip_horizontal=True,
        color_brightness=0.1,
    )
    changes = config.visual_changes()
    assert "speed" in changes
    assert "flip" in changes
    assert "color" in changes
    assert "crop" not in changes
    assert "zoom" not in changes
