import string
import tempfile
from collections import defaultdict
from enum import Enum, auto
from itertools import product, repeat
from pathlib import Path
from typing import Iterable

import pytest

from valifold.dsl import file, folder, sidecar, xor, only_one, at_least_one, anything
from valifold.errors import (
    MandatoryMissedError,
    NotFileError,
    NotDirectoryError,
    ExtraItemsError,
    FewOptionsError,
    NoSidecarError,
    AllValidationsFailedError,
    ManyOptionsError,
    ValifoldError,
)
from valifold.pattern import w, r
from valifold.validators import XorValidator

MANY = 50
VERY_MANY = 100


# ============ ФИКСТУРЫ ============


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


# class ValidateErrorStrategy(Enum):
#     STRICT = auto()
#     ACTUAL_IN_EXPECTED = auto()
#     EXPECTED_IN_ACTUAL = auto()
#
#     def __call__(self, expected: set[str], actual: set[str]) -> set[str]:
#         if self == ValidateErrorStrategy.STRICT:
#             return expected.symmetric_difference(actual)
#         elif self == ValidateErrorStrategy.ACTUAL_IN_EXPECTED:
#             return expected.intersection(actual)
#         elif self == ValidateErrorStrategy.EXPECTED_IN_ACTUAL:


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

            assert found_good_set, f"No matching names for {error_type.__name__} with names: {", ".join(error_names)}"

        missed_errors = []

        for error_type, file_names in expected_mapping.items():
            if file_names:
                missed_errors.append(error_type.__name__)

        assert not missed_errors, f"Some expected errors were not found: {", ".join(missed_errors)}"

    return inner


# @pytest.fixture
# def standard_project_structure(temp_dir, create_files):
#     """Стандартная структура Python-проекта для переиспользования в нескольких тестах."""
#     create_files(temp_dir, {
#         'README.md': None,
#         'requirements.txt': None,
#         'src': {
#             'main.py': None,
#             '__init__.py': None,
#         },
#         'tests': {
#             'test_main.py': None,
#         },
#         'docs': {
#             'index.md': None,
#         },
#     })
#     return temp_dir


# ============ ТЕСТЫ НА ФАЙЛ ============


class TestFile:
    @pytest.mark.parametrize("pattern, filename", [
        (w("test.txt"), "test.txt"),
        (w("*.txt"), "anything.txt"),
        (r(r'^\d+\.jpg$'), "001.jpg"),
        (r(r'^data_\w+\.csv$'), "data_export.csv"),
    ])
    def test_file_exists_is_file(self, temp_dir, create_files, pattern, filename):
        create_files(temp_dir, {filename: None})

        struct = file(pattern)
        result = struct.validate(temp_dir)

        assert not result

    @pytest.mark.parametrize("pattern, filename", [
        (w("test.txt"), "test.txt"),
        (w("*.txt"), "document.txt"),
        (r(r'^\d+\.jpg$'), "123.jpg"),
    ])
    def test_file_exists_is_not_file(self, temp_dir, create_files, validate_errors, pattern, filename):
        create_files(temp_dir, {filename: {}})

        struct = file(pattern)
        result = struct.validate(temp_dir)

        assert result
        validate_errors(
            result,
            (NotFileError, [filename]),
        )

    @pytest.mark.parametrize("is_optional, should_have_errors", [
        (False, True),
        (True, False),
    ])
    def test_file_not_exists(self, temp_dir, validate_errors, is_optional, should_have_errors):
        name = "test.txt"

        struct = file(w(name), is_optional=is_optional)
        result = struct.validate(temp_dir)

        if should_have_errors:
            assert result

            validate_errors(
                result,
                (MandatoryMissedError, [temp_dir.name]),
            )
        else:
            assert not result

    def test_file_validate_as_root_exists(self, temp_dir, create_files, validate_errors):
        name = "test.txt"

        create_files(temp_dir, {name: None})

        struct = file(w(name))
        result = struct.validate_as_root(temp_dir / name)

        assert not result

    def test_file_validate_as_root_missing_mandatory(self, temp_dir, validate_errors):
        name = "test.txt"

        test_file = temp_dir / name

        struct = file(w(name))
        result = struct.validate_as_root(test_file)

        assert result
        validate_errors(
            result,
            (MandatoryMissedError, [name]),
        )

    def test_file_validate_as_root_missing_optional(self, temp_dir):
        test_file = temp_dir / "test.txt"

        struct = file(w("test.txt"), is_optional=True)
        result = struct.validate_as_root(test_file)

        assert not result


