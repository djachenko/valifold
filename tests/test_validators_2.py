"""
Тесты для validators.py

Покрывает:
- XorValidator: __post_init__ валидация, matches(), _matching_children, FewOptionsError
- SidecarValidator: __post_init__ валидация количества групп
- SubstructureValidator: validate() из родителя
- FolderValidator: ExtraItemsError, _structure_children
- AnyValidator: matches() и validate()
"""

import tempfile
from pathlib import Path

import pytest

from valifold.dsl import file, folder, anything, sidecar, xor
from valifold.errors import (
    MandatoryMissedError,
    NotFileError,
    NotDirectoryError,
    ExtraItemsError,
    FewOptionsError,
)
from valifold.pattern import w, r
from valifold.validators import XorValidator


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestXorValidatorValidation:
    """Валидация параметров XorValidator"""

    def test_xor_min_checks_negative(self):
        """min_checks < 0 выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Minimum number of checks should be greater than or equal to 0"):
            XorValidator(
                children=[file(w("a.txt")), file(w("b.txt"))],
                min_checks=-1,
                max_checks=1
            )

    def test_xor_max_checks_zero(self):
        """max_checks = 0 выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Maximum number of checks should be greater than 0"):
            XorValidator(
                children=[file(w("a.txt")), file(w("b.txt"))],
                min_checks=0,
                max_checks=0
            )

    def test_xor_max_checks_negative(self):
        """max_checks < 0 выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Maximum number of checks should be greater than 0"):
            XorValidator(
                children=[file(w("a.txt")), file(w("b.txt"))],
                min_checks=0,
                max_checks=-5
            )

    def test_xor_min_greater_than_max(self):
        """min_checks > max_checks выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Maximum number of checks should be greater than or equal to minimum"):
            XorValidator(
                children=[file(w("a.txt")), file(w("b.txt"))],
                min_checks=5,
                max_checks=2
            )

    def test_xor_valid_min_max(self):
        """Валидные min/max создаются без ошибок"""
        validator1 = XorValidator(
            children=[file(w("a.txt")), file(w("b.txt"))],
            min_checks=1,
            max_checks=1
        )
        assert validator1.min_checks == 1
        assert validator1.max_checks == 1

        validator2 = XorValidator(
            children=[file(w("a.txt")), file(w("b.txt"))],
            min_checks=1,
            max_checks=3
        )
        assert validator2.min_checks == 1
        assert validator2.max_checks == 3

        validator3 = XorValidator(
            children=[file(w("a.txt")), file(w("b.txt"))],
            min_checks=1,
            max_checks=None
        )
        assert validator3.min_checks == 1
        assert validator3.max_checks is None


class TestXorValidatorMatching:
    """Тесты метода matches() в XorValidator"""

    def test_xor_matches_with_matching_children(self):
        """XOR matches возвращает True если есть подходящие дети"""
        validator = xor(
            file(w("*.txt")),
            file(w("*.json"))
        )

        assert validator.matches("test.txt")
        assert validator.matches("config.json")
        assert not validator.matches("image.jpg")

    def test_xor_matches_with_non_matching_children(self):
        """XOR matches возвращает False если нет SubstructureValidator детей"""
        validator = XorValidator(
            children=[anything(), anything()],
            min_checks=1,
            max_checks=2
        )

        assert not validator.matches("test.txt")

    def test_xor_matching_children_property(self):
        """Кэшированное свойство _matching_children"""
        file1 = file(w("*.txt"))
        file2 = file(w("*.json"))
        anything_validator = anything()

        validator = XorValidator(
            children=[file1, file2, anything_validator],
            min_checks=1,
            max_checks=2
        )

        matching = validator._matching_children
        assert len(matching) == 2
        assert file1 in matching
        assert file2 in matching
        assert anything_validator not in matching


