import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import pytest

from valifold.errors import ValifoldError


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def create_files():
    def _create(root: Path, structure: dict):
        for key, value in structure.items():
            new_path = root / key

            if value is None:
                new_path.touch()

            if isinstance(value, dict):
                new_path.mkdir(parents=True, exist_ok=True)

                _create(new_path, value)

    return _create


@pytest.fixture
def validate_errors():
    def inner(result: list[ValifoldError], *expected: tuple[type[ValifoldError], Iterable[str]]):
        expected_mapping = defaultdict(list)

        for error_type, names in expected:
            expected_mapping[error_type].append(set(names))

        for error in result:
            error_type = type(error)

            assert error_type in expected_mapping

            error_names = [path.name for path in error.paths]

            names_sets = expected_mapping[error_type]

            found_good_set = False

            for expected_names in names_sets:
                if not expected_names.symmetric_difference(error_names):
                    names_sets.remove(expected_names)

                    found_good_set = True

                    break

            assert found_good_set, f"No matching names for {error_type.__name__} with names: {', '.join(error_names)}"

        missed_errors = []

        for error_type, file_names in expected_mapping.items():
            if file_names:
                missed_errors.append(error_type.__name__)

        assert not missed_errors, f"Some expected errors were not found: {', '.join(missed_errors)}"

    return inner