# ============ ТЕСТЫ НА ПАПКУ ============


class TestFolder:
    @pytest.mark.parametrize("pattern, folder_name", [
        (w("test"), "test"),
        (w("data_*"), "data_export"),
        (r(r'^\d{4}-\d{2}-\d{2}$'), "2024-01-15"),
    ])
    def test_folder_exists_is_folder(self, temp_dir, create_files, pattern, folder_name):
        create_files(temp_dir, {folder_name: {}})

        struct = folder(pattern)
        result = struct.validate(temp_dir)

        assert not result

    @pytest.mark.parametrize("pattern, folder_name", [
        (w("test"), "test"),
        (w("data_*"), "data_export"),
    ])
    def test_folder_exists_is_not_folder(self, temp_dir, create_files, validate_errors, pattern, folder_name):
        create_files(temp_dir, {folder_name: None})

        struct = folder(pattern)
        result = struct.validate(temp_dir)

        assert result
        validate_errors(
            result,
            (NotDirectoryError, [folder_name]),
        )

    @pytest.mark.parametrize("is_optional, should_have_errors", [
        (False, True),
        (True, False),
    ])
    def test_folder_not_exists(self, temp_dir, validate_errors, is_optional, should_have_errors):
        name = "test_folder"

        struct = folder(w(name), is_optional=is_optional)
        result = struct.validate(temp_dir)

        if should_have_errors:
            assert result
            validate_errors(
                result,
                (MandatoryMissedError, [temp_dir.name]),
            )
        else:
            assert not result

    @pytest.mark.parametrize("extra_files, should_have_error", [
        ([], False),
        (["extra.txt"], True),
        (["extra1.txt", "extra2.dat"], True),
        (["extra.txt", "another.dat", "random.xyz"], True),
    ])
    def test_folder_extra_items(self, temp_dir, create_files, validate_errors, extra_files, should_have_error):
        required_name = "required.txt"
        folder_name = "test"

        create_files(temp_dir, {
            folder_name: {name: None for name in extra_files} | {
                required_name: None
            }
        })

        struct = folder(
            w(folder_name),
            file(w(required_name))
        )

        result = struct.validate_as_root(temp_dir / folder_name)

        if should_have_error:
            assert result
            validate_errors(
                result,
                (ExtraItemsError, extra_files),
            )
        else:
            assert not result

    def test_folder_structure_children_filtering(self, temp_dir, create_files):
        """SidecarValidator не попадает в _structure_children (только Matcher-совместимые)"""

        validator = folder(
            w("project"),
            file(w("*.txt")),
            sidecar(
                r(r'^(.+)\.jpg$'),
                r(r'^(.+)\.json$')
            )
        )

        assert len(validator._structure_children) == 1


# ============ ТЕСТЫ НА SIDECAR ============


