import tempfile
from pathlib import Path

import pytest

from valifold.errors import MandatoryMissedError
from valifold.dsl import file
from valifold.pattern import w


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_file_exists(temp_dir):
    name = "test.txt"

    test_file = temp_dir / name
    test_file.touch()

    struct = file(w(name))

    assert not struct.validate_as_root(test_file)


def test_file_doesnt_exist_mandatory(temp_dir):
    name = "test.txt"

    test_file = temp_dir / name

    struct = file(w(name))

    result = struct.validate_as_root(test_file)

    assert result
    assert any(isinstance(error, MandatoryMissedError) for error in result)


def test_file_doesnt_exist_optional(temp_dir):
    name = "test.txt"

    test_file = temp_dir / name

    struct = file(
        w(name),
        is_optional=True
    )

    assert not struct.validate_as_root(test_file)