class TestFewOptionsError:
    """Тесты на FewOptionsError"""

    def test_xor_too_few_successes(self, temp_dir):
        """XOR требует минимум 2 успеха, но получает только 1"""
        (temp_dir / "option_a.txt").touch()

        validator = XorValidator(
            children=[
                file(w("option_a.txt"), is_optional=False),
                file(w("option_b.txt"), is_optional=False),
                file(w("option_c.txt"), is_optional=False),
            ],
            min_checks=2,
            max_checks=3
        )

        errors = validator.validate(temp_dir)

        assert errors
        assert any(isinstance(e, FewOptionsError) for e in errors)

    def test_at_least_two_with_only_one_success(self, temp_dir):
        """Требуем минимум 2 файла, есть только 1"""
        (temp_dir / "file1.txt").touch()

        validator = XorValidator(
            children=[
                file(w("file1.txt"), is_optional=False),
                file(w("file2.txt"), is_optional=False),
                file(w("file3.txt"), is_optional=False),
            ],
            min_checks=2,
            max_checks=None
        )

        errors = validator.validate(temp_dir)

        assert errors
        assert any(isinstance(e, FewOptionsError) for e in errors)


class TestSidecarValidatorGroupCount:
    """Валидация количества групп в SidecarValidator"""

    def test_sidecar_main_pattern_no_groups(self):
        """main_pattern без групп выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Main pattern should have at least one capture group"):
            sidecar(
                main_pattern=r(r'^image\.jpg$'),
                sidecar_pattern=r(r'^(.+)\.json$')
            )

    def test_sidecar_sidecar_pattern_no_groups(self):
        """sidecar_pattern без групп выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Sidecar pattern should have at least one capture group"):
            sidecar(
                main_pattern=r(r'^(.+)\.jpg$'),
                sidecar_pattern=r(r'^image\.json$')
            )

    def test_sidecar_different_group_count(self):
        """Разное количество групп выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Main and sidecar pattern should have equal count of capture groups"):
            sidecar(
                main_pattern=r(r'^(\w+)_(\d+)\.jpg$'),
                sidecar_pattern=r(r'^(.+)\.json$')
            )

    def test_sidecar_equal_group_count(self):
        """Одинаковое количество групп работает"""
        validator1 = sidecar(
            main_pattern=r(r'^(.+)\.jpg$'),
            sidecar_pattern=r(r'^(.+)\.json$')
        )
        assert validator1.main_pattern.group_count == 1
        assert validator1.sidecar_pattern.group_count == 1

        validator2 = sidecar(
            main_pattern=r(r'^(\w+)_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^(\w+)_(\d+)\.json$')
        )
        assert validator2.main_pattern.group_count == 2
        assert validator2.sidecar_pattern.group_count == 2


class TestSubstructureValidatorValidate:
    """Тесты метода validate в SubstructureValidator"""

    def test_file_validate_from_parent_single_match(self, temp_dir):
        """validate файла из родителя (один файл)"""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        validator = file(w("test.txt"), is_optional=False)
        errors = validator.validate(temp_dir)

        assert not errors

    def test_file_validate_from_parent_multiple_matches(self, temp_dir):
        """validate когда паттерн совпадает с несколькими файлами"""
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.txt").touch()
        (temp_dir / "file3.txt").touch()

        validator = file(w("*.txt"), is_optional=False)
        errors = validator.validate(temp_dir)

        assert not errors

    def test_file_validate_from_parent_no_match_optional(self, temp_dir):
        """validate когда файл не найден но опциональный"""
        validator = file(w("missing.txt"), is_optional=True)
        errors = validator.validate(temp_dir)

        assert not errors

    def test_file_validate_from_parent_no_match_mandatory(self, temp_dir):
        """validate когда обязательный файл не найден"""
        validator = file(w("missing.txt"), is_optional=False)
        errors = validator.validate(temp_dir)

        assert errors
        assert any(isinstance(e, MandatoryMissedError) for e in errors)

    def test_validate_with_pattern_mismatch_is_not_file(self, temp_dir):
        """Паттерн совпадает, но это не файл (а директория)"""
        (temp_dir / "test.txt").mkdir()

        validator = file(w("test.txt"), is_optional=False)
        errors = validator.validate(temp_dir)

        assert errors
        assert any(isinstance(e, NotFileError) for e in errors)

    def test_validate_with_pattern_mismatch_is_not_directory(self, temp_dir):
        """Паттерн совпадает, но это не директория (а файл)"""
        (temp_dir / "subfolder").touch()

        validator = folder(w("subfolder"), is_optional=False)
        errors = validator.validate(temp_dir)

        assert errors
        assert any(isinstance(e, NotDirectoryError) for e in errors)


class TestFolderValidatorWithChildren:
    """FolderValidator с различными детьми"""

    def test_folder_with_extra_items(self, temp_dir):
        """Папка с лишними элементами (ExtraItemsError)"""
        test_folder = temp_dir / "project"
        test_folder.mkdir()
        (test_folder / "expected.txt").touch()
        (test_folder / "extra1.tmp").touch()
        (test_folder / "extra2.bak").touch()

        validator = folder(
            w("project"),
            file(w("expected.txt"))
        )

        errors = validator.validate_as_root(test_folder)

        assert errors
        assert any(isinstance(e, ExtraItemsError) for e in errors)

        extra_errors = [e for e in errors if isinstance(e, ExtraItemsError)]
        assert len(extra_errors) == 1
        assert len(extra_errors[0].paths) == 2

    def test_folder_with_anything_validator(self, temp_dir):
        """Папка с anything() валидатором (позволяет всё)"""
        test_folder = temp_dir / "project"
        test_folder.mkdir()
        (test_folder / "file1.txt").touch()
        (test_folder / "file2.jpg").touch()
        (test_folder / "anything.tmp").touch()

        validator = folder(
            w("project"),
            anything()
        )

        errors = validator.validate_as_root(test_folder)

        assert not errors

    def test_folder_structure_children_filtering(self, temp_dir):
        """Фильтрация _structure_children (только Matcher)"""
        test_folder = temp_dir / "project"
        test_folder.mkdir()
        (test_folder / "file.txt").touch()

        validator = folder(
            w("project"),
            file(w("*.txt")),
            sidecar(r(r'^(.+)\.jpg$'), r(r'^(.+)\.json$'))
        )

        assert len(validator._structure_children) == 1


class TestAnyValidator:
    """Тесты AnyValidator"""

    def test_anything_matches_any_name(self):
        """anything() совпадает с любым именем"""
        validator = anything()

        assert validator.matches("file.txt")
        assert validator.matches("image.jpg")
        assert validator.matches("")
        assert validator.matches("!@#$%^&*()")

    def test_anything_validate_always_succeeds(self, temp_dir):
        """anything().validate() всегда успешен"""
        validator = anything()

        errors = validator.validate(temp_dir)
        assert not errors

        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.jpg").touch()

        errors = validator.validate(temp_dir)
        assert not errors

    def test_anything_in_folder_allows_all_files(self, temp_dir):
        """anything() в папке разрешает любые файлы"""
        test_folder = temp_dir / "permissive"
        test_folder.mkdir()

        (test_folder / "file.txt").touch()
        (test_folder / "image.jpg").touch()
        (test_folder / "data.csv").touch()

        validator = folder(
            w("permissive"),
            anything()
        )

        errors = validator.validate_as_root(test_folder)

        assert not errors


class TestXorVariousScenarios:
    """Различные сценарии XorValidator"""

    @pytest.mark.parametrize("min_checks,max_checks,files,should_error", [
        (1, 1, ["a.txt"], False),
        (1, 1, ["a.txt", "b.txt"], True),
        (2, 3, ["a.txt"], True),
        (2, 3, ["a.txt", "b.txt"], False),
        (2, 3, ["a.txt", "b.txt", "c.txt"], False),
        (2, 3, ["a.txt", "b.txt", "c.txt", "d.txt"], True),
        (1, None, ["a.txt", "b.txt", "c.txt"], False),
    ])
    def test_xor_various_min_max_combinations(self, temp_dir, min_checks, max_checks, files, should_error):
        """Различные комбинации min/max для XOR"""
        for filename in files:
            (temp_dir / filename).touch()

        children = [
            file(w("a.txt"), is_optional=False),
            file(w("b.txt"), is_optional=False),
            file(w("c.txt"), is_optional=False),
            file(w("d.txt"), is_optional=False),
        ]

        validator = XorValidator(
            children=children,
            min_checks=min_checks,
            max_checks=max_checks
        )

        errors = validator.validate(temp_dir)

        if should_error:
            assert errors
        else:
            assert not errors