class TestSidecar:

    @pytest.mark.parametrize("main_extension, sidecar_extension, stems", [
        ("jpg", "json", ["image_001", "image_002"]),
        ("mp4", "srt", ["video_01"]),
        ("csv", "yaml", ["data_export.csv", "data_backup.csv"]),
    ])
    def test_sidecar_exists_for_each(self, temp_dir, create_files, main_extension, sidecar_extension, stems):
        file_list = []

        for stem in stems:
            file_list.extend([
                f"{stem}.{main_extension}",
                f"{stem}.{sidecar_extension}",
            ])

        create_files(temp_dir, {name: None for name in file_list})

        struct = sidecar(
            main_pattern=r(rf'^(.+)\.{main_extension}$'),
            sidecar_pattern=r(rf'^(.+)\.{sidecar_extension}$')
        )

        assert not struct.validate(temp_dir)

    @pytest.mark.parametrize("main_files, sidecar_files, expected_missing", [
        (["image_001.jpg", "image_002.jpg"], ["image_001.json"], 1),
        (["image_001.jpg", "image_002.jpg", "image_003.jpg"], ["image_001.json"], 2),
        (["image_001.jpg", "image_002.jpg", "image_003.jpg"], [], 3),
    ])
    def test_sidecar_missing(self, temp_dir, create_files, validate_errors, main_files, sidecar_files,
                             expected_missing):
        create_files(temp_dir, {name: None for name in main_files + sidecar_files})

        struct = sidecar(
            main_pattern=r(r'^(.+)\.jpg$'),
            sidecar_pattern=r(r'^(.+)\.json$')
        )

        result = struct.validate(temp_dir)

        assert result
        validate_errors(
            result,
            (NoSidecarError, main_files[-expected_missing:]),
        )

    @pytest.mark.parametrize("main_files, sidecar_files", [
        ([], ["image_001.json", "image_002.json"]),
        ([], ["image_001.yaml", "image_002.yaml"]),
        ([], []),
    ])
    def test_sidecar_no_main_files(self, temp_dir, create_files, main_files, sidecar_files):
        create_files(temp_dir, {name: None for name in main_files + sidecar_files})

        struct = sidecar(
            main_pattern=r(r'^(.+)\.jpg$'),
            sidecar_pattern=r(r'^(.+)\.json$')
        )

        assert not struct.validate(temp_dir)

    @pytest.mark.parametrize("main_groups, sidecar_groups, should_fail", [
        (0, 0, True),
        (1, 1, False),
        (2, 2, False),
        (1, 2, True),
        (3, 1, True),
    ])
    def test_sidecar_group_validation(self, main_groups, sidecar_groups, should_fail):
        main_pattern_str = r'^' + r'(\w+)_' * main_groups + r'image\.jpg$'
        sidecar_pattern_str = r'^' + r'(\w+)_' * sidecar_groups + r'image\.json$'

        if should_fail:
            with pytest.raises(ValueError):
                sidecar(
                    main_pattern=r(main_pattern_str),
                    sidecar_pattern=r(sidecar_pattern_str)
                )
        else:
            result = sidecar(
                main_pattern=r(main_pattern_str),
                sidecar_pattern=r(sidecar_pattern_str)
            )

            assert result


# ============ ТЕСТЫ НА XOR ============

def min_max_checks_file_generator(size: int):
    for check_count in range(1, size):
        for file_count in range(size):
            success_count = min(file_count, check_count)

            for min_checks in range(size):
                for max_checks in range(max(min_checks, 1), size):
                    yield min_checks, max_checks, file_count, check_count, min_checks <= success_count <= max_checks

                yield min_checks, None, file_count, check_count, min_checks <= success_count


