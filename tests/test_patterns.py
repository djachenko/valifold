"""
Тесты для pattern.py

Покрывает:
- BasePattern валидацию типов
- RegexPattern: валидация, group_count, match(), кэширование
- WildcardPattern: matches()
- DSL функции w() и r()
"""

import re
from dataclasses import is_dataclass, FrozenInstanceError

import pytest

from valifold.pattern import (
    Pattern,
    BasePattern,
    RegexPattern,
    WildcardPattern,
    w,
    r,
)


class TestPurePattern:
    def test_pattern_protocol_instantiation(self):
        with pytest.raises(TypeError, check=lambda e: "Can't instantiate abstract class" in str(e)):
            Pattern()


class TestBasePattern:
    """Валидация BasePattern"""

    @pytest.mark.parametrize("pattern", [
        None,
        123,
        "",
        "test",
    ])
    def test_base_pattern_with_non_string_raises(self, pattern):
        """BasePattern с не-строкой выбрасывает TypeError"""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BasePattern(pattern=pattern)


class TestRegexPattern:
    """Валидация регулярных выражений"""

    @pytest.mark.parametrize("invalid_pattern", [
        r'[',  # Незакрытая скобка
        r'(?P<',  # Незаконченная именованная группа
        r'(?P<name',  # Незаконченная именованная группа
        r'*',  # Звездочка в начале
    ])
    def test_invalid_regex_patterns_raise(self, invalid_pattern):
        """Невалидные regex паттерны выбрасывают ValueError"""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            RegexPattern(invalid_pattern)

    def test_valid_complex_regex(self):
        """Сложный валидный regex создается успешно"""
        complex_pattern = r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\.txt$'
        pattern = RegexPattern(complex_pattern)

        assert pattern.pattern == complex_pattern
        assert pattern.group_count == 3

    def test_regex_compilation_internal_error(self):
        """Ошибка компиляции сохраняется в цепочке исключений"""
        try:
            RegexPattern(r'[invalid')
        except ValueError as e:
            assert "Invalid regex pattern" in str(e)
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, re.error)

    @pytest.mark.parametrize("pattern_str, expected_group_count", [
        (r'^(.+)\.txt$', 1),
        (r'^(\w+)_(\d+)\.jpg$', 2),
        (r'^(\w+)_(\d+)_([a-z]+)\.png$', 3),
        (r'^test\.txt$', 0),  # Нет групп
        (r'^(a)(b)(c)(d)(e)$', 5),  # Много групп
        (r'^(?:non_capture)_(.+)$', 1),  # Не-захватывающая + захватывающая
        (r'^(?P<name>\w+)\.txt$', 1),  # Именованная группа
        (r'^(?P<name>\w+)_(?P<num>\d+)$', 2),  # Две именованные
    ])
    def test_group_count_various_patterns(self, pattern_str, expected_group_count):
        """Подсчет групп в различных паттернах"""
        pattern = RegexPattern(pattern_str)
        assert pattern.group_count == expected_group_count

    @pytest.mark.parametrize("pattern_str, expected_group_count", [
        (r'^(.+)\.txt$', 1),
        (r'^(\w+)_(\d+)$', 2),
    ])
    def test_group_count_is_reentrant(self, pattern_str, expected_group_count):
        """group_count использует кэшированный _compiled"""
        pattern = RegexPattern(pattern_str)

        count1 = pattern.group_count
        assert hasattr(pattern, '_compiled')

        count2 = pattern.group_count
        assert count1 == count2 == expected_group_count

    def test_match_returns_match_object(self):
        """match() возвращает Match объект при совпадении"""
        pattern = RegexPattern(r'^(.+)\.txt$')
        result = pattern.match("test.txt")

        assert result is not None
        assert isinstance(result, re.Match)
        assert result.group(1) == "test"

    def test_match_returns_none_on_no_match(self):
        """match() возвращает None при несовпадении"""
        pattern = RegexPattern(r'^(.+)\.txt$')
        result = pattern.match("test.jpg")

        assert result is None

    @pytest.mark.parametrize("pattern_str,test_str,expected_groups", [
        (r'^(.+)\.txt$', "test.txt", ("test",)),
        (r'^(\w+)_(\d+)\.jpg$', "image_001.jpg", ("image", "001")),
        (r'^(\d{4})-(\d{2})-(\d{2})$', "2024-01-15", ("2024", "01", "15")),
    ])
    def test_match_captures_groups(self, pattern_str, test_str, expected_groups):
        """match() правильно захватывает группы"""
        pattern = RegexPattern(pattern_str)
        result = pattern.match(test_str)

        assert result is not None
        assert result.groups() == expected_groups

    def test_match_captures_named_groups(self):
        """match() с именованными группами"""
        pattern = RegexPattern(r'^(?P<name>\w+)_(?P<num>\d+)\.txt$')
        result = pattern.match("file_123.txt")

        assert result is not None
        assert result.group('name') == "file"
        assert result.group('num') == "123"

    def test_compiled_pattern_is_cached(self):
        """_compiled кэшируется"""
        pattern = RegexPattern(r'^test\.txt$')

        compiled1 = pattern._compiled
        compiled2 = pattern._compiled

        assert compiled1 is compiled2

    @pytest.mark.parametrize("pattern_str, test_str, expected", [
        ("test.*", "test.txt", True),
        ("test.*", "test.jpg", True),
        ("test.*", "other.txt", False),
        (r"^test\.txt$", "test.txt", True),
        (r"^test\.txt$", "test1.txt", False),
        (r"^test\.txt", "test.txt.bak", True),
        (r"^test\.txt$", "test.txt.bak", False),
        (r"^\d+\.jpg$", "001.jpg", True),
        (r"^\d+\.jpg$", "001.png", False),
        (r"^\d+\.jpg$", "abc.jpg", False),
        (r"^[12][0-9]\.[01][0-9]\.[0-3][0-9]\..*$", "21.06.15.anything", True),
        (r"^[12][0-9]\.[01][0-9]\.[0-3][0-9]\..*$", "99.99.99.test", False),
    ])
    def test_regex_matches(self, pattern_str, test_str, expected):
        pattern = RegexPattern(pattern_str)

        assert pattern.matches(test_str) == expected


