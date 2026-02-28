"""
Тесты для errors.py

Покрывает:
- ValifoldError.formatted_message() с различными параметрами
- ValifoldError.__post_init__() валидацию
- Все подклассы ошибок
"""
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
import pytest
from valifold.errors import (
    ValifoldError,
    MandatoryMissedError,
    NotFileError,
    NotDirectoryError,
    ExtraItemsError,
    AllValidationsFailedError,
    FewOptionsError,
    ManyOptionsError,
    NoSidecarError,
)

# ============================================================================
# ФИКСТУРЫ
# ============================================================================

MANY = 5
VERY_MANY = 100


@pytest.fixture
def sample_paths(tmp_path):
    """Создаёт набор тестовых путей"""
    paths = {
        'single': [tmp_path / "file.txt"],
        'double': [tmp_path / "file1.txt", tmp_path / "file2.txt"],
        'triple': [tmp_path / "file1.txt", tmp_path / "file2.txt", tmp_path / "file3.txt"],
        'many': [tmp_path / f"file{i}.txt" for i in range(MANY)],
        'nested': [tmp_path / "subdir" / "file.txt"],
    }

    # # Создаём директории для nested
    # (tmp_path / "subdir").mkdir(exist_ok=True)

    return paths


PLACEHOLDER = "{paths}"


@dataclass
class ErrorClassInfo:
    error_class: type[ValifoldError]
    raw_message: str
    user_substrings: list[str]


@pytest.fixture(params=[
    (MandatoryMissedError, "Mandatory paths {paths} are missed",),
    (NotFileError, "{paths} is not a file",),
    (NotDirectoryError, "{paths} is not a directory",),
    (ExtraItemsError, "Extra items found: {paths}"),
    (AllValidationsFailedError, "{paths} failed all validations",),
    (FewOptionsError, "{paths} matches too few options",),
    (ManyOptionsError, "{paths} matches too many options",),
    (NoSidecarError, "{paths} do not have sidecar",),
])
def error_class_info(request):
    """Параметризованная фикстура для всех классов ошибок"""
    error_class, raw_message = request.param

    user_messages = raw_message.split(PLACEHOLDER)
    user_messages = [message.strip() for message in user_messages]
    user_messages = [message for message in user_messages if message]

    return ErrorClassInfo(error_class, raw_message, user_messages)


@pytest.fixture
def error_class(error_class_info):
    return error_class_info.error_class


TEST_TXT = [Path("test.txt")]


# ============================================================================
# ТЕСТЫ ФОРМАТИРОВАНИЯ
# ============================================================================

class TestErrorFormatting:
    """Тесты форматирования сообщений об ошибках"""

    @pytest.mark.parametrize("paths_key, expected_and, expected_comma", [
        ('single', False, False),  # "file.txt"
        ('double', True, False),  # "file1.txt and file2.txt"
        ('triple', True, True),  # "file1.txt, file2.txt and file3.txt"
        ('many', True, True),  # "file0.txt, file1.txt, file2.txt, file3.txt and file4.txt"
    ])
    def test_formatted_message_paths_count(self, error_class, sample_paths, paths_key, expected_and, expected_comma):
        """Форматирование корректно работает для 1, 2, 3+ путей"""
        paths = sample_paths[paths_key]
        error = error_class(paths)
        formatted = error.formatted_message(root_path=None)

        assert (" and " in formatted) == expected_and
        assert (", " in formatted) == expected_comma

    @pytest.mark.parametrize("use_root_path", [True, False])
    def test_formatted_message_with_and_without_root(self, error_class, sample_paths, tmp_path, use_root_path):
        """Форматирование с корневым путём и без него"""
        paths = sample_paths['nested']
        error = error_class(paths)

        root_path = tmp_path if use_root_path else None
        formatted = error.formatted_message(root_path=root_path)

        assert "file.txt" in formatted
        assert ("subdir" in formatted) == use_root_path

    def test_formatted_message_preserves_all_filenames(self, error_class, sample_paths):
        """Все имена файлов присутствуют в отформатированном сообщении"""
        paths = sample_paths['many']
        error = error_class(paths)
        formatted = error.formatted_message(root_path=None)

        for i in range(MANY):
            assert f"file{i}.txt" in formatted

    def test_error_with_custom_message(self, error_class_info, sample_paths):
        """Кастомное сообщение об ошибке переопределяет default_message"""
        custom_message = "Custom error: {paths} not found"
        error = error_class_info.error_class(sample_paths['single'], message=custom_message)
        formatted = error.formatted_message(root_path=None)

        assert "Custom error:" in formatted
        assert "file.txt" in formatted

        for substring in error_class_info.user_substrings:
            assert substring not in formatted