class TestXorValidator:
    """Валидация параметров XorValidator.__post_init__."""

    @pytest.mark.parametrize("children_count, min_checks, max_checks, error_message", [
        (2, -1, 1, "Minimum number of checks should be greater than or equal to 0"),
        (2, 0, 0, "Maximum number of checks should be greater than 0"),
        (2, 0, -5, "Maximum number of checks should be greater than 0"),
        (2, 5, 2, "Maximum number of checks should be greater than or equal to minimum"),
        (2, 5, 6, "Minimum number of checks should be greater than or equal to children count"),
        (0, 5, 6, "There should be at least one child"),
        (1, 0, None, "Combination of min=0 and no max doesn't have sense"),
    ])
    def test_xor_checks_limits(self, children_count, min_checks, max_checks, error_message):
        with pytest.raises(ValueError, match=error_message):
            children = [file(w(c + ".txt")) for c in string.ascii_lowercase[:children_count]]

            XorValidator(
                children=children,
                min_checks=min_checks,
                max_checks=max_checks
            )

    @pytest.mark.parametrize("min_checks, max_checks", [
        (1, 1),
        (1, 3),
        (1, None),
        (0, 1),
    ])
    def test_xor_valid_params(self, min_checks, max_checks):
        validator = XorValidator(
            children=[file(w("a.txt")), file(w("b.txt"))],
            min_checks=min_checks,
            max_checks=max_checks
        )

        assert validator.min_checks == min_checks
        assert validator.max_checks == max_checks

    """Метод matches() и свойство _matching_children."""

    @pytest.mark.parametrize("test_name, expected", [
        ("test.txt", True),
        ("test_txt", False),
        ("config.json", True),
        ("image.jpg", False),
    ])
    def test_xor_matches_with_matching_children(self, test_name, expected):
        validator = xor(
            file(w("*.txt")),
            file(w("*.json"))
        )

        assert validator.matches(test_name) == expected

    def test_xor_matches_without_substructure_children(self):
        validator = XorValidator(
            children=[
                anything(),
                anything()
            ],
            min_checks=1,
            max_checks=2
        )

        assert validator.matches("test.txt")

    def test_xor_matching_children_includes_any_validator(self):
        file1 = file(w("*.txt"))
        file2 = file(w("*.json"))
        any_validator = anything()

        validator = XorValidator(
            children=[file1, file2, any_validator],
            min_checks=1,
            max_checks=2
        )

        matching = validator._matching_children

        assert len(matching) == 3
        assert file1 in matching
        assert file2 in matching
        assert any_validator in matching

    @pytest.mark.parametrize("create_a, create_b, expected_errors", [
        (False, False, [
            AllValidationsFailedError,
            MandatoryMissedError,
            MandatoryMissedError,
        ]),
        (True, True, [
            ManyOptionsError,
        ]),
        (True, False, []),
        (False, True, []),
    ])
    def test_xor_scenarios(self, temp_dir, create_files, validate_errors, create_a, create_b, expected_errors):
        structure = {}
        name_a = "option_a.txt"
        name_b = "option_b.txt"

        if create_a:
            structure[name_a] = None

        if create_b:
            structure[name_b] = None

        create_files(temp_dir, structure)

        struct = xor(
            file(w(name_a)),
            file(w(name_b))
        )
        result = struct.validate(temp_dir)

        if expected_errors:
            assert result

            validate_errors(
                result,
                *[(error, [temp_dir.name]) for error in expected_errors],
            )
        else:
            assert not result

    # @pytest.mark.parametrize("min_checks, max_checks, files, should_error", [
    #     (1, 1, ["a.txt"], False),
    #     (1, 1, ["a.txt", "b.txt"], True),
    #     (2, 3, ["a.txt"], True),
    #     (2, 3, ["a.txt", "b.txt"], False),
    #     (2, 3, ["a.txt", "b.txt", "c.txt"], False),
    #     (2, 3, ["a.txt", "b.txt", "c.txt", "d.txt"], True),
    #     (1, None, ["a.txt", "b.txt", "c.txt"], False),
    # ])
    @pytest.mark.parametrize(
        "min_checks, max_checks, file_count, check_count, success",
        min_max_checks_file_generator(5)
    )
    def test_xor_min_max_combinations(
            self,
            temp_dir,
            create_files,
            min_checks,
            max_checks,
            file_count,
            check_count,
            success
    ):
        extension = ".txt"

        files = (stem + extension for stem in string.ascii_lowercase[:file_count])

        create_files(temp_dir, {f: None for f in files})

        children = [file(w(stem + extension)) for stem in string.ascii_lowercase[:check_count]]

        validator = XorValidator(
            children=children,
            min_checks=min_checks,
            max_checks=max_checks
        )

        result = validator.validate(temp_dir)

        if success:
            assert not result
        else:
            assert result

    @pytest.mark.parametrize("files_count, checks_count", [
        (files_count, checks_count)
        for files_count in range(10)
        for checks_count in range(files_count + 1, 10)
    ])
    def test_xor_few_options_error(self, temp_dir, create_files, validate_errors, files_count, checks_count):
        extension = ".txt"

        create_files(temp_dir, {c + extension: None for c in string.ascii_lowercase[:files_count]})
        children = [file(w(c + extension)) for c in string.ascii_lowercase[:checks_count]]

        validator = XorValidator(
            children=children,
            min_checks=checks_count,
            max_checks=checks_count,
        )

        result = validator.validate(temp_dir)

        assert result
        validate_errors(
            result,
            (FewOptionsError, [temp_dir.name]),
        )