class TestWildcardPatternMatches:
    """Тесты matches() для WildcardPattern"""

    @pytest.mark.parametrize("pattern_str, test_str, expected", [
        ("*.txt", "test.txt", True),
        ("*.txt", "document.txt", True),
        ("*.txt", "test.jpg", False),
        ("test.*", "test.txt", True),
        ("test.*", "test.jpg", True),
        ("test.*", "other.txt", False),
        ("file_???.jpg", "file_001.jpg", True),
        ("file_???.jpg", "file_01.jpg", False),
        ("file_??.jpg", "file_01.jpg", True),
        ("file_???.jpg", "file_abcd.jpg", False),
    ])
    def test_wildcard_matches(self, pattern_str, test_str, expected):
        """WildcardPattern.matches() работает корректно"""
        pattern = WildcardPattern(pattern_str)

        assert pattern.matches(test_str) == expected


class TestCommonForPatterns:
    @pytest.mark.parametrize("pattern_class", [
        RegexPattern,
        WildcardPattern,
    ])
    def test_subclasses_inheritance(self, pattern_class):
        assert issubclass(pattern_class, Pattern)
        assert issubclass(pattern_class, BasePattern)

        pattern = pattern_class(f"test")

        assert hasattr(pattern, "matches")
        assert callable(pattern.matches)

    @pytest.mark.parametrize("pattern", [
        None,
        123,
        [],
        {},
        set(),
    ])
    @pytest.mark.parametrize("pattern_class", [
        RegexPattern,
        WildcardPattern,
    ])
    def test_subclasses_invalid_pattern(self, pattern_class, pattern):
        with pytest.raises(TypeError, match="Pattern must be string"):
            pattern_class(pattern)

    @pytest.mark.parametrize("pattern_class", [
        RegexPattern,
        WildcardPattern,
    ])
    def test_subclasses_empty_pattern(self, pattern_class):
        assert issubclass(pattern_class, BasePattern)

        with pytest.raises(ValueError, match="Pattern must not be empty"):
            pattern_class("")

    @pytest.mark.parametrize("pattern_class", [
        RegexPattern,
        WildcardPattern,
    ])
    def test_immutability(self, pattern_class):
        assert is_dataclass(pattern_class)

        pattern_str = "test"
        pattern = pattern_class(pattern_str)

        with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
            pattern.pattern = ""

        assert pattern.pattern == pattern_str


class TestPatternEquivalence:
    @pytest.mark.parametrize("wildcard_pattern, regex_pattern, test_cases", [
        # Простые соответствия
        ("*.txt", r"^.*\.txt$", ["test.txt", "file.txt", "document.txt"]),
        ("test.*", r"^test\..*$", ["test.txt", "test.jpg", "test.png"]),
        ("file_???.jpg", r"^file_...\.jpg$", ["file_001.jpg", "file_abc.jpg", "file_xyz.jpg"]),

        # Специальные символы
        ("file[0-9].txt", r"^file[0-9]\.txt$", ["file1.txt", "file2.txt", "file3.txt"]),

        # Смешанные шаблоны
        ("*.*", r"^.*\..*$", ["test.txt", "image.jpg", "document.pdf"]),
    ])
    def test_wildcard_regex_equivalence(self, wildcard_pattern, regex_pattern, test_cases):
        """Тест на эквивалентность wildcard и regex паттернов"""
        w_pattern = WildcardPattern(wildcard_pattern)
        r_pattern = RegexPattern(regex_pattern)

        for test_string in test_cases:
            w_result = w_pattern.matches(test_string)
            r_result = r_pattern.matches(test_string)

            # Оба паттерна должны давать одинаковый результат
            assert w_result == r_result, \
                f"Несоответствие для '{test_string}': " \
                f"WildcardPattern('{wildcard_pattern}') = {w_result}, " \
                f"RegexPattern('{regex_pattern}') = {r_result}"


