"""Test backend."""

import os
import posixpath
import tempfile

import pytest

from flask_celery.backends.filesystem import LockBackendFilesystem


def get_tempdir(name='path_exists_dir'):
    """Return temp dir path."""
    return posixpath.join(tempfile.gettempdir().replace('\\', '/'), name)


def test_filesystem_path_exists():
    """Test Not failing when path exists."""
    path = get_tempdir()
    if not os.path.isdir(path):
        os.mkdir(path)
    LockBackendFilesystem('file://{}'.format(path))


def test_filesystem_path_exists_file():
    """Test Failing when path exists and it is a file."""
    path = get_tempdir('path_exists_file')
    with open(path, 'w') as f:
        f.write('exists')
    with pytest.raises(OSError):
        LockBackendFilesystem('file://{}'.format(path))


def test_filesystem_acquire_exists_empty_file():
    """Test Creation of correct lock file when empty one exists."""
    path = get_tempdir()
    lb = LockBackendFilesystem('file://{}'.format(path))
    with open(lb.get_lock_path('identifier'), 'w') as f:
        f.write('')

    assert lb.acquire('identifier', 0) is True


def test_filesystem_release_file_not_found():
    """Test release of non existing lock."""
    path = get_tempdir()
    lb = LockBackendFilesystem('file://{}'.format(path))
    lb.release('not_found_file')


def test_filesystem_release_file_is_not_a_file():
    """Test release of non-file file."""
    path = get_tempdir()
    lb = LockBackendFilesystem('file://{}'.format(path))

    dir_path = lb.get_lock_path('not_a_file')

    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    with pytest.raises(OSError):
        lb.release('not_a_file')


def test_filesystem_exists_exists_empty_file():
    """Test Creation of correct lock file when empty one exists."""
    path = get_tempdir()
    lb = LockBackendFilesystem('file://{}'.format(path))
    with open(lb.get_lock_path('identifier'), 'w') as f:
        f.write('')

    assert lb.exists('identifier', 0) is False