class TestOnlyOne:
    @pytest.mark.parametrize("checks_count, file_stem", [
        (count, string.ascii_lowercase[stem_index])
        for count in range(1, 10)
        for stem_index in range(count)
    ])
    def test_only_one_success(self, temp_dir, create_files, checks_count, file_stem):
        extension = ".txt"

        create_files(temp_dir, {file_stem + extension: None})

        struct = only_one(*[file(w(c + extension)) for c in string.ascii_lowercase[:checks_count]])
        result = struct.validate(temp_dir)

        assert not result

    @pytest.mark.parametrize("checks_count", list(range(1, 10)))
    def test_only_one_none_exists(self, temp_dir, create_files, validate_errors, checks_count):
        extension = ".txt"

        struct = only_one(*[file(w(c + extension)) for c in string.ascii_lowercase[:checks_count]])
        result = struct.validate(temp_dir)

        assert result

        validate_errors(
            result,
            (AllValidationsFailedError, [temp_dir.name]),
            *[(MandatoryMissedError, [temp_dir.name]) for _ in range(checks_count)],
        )

    @pytest.mark.parametrize("files_count, checks_count", [
        (files_count, checks_count)
        for checks_count in range(2, 10)
        for files_count in range(2, checks_count + 1)
    ])
    def test_only_one_too_many(self, temp_dir, create_files, validate_errors, files_count, checks_count):
        # Создаем слишком много файлов проходящих проверки (больше двух)
        extension = ".txt"

        create_files(temp_dir, {c + extension: None for c in string.ascii_lowercase[:files_count]})

        struct = only_one(*[file(w(c + extension)) for c in string.ascii_lowercase[:checks_count]])
        result = struct.validate(temp_dir)

        assert result
        validate_errors(result, (ManyOptionsError, [temp_dir.name]))


class TestAtLeastOne:
    @pytest.mark.parametrize("stems, checks_count", [
        (string.ascii_lowercase[start:end], checks_count)
        for checks_count in range(1, 10)
        for start in range(0, checks_count)
        for end in range(start + 1, checks_count + 1)
    ])
    def test_at_least_one_success(self, temp_dir, create_files, stems, checks_count):
        extension = ".txt"

        create_files(temp_dir, {stem + extension: None for stem in stems})

        struct = at_least_one(*[file(w(c + extension)) for c in string.ascii_lowercase[:checks_count]])
        result = struct.validate(temp_dir)

        assert not result

    @pytest.mark.parametrize("checks_count", list(range(1, 10)))
    def test_at_least_one_none_exists(self, temp_dir, create_files, validate_errors, checks_count):
        extension = ".txt"

        struct = at_least_one(*[file(w(c + extension)) for c in string.ascii_lowercase[:checks_count]])
        result = struct.validate(temp_dir)

        assert result
        validate_errors(
            result,
            (AllValidationsFailedError, [temp_dir.name]),
            *[(MandatoryMissedError, [temp_dir.name]) for _ in range(checks_count)],
        )


class TestAnything:
    @pytest.mark.parametrize("stem", [
        *[c for c in "abcde"],
        ".hidden",
        "123.456.789",
        "stem with spaces",
        "!@#$%^&*()",
        "",
    ])
    @pytest.mark.parametrize("extension", [
        ".txt",
        ".jpg",
        ".csv",
        "",
    ])
    @pytest.mark.parametrize("structure", [
        {},
        None,
    ])
    def test_anything_in_folder(self, temp_dir, create_files, stem, extension, structure):
        folder_name = "test"

        create_files(temp_dir, {
            folder_name: {
                stem + extension: structure,
            }
        })

        struct = folder(
            w(folder_name),
            anything()
        )

        result = struct.validate(temp_dir)

        assert not result

    def test_anything_matches_any_name(self):
        validator = anything()

        assert validator.matches("file.txt")
        assert validator.matches("image.jpg")
        assert validator.matches("")
        assert validator.matches("!@#$%^&*()")

    def test_anything_validate_nothing(self, temp_dir, create_files):
        validator = anything()

        result = validator.validate(temp_dir)

        assert not result


class TestComplexScenarios:
    @pytest.mark.parametrize("depth", list(range(1, 10)))
    def test_nested_folders_depth(self, temp_dir, create_files, depth):
        structure = {}
        current = structure

        for i in range(depth):
            nested = {}

            current |= {
                f"file_{i}.txt": None,
                f"folder_{i}": nested,
            }

            current = nested

        create_files(temp_dir, structure)

        children = []

        for i in reversed(range(depth)):
            children = [
                folder(
                    w(f"folder_{i}"),
                    *children,
                ),
                file(w(f"file_{i}.txt"))
            ]

        validator = folder(
            w("*"),
            *children,
        )

        result = validator.validate_as_root(temp_dir)

        assert not result

    @pytest.mark.parametrize("extensions_count", range(1, 10))
    def test_multiple_patterns_same_folder(self, temp_dir, create_files, extensions_count):
        extensions = [f".{c}" for c in string.ascii_lowercase[:extensions_count]]
        filenames = {f"file{ext}": None for ext in extensions}

        create_files(temp_dir, filenames)

        children = [file(w(f"*{ext}")) for ext in extensions]
        struct = folder(
            w("*"),
            *children
        )

        result = struct.validate_as_root(temp_dir)

        assert not result


