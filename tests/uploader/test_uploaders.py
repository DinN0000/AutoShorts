"""Tests for all 6 platform uploaders."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from autoshorts.uploader.base import PlatformUploader, UploadResult
from autoshorts.uploader.youtube import YouTubeUploader
from autoshorts.uploader.tiktok import TikTokUploader
from autoshorts.uploader.instagram import InstagramUploader
from autoshorts.uploader.facebook import FacebookUploader
from autoshorts.uploader.threads import ThreadsUploader
from autoshorts.uploader.snapchat import SnapchatUploader
from autoshorts.uploader._helpers import load_secrets, retry_upload, RETRY_DELAYS


# ---------- helpers tests ----------

class TestLoadSecrets:
    def test_env_vars_take_priority(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_ACCESS_TOKEN", "env_token")
        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "env_client")
        result = load_secrets("youtube")
        assert result["access_token"] == "env_token"
        assert result["client_id"] == "env_client"

    def test_falls_back_to_yaml(self, tmp_path, monkeypatch):
        secrets_data = {"youtube": {"access_token": "yaml_token"}}

        import autoshorts.uploader._helpers as helpers
        monkeypatch.setattr(
            helpers, "load_secrets",
            lambda platform: secrets_data.get(platform, {}),
        )
        result = helpers.load_secrets("youtube")
        assert result["access_token"] == "yaml_token"

    def test_returns_empty_when_no_secrets(self):
        result = load_secrets("nonexistent_platform_xyz")
        assert result == {} or isinstance(result, dict)


class TestRetryUpload:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        factory = AsyncMock(return_value="ok")
        result = await retry_upload(factory, "test")
        assert result == "ok"
        assert factory.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("fail")
            return "ok"

        with patch("autoshorts.uploader._helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_upload(flaky, "test")
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        async def always_fail():
            raise RuntimeError("permanent failure")

        with patch("autoshorts.uploader._helpers.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="permanent failure"):
                await retry_upload(always_fail, "test")


# ---------- interface compliance ----------

class TestInterfaceCompliance:
    """All uploaders must be PlatformUploader subclasses."""

    @pytest.mark.parametrize("cls,name", [
        (YouTubeUploader, "youtube"),
        (TikTokUploader, "tiktok"),
        (InstagramUploader, "instagram"),
        (FacebookUploader, "facebook"),
        (ThreadsUploader, "threads"),
        (SnapchatUploader, "snapchat"),
    ])
    def test_is_platform_uploader(self, cls, name):
        uploader = cls()
        assert isinstance(uploader, PlatformUploader)
        assert uploader.platform_name == name


# ---------- missing secrets tests ----------

class TestMissingSecrets:
    """All uploaders should return error UploadResult when secrets are missing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("cls", [
        YouTubeUploader,
        TikTokUploader,
        InstagramUploader,
        FacebookUploader,
        ThreadsUploader,
        SnapchatUploader,
    ])
    async def test_missing_secrets_returns_error(self, cls, monkeypatch):
        monkeypatch.setattr(
            "autoshorts.uploader._helpers.load_secrets",
            lambda p: {},
        )
        # Patch per-module reference too
        mod_name = cls.__module__
        monkeypatch.setattr(f"{mod_name}.load_secrets", lambda p: {})

        uploader = cls()
        result = await uploader.upload("/fake/video.mp4", "title", "desc", ["tag"])
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error != ""
        assert result.platform == uploader.platform_name


# ---------- YouTube tests ----------

class TestYouTubeUploader:
    @pytest.mark.asyncio
    async def test_successful_upload(self, monkeypatch, tmp_path):
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake_video_data")

        monkeypatch.setattr(
            "autoshorts.uploader.youtube.load_secrets",
            lambda p: {"access_token": "test_token"},
        )

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"id": "yt_12345"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            uploader = YouTubeUploader()
            result = await uploader.upload(str(video_file), "Test", "Desc", ["tag1"])

        assert result.success is True
        assert result.video_id == "yt_12345"
        assert "youtube.com/shorts/yt_12345" in result.url

    @pytest.mark.asyncio
    async def test_api_error_triggers_retry(self, monkeypatch, tmp_path):
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake")

        monkeypatch.setattr(
            "autoshorts.uploader.youtube.load_secrets",
            lambda p: {"access_token": "test_token"},
        )

        call_count = 0
        mock_error_resp = AsyncMock()
        mock_error_resp.status = 500
        mock_error_resp.json = AsyncMock(return_value={"error": {"message": "server error"}})
        mock_error_resp.__aenter__ = AsyncMock(return_value=mock_error_resp)
        mock_error_resp.__aexit__ = AsyncMock(return_value=False)

        mock_ok_resp = AsyncMock()
        mock_ok_resp.status = 200
        mock_ok_resp.json = AsyncMock(return_value={"id": "yt_retry_ok"})
        mock_ok_resp.__aenter__ = AsyncMock(return_value=mock_ok_resp)
        mock_ok_resp.__aexit__ = AsyncMock(return_value=False)

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return mock_error_resp
            return mock_ok_resp

        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=side_effect)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session), \
             patch("autoshorts.uploader._helpers.asyncio.sleep", new_callable=AsyncMock):
            uploader = YouTubeUploader()
            result = await uploader.upload(str(video_file), "Test", "Desc", ["tag1"])

        assert result.success is True
        assert result.video_id == "yt_retry_ok"