# ============================================================================
# ТЕСТЫ ВАЛИДАЦИИ
# ============================================================================

class TestErrorValidation:
    """Тесты валидации ошибок"""

    @pytest.mark.parametrize("default_message_, message, paths, is_good", [
        # Пустое сообщение - ошибка
        (None, None, TEST_TXT, False),
        (None, "", TEST_TXT, False),
        ("", None, TEST_TXT, False),
        ("", "", TEST_TXT, False),

        # Пустой список путей - ошибка
        ("valid_default", None, [], False),
        (None, "valid_custom", [], False),
        ("valid_default", "valid_custom", [], False),

        # Оба пустые - ошибка
        (None, None, [], False),
        ("", "", [], False),

        # Валидные комбинации - OK
        ("valid_default", None, TEST_TXT, True),
        ("valid_default", "", TEST_TXT, True),
        (None, "valid_custom", TEST_TXT, True),
        ("", "valid_custom", TEST_TXT, True),
        ("valid_default", "valid_custom", TEST_TXT, True),
    ])
    def test_message_and_paths_validation(self, default_message_, message, paths, is_good):
        """Валидация сообщения и путей при создании ошибки"""

        class TestError(ValifoldError):
            default_message = default_message_

        if is_good:
            TestError(paths=paths, message=message)
        else:
            with pytest.raises(ValueError):
                TestError(paths=paths, message=message)

    @pytest.mark.parametrize("default_message_", [
        None,
        "",
    ])
    @pytest.mark.parametrize("message", [
        None,
        "",
    ])
    def test_valifold_error_without_message_raises(self, default_message_, message):
        """ValifoldError без сообщения выбрасывает ValueError"""

        class EmptyError(ValifoldError):
            default_message = default_message_

        with pytest.raises(ValueError, match="Message or default message"):
            EmptyError(paths=TEST_TXT, message=message)

    def test_valifold_error_with_valid_message(self, error_class):
        """ValifoldError с валидным сообщением создается успешно"""
        error = error_class(TEST_TXT)

        assert error.paths == TEST_TXT.copy()
        assert error.default_message is not None

    def test_valifold_error_with_custom_message_override(self, error_class):
        """Кастомное сообщение перекрывает default_message"""
        custom = "My custom message: {paths}"
        error = error_class(TEST_TXT, message=custom)

        assert error.message == custom
        assert error._message_format == custom

    @pytest.mark.parametrize("message", [
        "Valid message with {paths}",
        "Another valid {paths} message",
        "Just text without placeholder",  # это валидно, просто не будет подстановки
        "Another valid {paths} message with {paths}",  # две подстановки тоже возможны
    ])
    def test_valifold_error_accepts_various_valid_messages(self, error_class, message):
        """Различные валидные сообщения принимаются"""
        error = error_class(TEST_TXT, message=message)

        assert error.message == message


# ============================================================================
# ТЕСТЫ ПОДКЛАССОВ ОШИБОК
# ============================================================================

