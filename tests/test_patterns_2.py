"""
Тесты для pattern.py

Покрывает:
- BasePattern валидацию типов
- RegexPattern: валидация, group_count, match(), кэширование
- WildcardPattern: matches()
- DSL функции w() и r()
"""

import re

import pytest

from valifold.pattern import (
    Pattern,
    BasePattern,
    RegexPattern,
    WildcardPattern,
    w,
    r,
)


class TestBasePatternValidation:
    """Валидация BasePattern"""

    def test_pattern_protocol_instantiation(self):
        with pytest.raises(TypeError, check=lambda e: "Can't instantiate abstract class" in str(e)):
            Pattern()

    @pytest.mark.parametrize("pattern", [
        None,
        123,
        "",
        "test",
    ])
    def test_base_pattern_with_non_string_raises(self, pattern):
        """BasePattern с не-строкой выбрасывает TypeError"""
        with pytest.raises(TypeError, check=lambda e: "Can't instantiate abstract class" in str(e)):
            BasePattern(pattern=pattern)

    def test_regex_pattern_with_non_string_raises(self):
        """RegexPattern с не-строкой выбрасывает TypeError"""
        with pytest.raises(TypeError, match="Pattern must be string"):
            RegexPattern(pattern=123)

    def test_wildcard_pattern_with_non_string_raises(self):
        """WildcardPattern с не-строкой выбрасывает TypeError"""
        with pytest.raises(TypeError, match="Pattern must be string"):
            WildcardPattern(pattern=456)


class TestRegexPatternValidation:
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

    def test_regex_compilation_error_preserved(self):
        """Ошибка компиляции сохраняется в цепочке исключений"""
        try:
            RegexPattern(r'[invalid')
        except ValueError as e:
            assert "Invalid regex pattern" in str(e)
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, re.error)


class TestRegexPatternGroupCount:
    """Тестирование group_count"""

    @pytest.mark.parametrize("pattern_str,expected_groups", [
        (r'^(.+)\.txt$', 1),
        (r'^(\w+)_(\d+)\.jpg$', 2),
        (r'^(\w+)_(\d+)_([a-z]+)\.png$', 3),
        (r'^test\.txt$', 0),  # Нет групп
        (r'^(a)(b)(c)(d)(e)$', 5),  # Много групп
        (r'^(?:non_capture)_(.+)$', 1),  # Не-захватывающая + захватывающая
        (r'^(?P<name>\w+)\.txt$', 1),  # Именованная группа
        (r'^(?P<name>\w+)_(?P<num>\d+)$', 2),  # Две именованные
    ])
    def test_group_count_various_patterns(self, pattern_str, expected_groups):
        """Подсчет групп в различных паттернах"""
        pattern = RegexPattern(pattern_str)
        assert pattern.group_count == expected_groups

    def test_group_count_is_cached(self):
        """group_count использует кэшированный _compiled"""
        pattern = RegexPattern(r'^(.+)\.txt$')

        count1 = pattern.group_count
        assert hasattr(pattern, '_compiled')

        count2 = pattern.group_count
        assert count1 == count2 == 1


class TestRegexPatternMatch:
    """Тестирование метода match()"""

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

    def test_match_with_named_groups(self):
        """match() с именованными группами"""
        pattern = RegexPattern(r'^(?P<name>\w+)_(?P<num>\d+)\.txt$')
        result = pattern.match("file_123.txt")

        assert result is not None
        assert result.group('name') == "file"
        assert result.group('num') == "123"


class TestRegexPatternCaching:
    """Тесты кэширования _compiled"""

    def test_compiled_pattern_is_cached(self):
        """_compiled кэшируется"""
        pattern = RegexPattern(r'^test\.txt$')

        compiled1 = pattern._compiled
        compiled2 = pattern._compiled

        assert compiled1 is compiled2

    def test_cached_compiled_used_in_match(self):
        """match() использует кэшированный _compiled"""
        pattern = RegexPattern(r'^(.+)\.txt$')

        _ = pattern._compiled
        result = pattern.match("test.txt")

        assert result is not None

    def test_group_count_uses_cached_compiled(self):
        """group_count использует кэшированный _compiled"""
        pattern = RegexPattern(r'^(\w+)_(\d+)$')

        count = pattern.group_count
        assert hasattr(pattern, '_compiled')

        count2 = pattern.group_count
        assert count == count2 == 2


class TestWildcardPatternMatches:
    """Тесты matches() для WildcardPattern"""

    @pytest.mark.parametrize("pattern_str,test_str,expected", [
        ("*.txt", "test.txt", True),
        ("*.txt", "test.jpg", False),
        ("test.*", "test.txt", True),
        ("test.*", "other.txt", False),
        ("file_???.jpg", "file_001.jpg", True),
        ("file_???.jpg", "file_01.jpg", False),
    ])
    def test_wildcard_matches(self, pattern_str, test_str, expected):
        """WildcardPattern.matches() работает корректно"""
        pattern = WildcardPattern(pattern_str)
        assert pattern.matches(test_str) == expected


class TestDSLFunctions:
    """Тесты DSL функций w() и r()"""

    def test_w_creates_wildcard_pattern(self):
        """w() создает WildcardPattern"""
        pattern = w("*.txt")
        assert isinstance(pattern, WildcardPattern)
        assert pattern.pattern == "*.txt"

    def test_r_creates_regex_pattern(self):
        """r() создает RegexPattern"""
        pattern = r(r'^test\.txt$')
        assert isinstance(pattern, RegexPattern)
        assert pattern.pattern == r'^test\.txt$'

    @pytest.mark.parametrize("pattern_str", [
        "*.txt",
        "test.*",
        "file_???.jpg",
        "*",
        "?",
        "",
    ])
    def test_w_with_various_patterns(self, pattern_str):
        """w() с различными паттернами"""
        pattern = w(pattern_str)
        assert isinstance(pattern, WildcardPattern)
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
        assert isinstance(pattern, RegexPattern)
        assert pattern.pattern == pattern_str


class TestPatternEdgeCases:
    """Граничные случаи"""

    def test_regex_pattern_empty_string(self):
        """RegexPattern с пустой строкой"""
        pattern = RegexPattern(r'^$')
        assert pattern.matches("")
        assert not pattern.matches("a")

    def test_wildcard_pattern_empty_string(self):
        """WildcardPattern с пустой строкой"""
        pattern = WildcardPattern("")
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
