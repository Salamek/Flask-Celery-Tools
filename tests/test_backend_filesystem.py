"""Test backend."""

import tempfile
from pathlib import Path

import pytest

from flask_celery.backends.filesystem import LockBackendFilesystem


def get_tempdir(name: str="path_exists_dir") -> Path:
    """Return temp dir path."""
    return Path(tempfile.gettempdir().replace("\\", "/")).joinpath(name)


def test_filesystem_path_exists() -> None:
    """Test Not failing when path exists."""
    path = get_tempdir()
    if not path.is_dir():
        path.mkdir()
    LockBackendFilesystem(f"file://{path}")


def test_filesystem_path_exists_file() -> None:
    """Test Failing when path exists and it is a file."""
    path = get_tempdir("path_exists_file")
    with path.open("w") as f:
        f.write("exists")
    with pytest.raises(FileExistsError):
        LockBackendFilesystem(f"file://{path}")


def test_filesystem_acquire_exists_empty_file() -> None:
    """Test Creation of correct lock file when empty one exists."""
    path = get_tempdir()
    lb = LockBackendFilesystem(f"file://{path}")
    with lb.get_lock_path("identifier").open("w") as f:
        f.write("")

    assert lb.acquire("identifier", 0) is True


def test_filesystem_release_file_not_found() -> None:
    """Test release of non existing lock."""
    path = get_tempdir()
    lb = LockBackendFilesystem(f"file://{path}")
    lb.release("not_found_file")


def test_filesystem_release_file_is_not_a_file() -> None:
    """Test release of non-file file."""
    path = get_tempdir()
    lb = LockBackendFilesystem(f"file://{path}")

    dir_path = lb.get_lock_path("not_a_file")

    if not dir_path.is_dir():
        dir_path.mkdir()

    with pytest.raises(IsADirectoryError):
        lb.release("not_a_file")


def test_filesystem_exists_exists_empty_file() -> None:
    """Test Creation of correct lock file when empty one exists."""
    path = get_tempdir()
    lb = LockBackendFilesystem(f"file://{path}")
    with lb.get_lock_path("identifier").open("w") as f:
        f.write("")

    assert lb.exists("identifier", 0) is False