# ============ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ============


class TestIntegration:

    def test_photo_project_structure(self, temp_dir, create_files):
        project = temp_dir / "photo_project"
        project.mkdir()

        create_files(project, {
            'raw': {},
            'edited': {},
            'IMG_001.jpg': None,
            'IMG_001.json': None,
            'IMG_002.jpg': None,
            'IMG_002.json': None,
            'README.md': None,
        })

        struct = folder(
            w("photo_project"),
            file(w("*.jpg")),
            file(w("*.json")),
            sidecar(
                main_pattern=r(r'^(.+)\.jpg$'),
                sidecar_pattern=r(r'^(.+)\.json$')
            ),
            file(w("README.md")),
            folder(w("raw")),
            folder(w("edited"))
        )

        assert not struct.validate_as_root(project)

    def test_config_either_file_or_folder(self, temp_dir, create_files):
        create_files(temp_dir, {"config.json": None})

        struct = xor(
            file(w("config.json")),
            folder(w("config"), file(w("*.yaml")))
        )

        assert not struct.validate(temp_dir)

    @pytest.mark.parametrize("structure_type", ["simple", "with_metadata", "with_archive"])
    def test_data_folder_variants(self, temp_dir, create_files, structure_type):
        data_folder = temp_dir / "data"
        data_folder.mkdir()

        if structure_type == "simple":
            create_files(data_folder, {"dataset.csv": None})
            validators = [file(w("*.csv"))]
        elif structure_type == "with_metadata":
            create_files(data_folder, {"dataset.csv": None, "metadata.json": None})
            validators = [file(w("*.csv")), file(w("metadata.json"))]
        else:
            create_files(data_folder, {"dataset.csv": None, "metadata.json": None, "backup.zip": None})
            validators = [file(w("*.csv")), file(w("metadata.json")), file(w("*.zip"), is_optional=True)]

        assert not folder(w("data"), *validators).validate_as_root(data_folder)

    def test_project_has_readme(self, standard_project_structure):
        assert not file(w("README.md")).validate(standard_project_structure)

    def test_project_has_src(self, standard_project_structure):
        assert not folder(w("src"), file(w("*.py"))).validate(standard_project_structure)


# ============ ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ============


@pytest.mark.slow
class TestPerformance:

    @pytest.mark.parametrize("file_count", [10, MANY, VERY_MANY])
    def test_many_files_validation(self, temp_dir, create_files, file_count):
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        create_files(test_folder, {f"file_{i:04d}.txt": None for i in range(file_count)})

        assert not folder(w("test"), file(w("*.txt"))).validate_as_root(test_folder)

    @pytest.mark.parametrize("pair_count", [5, 20, MANY])
    def test_many_sidecar_pairs(self, temp_dir, create_files, pair_count):
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        files = {}
        for i in range(pair_count):
            files[f"image_{i:04d}.jpg"] = None
            files[f"image_{i:04d}.json"] = None

        create_files(test_folder, files)

        struct = folder(
            w("test"),
            sidecar(
                main_pattern=r(r'^(.+)\.jpg$'),
                sidecar_pattern=r(r'^(.+)\.json$')
            )
        )

        assert not struct.validate_as_root(test_folder)


# ============ ГРАНИЧНЫЕ СЛУЧАИ ============


@pytest.mark.edge_case
class TestEdgeCases:

    @pytest.mark.parametrize("filename", [
        "file with spaces.txt",
        "file[brackets].txt",
        "file(parens).txt",
        "file{braces}.txt",
        ".hidden",
        "..double_dot",
        "file@special#chars.txt",
    ])
    def test_special_filenames(self, temp_dir, filename):
        test_file = temp_dir / filename
        test_file.touch()

        assert not file(w("*")).validate_as_root(test_file)