class TestErrorSubclasses:
    """Тесты всех подклассов ошибок"""

    def test_all_error_classes_have_default_message(self, error_class):
        """Все классы ошибок имеют default_message"""
        assert error_class.default_message is not None
        assert len(error_class.default_message) > 0

    def test_default_message_contains_raw_substrings(self, error_class_info):
        """Все классы ошибок содержат ожидаемые подстроки в default_message"""
        error_class = error_class_info.error_class

        message = error_class.default_message

        substring = error_class_info.raw_message

        assert substring in message, \
            f"{error_class.__name__}.default_message должен содержать '{substring}'"

    def test_formatted_message_contains_user_substrings(self, error_class_info):
        """Каждый класс ошибки имеет специфичное содержимое в сообщении"""
        error_class = error_class_info.error_class
        error = error_class(TEST_TXT)

        message = error.formatted_message()

        for substring in error_class_info.user_substrings:
            assert substring in message, \
                f"{error_class.__name__}.formatted_message() должен содержать '{substring}'"

    def test_all_error_classes_can_be_instantiated(self, error_class):
        """Все классы ошибок можно инстанцировать"""
        error = error_class(TEST_TXT)

        assert error.paths == TEST_TXT.copy()
        assert error.default_message is not None

    def test_all_error_classes_can_format_message(self, error_class, sample_paths):
        """Все классы ошибок могут отформатировать сообщение"""
        error = error_class(sample_paths['single'])

        # Не должно выбросить исключение
        formatted = error.formatted_message(root_path=None)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "file.txt" in formatted


# ============================================================================
# ТЕСТЫ EDGE CASES
# ============================================================================

class TestErrorEdgeCases:
    """Граничные случаи и особые сценарии"""

    def test_empty_paths_list(self, error_class):
        """Пустой список путей вызывает IndexError при форматировании"""

        with pytest.raises(ValueError, match="Paths must not be empty"):
            error_class([])

    def test_paths_with_special_characters(self, error_class, tmp_path):
        """Пути со специальными символами в именах"""
        special_path = tmp_path / "file with spaces & special.txt"
        error = error_class([special_path])
        formatted = error.formatted_message(root_path=None)

        assert "file with spaces & special.txt" in formatted

    def test_very_long_path_list(self, error_class, tmp_path):
        """Очень длинный список путей"""
        file_names = [f"file_{i:03d}.txt" for i in range(VERY_MANY)]

        long_paths = [tmp_path / name for name in file_names]
        error = error_class(long_paths)
        formatted = error.formatted_message(root_path=None)

        # Проверяем, что все файлы в сообщении
        for file_name in file_names:
            assert file_name in formatted

        assert formatted.count(" and ") == 1  # только один " and " в конце

    def test_unicode_in_paths(self, error_class, tmp_path):
        """Пути с Unicode символами"""
        unicode_name = "файл_тест_日本語.txt"
        unicode_path = tmp_path / unicode_name

        error = error_class([unicode_path])
        formatted = error.formatted_message(root_path=None)

        assert unicode_name in formatted

    def test_root_path_not_parent_of_path(self, error_class, tmp_path):
        """root_path не является родителем пути - должен выбросить ValueError"""
        other_tmp = Path("/tmp/other")
        test_file = tmp_path / "file.txt"

        error = error_class([test_file])

        # relative_to должен выбросить ValueError
        with pytest.raises(ValueError):
            error.formatted_message(root_path=other_tmp)

    @pytest.mark.parametrize("num_paths", [1, 2, 3, 5, 10])
    def test_formatted_message_consistency_across_sizes(self, error_class, tmp_path, num_paths):
        """Форматирование консистентно для разных размеров списков"""
        file_names = [f"file_{i}.txt" for i in range(num_paths)]
        paths = [tmp_path / name for name in file_names]

        error = error_class(paths)
        formatted = error.formatted_message(root_path=None)

        # Все файлы должны быть в сообщении
        for file_name in file_names:
            assert file_name in formatted

        # Структура " and " должна быть корректной
        if num_paths == 1:
            assert " and " not in formatted
        else:
            assert formatted.count(" and ") == 1


# ============================================================================
# ТЕСТЫ IMMUTABILITY
# ============================================================================

class TestErrorImmutability:
    """Тесты неизменяемости объектов ошибок (frozen=True)"""

    def test_cannot_modify_paths(self, error_class):
        """Нельзя изменить paths после создания"""
        error = error_class(TEST_TXT)

        with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
            error.paths = [Path("other.txt")]

    def test_cannot_modify_message(self, error_class):
        """Нельзя изменить message после создания"""
        error = error_class(TEST_TXT, message="Custom")

        with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
            error.message = "New message"

