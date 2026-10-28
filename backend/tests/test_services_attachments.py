from __future__ import annotations

import io
from pathlib import Path

import pytest

from backend.app.services.attachments import AttachmentError, AttachmentService

pytestmark = pytest.mark.anyio


class FakeUpload:
    def __init__(
        self,
        filename: str | None,
        data: bytes = b"",
        content_type: str | None = None,
    ) -> None:
        self.filename = filename
        self.content_type = content_type
        self._buffer = io.BytesIO(data)
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    async def close(self) -> None:
        self.closed = True


class BrokenUpload(FakeUpload):
    async def read(self, size: int = -1) -> bytes:
        raise RuntimeError("disk exploded")


@pytest.fixture
def service(tmp_path) -> AttachmentService:
    return AttachmentService(upload_dir=tmp_path)


async def test_save_upload_stores_safe_filename_and_size(service):
    upload = FakeUpload(
        "../../notes.txt",
        b"hello attachment",
        "text/plain",
    )

    stored = await service.save_upload(upload, 7)

    assert stored.original_filename == "notes.txt"
    assert stored.content_type == "text/plain"
    assert stored.file_size == 16
    assert stored.extension == ".txt"
    assert stored.stored_filename.endswith(".txt")
    path = service.path_for(7, stored.stored_filename)
    assert path.is_file()
    assert path.read_bytes() == b"hello attachment"
    assert upload.closed is True


async def test_save_upload_guesses_content_type(service):
    upload = FakeUpload("notes.md", b"# Notes", None)

    stored = await service.save_upload(upload, 1)

    assert stored.content_type.startswith("text/")


async def test_save_upload_rejects_missing_name_and_bad_extensions(service):
    with pytest.raises(AttachmentError, match="filename is required") as missing:
        await service.save_upload(FakeUpload(""), 1)
    assert missing.value.status_code == 400

    with pytest.raises(AttachmentError, match="not supported") as unsupported:
        await service.save_upload(FakeUpload("malware.exe", b"x"), 1)
    assert unsupported.value.status_code == 415

    with pytest.raises(AttachmentError, match="does not match") as mismatch:
        await service.save_upload(
            FakeUpload("photo.png", b"x", "text/plain"),
            1,
        )
    assert mismatch.value.status_code == 415


async def test_save_upload_accepts_image_with_octet_stream(service):
    upload = FakeUpload("photo.png", b"png", "application/octet-stream")

    stored = await service.save_upload(upload, 1)

    assert stored.content_type == "application/octet-stream"
    assert service.path_for(1, stored.stored_filename).is_file()


async def test_save_upload_rejects_empty_and_oversized_files(service, monkeypatch):
    with pytest.raises(AttachmentError, match="empty") as empty:
        await service.save_upload(FakeUpload("empty.txt", b""), 1)
    assert empty.value.status_code == 400

    monkeypatch.setattr(
        "backend.app.services.attachments.settings.max_upload_size",
        4,
    )
    with pytest.raises(AttachmentError, match="too large") as oversized:
        await service.save_upload(FakeUpload("large.txt", b"12345"), 1)
    assert oversized.value.status_code == 413

    directory = service.upload_dir / "1"
    assert not directory.exists() or not any(directory.iterdir())


async def test_save_upload_handles_unexpected_write_failure(service):
    with pytest.raises(AttachmentError, match="could not be stored") as failure:
        await service.save_upload(BrokenUpload("notes.txt", b"data"), 1)
    assert failure.value.status_code == 500


def test_path_for_uses_only_final_component(service):
    path = service.path_for(3, "../../etc/passwd")

    assert path == service.upload_dir / "3" / "passwd"


def test_delete_file_tolerates_missing_and_os_errors(service, monkeypatch):
    service.delete_file(1, "missing.txt")

    monkeypatch.setattr(
        Path,
        "unlink",
        lambda self, missing_ok=False: (_ for _ in ()).throw(OSError("no")),
    )
    service.delete_file(1, "whatever.txt")


def test_delete_conversation_files_removes_directory(service):
    directory = service.upload_dir / "9"
    directory.mkdir(parents=True)
    (directory / "file.txt").write_text("data", encoding="utf-8")

    service.delete_conversation_files(9)

    assert not directory.exists()
    service.delete_conversation_files(9)


async def test_extract_text_for_text_and_unknown_files(service):
    directory = service.upload_dir / "2"
    directory.mkdir(parents=True)
    (directory / "notes.txt").write_text("hello", encoding="utf-8")
    (directory / "image.png").write_bytes(b"png")

    assert await service.extract_text(2, "notes.txt", "notes.txt") == "hello"
    assert await service.extract_text(2, "image.png", "image.png") == ""
    assert await service.extract_text(2, "missing.txt", "missing.txt") == ""


async def test_extract_text_handles_read_errors(service, monkeypatch):
    directory = service.upload_dir / "2"
    directory.mkdir(parents=True)
    (directory / "notes.txt").write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(OSError("no")),
    )

    assert await service.extract_text(2, "notes.txt", "notes.txt") == ""


async def test_extract_text_reads_pdf_pages(service, monkeypatch):
    directory = service.upload_dir / "4"
    directory.mkdir(parents=True)
    (directory / "doc.pdf").write_bytes(b"%PDF-1.4")

    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def extract_text(self) -> str:
            return self.text

    class FakeReader:
        def __init__(self, path: str) -> None:
            self.pages = [FakePage("Page one."), FakePage("Page two.")]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)

    text = await service.extract_text(4, "doc.pdf", "doc.pdf")

    assert "Page one." in text
    assert "Page two." in text


async def test_extract_text_handles_invalid_pdf(service):
    directory = service.upload_dir / "4"
    directory.mkdir(parents=True)
    (directory / "bad.pdf").write_bytes(b"not a pdf")

    assert await service.extract_text(4, "bad.pdf", "bad.pdf") == ""


async def test_build_context_includes_text_and_placeholders(service):
    directory = service.upload_dir / "5"
    directory.mkdir(parents=True)
    (directory / "notes.txt").write_text("log content", encoding="utf-8")

    context = await service.build_context(
        [
            (5, "notes.txt", "notes.txt", "text/plain"),
            (5, "photo.png", "missing.png", "image/png"),
        ]
    )

    assert context.startswith("\n\n--- Attached file: notes.txt ---")
    assert "log content" in context
    assert "[Attached file: photo.png (image/png)." in context
    assert "No text preview is available." in context


async def test_build_context_is_bounded(service, monkeypatch):
    directory = service.upload_dir / "6"
    directory.mkdir(parents=True)
    (directory / "one.txt").write_text("abcdef", encoding="utf-8")
    (directory / "two.txt").write_text("ghijkl", encoding="utf-8")

    monkeypatch.setattr(
        "backend.app.services.attachments.settings.max_attachment_text_chars",
        5,
    )

    context = await service.build_context(
        [
            (6, "one.txt", "one.txt", "text/plain"),
            (6, "two.txt", "two.txt", "text/plain"),
        ]
    )

    assert "abcde" in context
    assert "ghijkl" not in context


async def test_build_context_empty(service):
    assert await service.build_context([]) == ""
