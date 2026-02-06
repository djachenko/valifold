"""
Тесты для errors.py

Покрывает:
- ValifoldError.formatted_message() с различными параметрами
- ValifoldError.__post_init__() валидацию
- Все подклассы ошибок
"""

from pathlib import Path
import pytest
from valifold.errors import (
    ValifoldError,
    MandatoryMissedError,
    NotFileError,
    ExtraItemsError,
)


class TestErrorFormatting:
    """Тесты форматирования сообщений об ошибках"""

    def test_formatted_message_with_root_path(self, tmp_path):
        """Форматирование с корневым путем (relative_to)"""
        test_file = tmp_path / "subdir" / "test.txt"
        test_file.parent.mkdir(parents=True)

        error = MandatoryMissedError([test_file])
        formatted = error.formatted_message(root_path=tmp_path)

        assert "subdir" in formatted or "subdir" in formatted.replace("\\", "/")

    def test_formatted_message_without_root_path(self, tmp_path):
        """Форматирование без корневого пути (только имя файла)"""
        test_file = tmp_path / "test.txt"

        error = MandatoryMissedError([test_file])
        formatted = error.formatted_message(root_path=None)

        assert "test.txt" in formatted
        assert str(tmp_path) not in formatted

    def test_formatted_message_multiple_paths(self, tmp_path):
        """Форматирование с несколькими путями"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"

        error = ExtraItemsError([file1, file2, file3])
        formatted = error.formatted_message(root_path=None)

        assert "file1.txt" in formatted
        assert "file2.txt" in formatted
        assert "file3.txt" in formatted

    def test_formatted_message_two_paths(self, tmp_path):
        """Форматирование с двумя путями (для покрытия " and ")"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        error = ExtraItemsError([file1, file2])
        formatted = error.formatted_message(root_path=None)

        assert "file1.txt" in formatted
        assert "file2.txt" in formatted
        assert " and " in formatted

    def test_error_with_custom_message(self, tmp_path):
        """Кастомное сообщение об ошибке"""
        test_file = tmp_path / "test.txt"

        custom_message = "Custom error: {paths} not found"
        error = MandatoryMissedError([test_file], message=custom_message)
        formatted = error.formatted_message(root_path=None)

        assert "Custom error:" in formatted
        assert "test.txt" in formatted


class TestErrorValidation:
    """Тесты валидации ошибок"""

    def test_valifold_error_without_message_raises(self):
        """ValifoldError без сообщения выбрасывает ValueError"""

        class EmptyError(ValifoldError):
            default_message = None

        with pytest.raises(ValueError, match="Message or default message"):
            EmptyError(paths=[Path("test.txt")])

    def test_valifold_error_with_empty_message_raises(self):
        """ValifoldError с пустым сообщением выбрасывает ValueError"""
        with pytest.raises(ValueError, match="Message or default message"):
            ValifoldError(paths=[Path("test.txt")], message="")

    def test_valifold_error_with_valid_message(self):
        """ValifoldError с валидным сообщением создается успешно"""
        error = MandatoryMissedError([Path("test.txt")])
        assert error.paths == [Path("test.txt")]
        assert error.default_message is not None

    def test_valifold_error_with_custom_message_override(self):
        """Кастомное сообщение перекрывает default_message"""
        custom = "My custom message: {paths}"
        error = MandatoryMissedError([Path("test.txt")], message=custom)

        assert error.message == custom
        assert error._message_format == custom


class TestErrorSubclasses:
    """Тесты всех подклассов ошибок"""

    def test_mandatory_missed_error(self):
        """MandatoryMissedError имеет правильное сообщение"""
        error = MandatoryMissedError([Path("test.txt")])
        assert "Mandatory" in error.default_message

    def test_not_file_error(self):
        """NotFileError имеет правильное сообщение"""
        error = NotFileError([Path("test.txt")])
        assert "not a file" in error.default_message

    def test_extra_items_error(self):
        """ExtraItemsError имеет правильное сообщение"""
        error = ExtraItemsError([Path("test.txt")])
        assert "Extra items" in error.default_message