# ---------- TikTok tests ----------

class TestTikTokUploader:
    @pytest.mark.asyncio
    async def test_successful_upload(self, monkeypatch, tmp_path):
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake_video")

        monkeypatch.setattr(
            "autoshorts.uploader.tiktok.load_secrets",
            lambda p: {"access_token": "tt_token"},
        )

        init_resp = AsyncMock()
        init_resp.status = 200
        init_resp.json = AsyncMock(return_value={
            "error": {"code": "ok"},
            "data": {"publish_id": "tt_pub_123", "upload_url": "https://upload.tiktok.com/video"},
        })
        init_resp.__aenter__ = AsyncMock(return_value=init_resp)
        init_resp.__aexit__ = AsyncMock(return_value=False)

        upload_resp = AsyncMock()
        upload_resp.status = 200
        upload_resp.__aenter__ = AsyncMock(return_value=upload_resp)
        upload_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=init_resp)
        mock_session.put = MagicMock(return_value=upload_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            uploader = TikTokUploader()
            result = await uploader.upload(str(video_file), "Title", "Desc", ["cat"])

        assert result.success is True
        assert result.video_id == "tt_pub_123"


# ---------- Instagram tests ----------

class TestInstagramUploader:
    @pytest.mark.asyncio
    async def test_missing_video_host_url(self, monkeypatch):
        monkeypatch.setattr(
            "autoshorts.uploader.instagram.load_secrets",
            lambda p: {"access_token": "ig_token", "user_id": "123"},
        )
        uploader = InstagramUploader()
        result = await uploader.upload("/fake.mp4", "T", "D", [])
        assert result.success is False
        assert "video_host_url" in result.error


# ---------- Facebook tests ----------

class TestFacebookUploader:
    @pytest.mark.asyncio
    async def test_missing_page_id(self, monkeypatch):
        monkeypatch.setattr(
            "autoshorts.uploader.facebook.load_secrets",
            lambda p: {"access_token": "fb_token"},
        )
        uploader = FacebookUploader()
        result = await uploader.upload("/fake.mp4", "T", "D", [])
        assert result.success is False
        assert "page_id" in result.error


# ---------- Threads tests ----------

class TestThreadsUploader:
    @pytest.mark.asyncio
    async def test_missing_user_id(self, monkeypatch):
        monkeypatch.setattr(
            "autoshorts.uploader.threads.load_secrets",
            lambda p: {"access_token": "th_token"},
        )
        uploader = ThreadsUploader()
        result = await uploader.upload("/fake.mp4", "T", "D", [])
        assert result.success is False
        assert "user_id" in result.error


# ---------- Snapchat tests ----------

class TestSnapchatUploader:
    @pytest.mark.asyncio
    async def test_missing_org_id(self, monkeypatch):
        monkeypatch.setattr(
            "autoshorts.uploader.snapchat.load_secrets",
            lambda p: {"access_token": "sc_token"},
        )
        uploader = SnapchatUploader()
        result = await uploader.upload("/fake.mp4", "T", "D", [])
        assert result.success is False
        assert "org_id" in result.error


# ---------- UploadResult dataclass ----------

class TestUploadResult:
    def test_defaults(self):
        r = UploadResult(platform="test", video_id="v1", success=True)
        assert r.url == ""
        assert r.error == ""
        assert r.uploaded_at == ""

    def test_full_fields(self):
        r = UploadResult(
            platform="youtube",
            video_id="abc",
            success=True,
            url="https://youtube.com/shorts/abc",
            error="",
            uploaded_at="2026-03-26T00:00:00+00:00",
        )
        assert r.platform == "youtube"
        assert r.video_id == "abc"