class TestDSLFunctions:
    """Тесты DSL функций w() и r()"""

    def test_w_creates_wildcard_pattern(self):
        """w() создает WildcardPattern"""
        pattern = w("*.txt")

        assert isinstance(pattern, WildcardPattern)

    def test_r_creates_regex_pattern(self):
        """r() создает RegexPattern"""
        pattern = r(r'^test\.txt$')

        assert isinstance(pattern, RegexPattern)

    @pytest.mark.parametrize("pattern_str", [
        "*.txt",
        "test.*",
        "file_???.jpg",
        "*",
        "?",
    ])
    def test_w_with_various_patterns(self, pattern_str):
        """w() с различными паттернами"""
        pattern = w(pattern_str)

        assert pattern.pattern == pattern_str

    @pytest.mark.parametrize("pattern_str", [
        r'^test\.txt$',
        r'^\d+\.jpg$',
        r'^.*$',
        r'^$',
        r'^(.+)\.txt$',
    ])
    def test_r_with_various_patterns(self, pattern_str):
        """r() с различными паттернами"""
        pattern = r(pattern_str)

        assert pattern.pattern == pattern_str


class TestPatternEdgeCases:
    """Граничные случаи"""

    def test_regex_pattern_empty_string(self):
        """RegexPattern с пустой строкой"""
        pattern = RegexPattern(r'^$')

        assert pattern.matches("")
        assert not pattern.matches("a")


    def test_regex_pattern_match_any(self):
        """RegexPattern совпадающий с любой строкой"""
        pattern = RegexPattern(r'^.*$')

        assert pattern.matches("")
        assert pattern.matches("test")
        assert pattern.matches("any string")

    def test_wildcard_pattern_match_any(self):
        """WildcardPattern совпадающий с любой строкой"""
        pattern = WildcardPattern("*")

        assert pattern.matches("")
        assert pattern.matches("test")
        assert pattern.matches("any string")

    @pytest.mark.parametrize("pattern_class, pattern_str", [
        (RegexPattern, r"^$"),  # Пустая строка
        (RegexPattern, r"^.*$"),  # Любая строка
        (RegexPattern, r"^a{0}$"),  # Ноль повторений
        # (WildcardPattern, ""), # Пустой паттерн
        (WildcardPattern, "*"),  # Любая строка
        (WildcardPattern, "?"),  # Ровно один символ
    ])
    def test_edge_case_patterns(self, pattern_class, pattern_str):
        """Тест паттернов с краевыми значениями"""
        pattern = pattern_class(pattern_str)

        # Проверяем, что паттерн создается без ошибок
        assert pattern is not None

        # Проверяем некоторые базовые случаи
        if pattern_str == "":
            assert pattern.matches("")
            assert not pattern.matches("a")
        elif pattern_str in (r"^.*$", "*"):
            assert pattern.matches("")
            assert pattern.matches("test")
            assert pattern.matches("file.txt")

    @pytest.mark.parametrize("test_string", [
        "",  # Пустая строка
        ".",  # Только точка
        "..",  # Две точки
        " ",  # Пробел
        "  ",  # Два пробела
        "file with spaces.txt",  # Пробелы в имени
        "file.with.many.dots.txt",  # Много точек
        "UPPERCASE.TXT",  # Верхний регистр
        "MixedCase.File",  # Смешанный регистр
        "file_with_underscore.txt",  # Подчеркивания
        "file-with-dash.txt",  # Дефисы
        "file@special#chars.txt",  # Спецсимволы
        "file(1).txt",  # Скобки
        "file[1].txt",  # Квадратные скобки
        "file{1}.txt",  # Фигурные скобки
    ])
    def test_special_characters_in_strings(self, test_string):
        """Тест паттернов на строках со специальными символами"""
        # WildcardPattern с *
        w_pattern = WildcardPattern("*")
        assert w_pattern.matches(test_string)

        # RegexPattern с .*
        r_pattern = RegexPattern(r"^.*$")
        assert r_pattern.matches(test_string)


# performance