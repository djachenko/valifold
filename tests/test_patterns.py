import pytest

from valifold.dsl import file, folder
from valifold.pattern import RegexPattern, WildcardPattern, w, r, Pattern


# ============ ТЕСТЫ НА БАЗОВОЕ ПОВЕДЕНИЕ ============

@pytest.mark.parametrize(
    "pattern_class, pattern_str", [
        (RegexPattern, r"^test\.txt$",),
        (WildcardPattern, "test.txt",),
    ])
def test_pattern_protocol(pattern_class, pattern_str):
    """Тест, что оба класса реализуют протокол Pattern"""
    # Просто создаем экземпляры - если они создаются, значит, протокол соблюден

    pattern = pattern_class(pattern_str)

    assert isinstance(pattern, Pattern)
    assert hasattr(pattern, "matches")
    assert callable(pattern.matches)


@pytest.mark.parametrize("pattern_class, pattern_str, test_string, expected", [
    # RegexPattern тесты
    (RegexPattern, r"^test\.txt$", "test.txt", True),
    (RegexPattern, r"^test\.txt$", "test1.txt", False),
    (RegexPattern, r"^test\.txt", "test.txt.bak", True),
    (RegexPattern, r"^test\.txt$", "test.txt.bak", False),
    (RegexPattern, r"^\d+\.jpg$", "001.jpg", True),
    (RegexPattern, r"^\d+\.jpg$", "001.png", False),
    (RegexPattern, r"^\d+\.jpg$", "abc.jpg", False),
    (RegexPattern, r"^[12][0-9]\.[01][0-9]\.[0-3][0-9]\..*$", "21.06.15.anything", True),
    (RegexPattern, r"^[12][0-9]\.[01][0-9]\.[0-3][0-9]\..*$", "99.99.99.test", False),

    # WildcardPattern тесты
    (WildcardPattern, "*.txt", "test.txt", True),
    (WildcardPattern, "*.txt", "document.txt", True),
    (WildcardPattern, "*.txt", "test.jpg", False),
    (WildcardPattern, "test.*", "test.txt", True),
    (WildcardPattern, "test.*", "test.jpg", True),
    (WildcardPattern, "test.*", "other.txt", False),
    (WildcardPattern, "file_???.jpg", "file_001.jpg", True),
    (WildcardPattern, "file_???.jpg", "file_01.jpg", False),
    (WildcardPattern, "file_??.jpg", "file_01.jpg", True),
    (WildcardPattern, "file_???.jpg", "file_abcd.jpg", False),
])
def test_pattern_matching(pattern_class, pattern_str, test_string, expected):
    """Параметризованный тест соответствия паттернов"""
    pattern = pattern_class(pattern_str)

    result = pattern.matches(test_string)

    assert result == expected, \
        f"{pattern_class.__name__}('{pattern_str}').matches('{test_string}') = {result}, ожидалось {expected}"


# ============ ТЕСТЫ НА ВЗАИМОЗАМЕНЯЕМОСТЬ ============

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
def test_wildcard_regex_equivalence(wildcard_pattern, regex_pattern, test_cases):
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


# ============ ТЕСТЫ НА КРАЕВЫЕ СЛУЧАИ ============

@pytest.mark.parametrize("pattern_class, pattern_str", [
    (RegexPattern, r"^$"),  # Пустая строка
    (RegexPattern, r"^.*$"),  # Любая строка
    (RegexPattern, r"^a{0}$"),  # Ноль повторений
    (WildcardPattern, ""),  # Пустой паттерн
    (WildcardPattern, "*"),  # Любая строка
    (WildcardPattern, "?"),  # Ровно один символ
])
def test_edge_case_patterns(pattern_class, pattern_str):
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
def test_special_characters_in_strings(test_string):
    """Тест паттернов на строках со специальными символами"""
    # WildcardPattern с *
    w_pattern = WildcardPattern("*")
    assert w_pattern.matches(test_string)

    # RegexPattern с .*
    r_pattern = RegexPattern(r"^.*$")
    assert r_pattern.matches(test_string)


# ============ ТЕСТЫ НА ИММУТАБЕЛЬНОСТЬ ============

def test_pattern_immutability():
    """Тест, что паттерны неизменяемы (frozen dataclass)"""
    import dataclasses

    # Проверяем, что это frozen dataclass
    assert dataclasses.is_dataclass(RegexPattern)
    assert dataclasses.is_dataclass(WildcardPattern)

    # Пытаемся изменить поле - должно вызывать исключение
    regex = RegexPattern(r"^test$")

    try:
        regex.pattern = " "

        assert False
    except AttributeError:
        assert True

    # Проверяем, что паттерн можно использовать многократно
    assert regex.matches("test")
    assert regex.matches("test")  # Повторный вызов
    assert not regex.matches("other")

    # Убеждаемся, что внутреннее состояние не меняется
    pattern_str_before = regex.pattern
    regex.matches("test")
    assert regex.pattern == pattern_str_before


# ============ ИНТЕГРАЦИОННЫЕ ТЕСТЫ С СТРУКТУРАМИ ============

def test_patterns_in_folder_structure():
    """Тест использования паттернов в структурах Folder"""

    # Создаем структуру с разными типами паттернов
    struct = folder(
        w("*"),
        file(
            w("*.jpg"),
            is_optional=True
        ),
        file(
            r(r"^_\w+\.json$"),
            is_optional=False
        ),
        file(
            w("data_??.txt"),
            is_optional=True
        ),
    )

    # Проверяем, что структура создана корректно
    assert len(struct.children) == 3

    # Проверяем типы паттернов в структуре
    for child in struct.children:
        assert hasattr(child, 'matches')
        assert callable(child.matches)


@pytest.mark.parametrize("pattern_maker, pattern_args, test_cases", [
    # DSL функция w()
    (w, ("*.txt",), [
        ("test.txt", True),
        ("document.txt", True),
        ("test.jpg", False),
        ("txt", False),
    ]),

    # DSL функция r()
    (r, (r"^\d+\.jpg$",), [
        ("001.jpg", True),
        ("123.jpg", True),
        ("abc.jpg", False),
        ("001.png", False),
    ]),

    # Составные паттерны для фотосетов
    (r, (r"^[12][0-9]\.[01][0-9]\.[0-3][0-9]\..*$",), [
        ("21.06.15.beach_photos", True),
        ("21.06.15.beach", True),
        ("99.99.99.test", False),
        ("21.06.15", False),
    ]),
])
def test_dsl_functions(pattern_maker, pattern_args, test_cases):
    """Тест DSL функций w() и r()"""
    pattern = pattern_maker(*pattern_args)

    for test_string, expected in test_cases:
        result = pattern.matches(test_string)
        assert result == expected, \
            f"{pattern_maker.__name__}{pattern_args}.matches('{test_string}') = {result}, ожидалось {expected}"


# ============ ТЕСТЫ НА ПРОИЗВОДИТЕЛЬНОСТЬ ============

def test_pattern_performance():
    """Тест производительности паттернов (без реального бенчмарка)"""
    import time

    # Создаем паттерны
    w_patterns = [WildcardPattern(f"file_{i:03d}.*") for i in range(100)]
    r_patterns = [RegexPattern(f"^file_{i:03d}\\..*$") for i in range(100)]

    # Тестируем WildcardPattern
    start = time.time()
    for i in range(100):
        for pattern in w_patterns:
            pattern.matches(f"file_{i:03d}.txt")
    w_time = time.time() - start

    # Тестируем RegexPattern
    start = time.time()
    for i in range(100):
        for pattern in r_patterns:
            pattern.matches(f"file_{i:03d}.txt")
    r_time = time.time() - start

    # Выводим результаты для информации
    print("\nПроизводительность паттернов:")
    print(f"WildcardPattern: {w_time:.4f} сек")
    print(f"RegexPattern: {r_time:.4f} сек")

    # Убеждаемся, что оба работают за разумное время
    assert w_time < 1.0, f"WildcardPattern слишком медленный: {w_time:.4f} сек"
    assert r_time < 1.0, f"RegexPattern слишком медленный: {r_time:.4f} сек"


# ============ ТЕСТЫ НА КОНСИСТЕНТНОСТЬ ============

def test_pattern_consistency():
    """Тест, что одинаковые паттерны ведут себя одинаково"""
    # Создаем несколько экземпляров одного паттерна
    w1 = WildcardPattern("*.txt")
    w2 = WildcardPattern("*.txt")
    w3 = w("*.txt")  # Через DSL

    r1 = RegexPattern(r"^.*\.txt$")
    r2 = RegexPattern(r"^.*\.txt$")
    r3 = r(r"^.*\.txt$")  # Через DSL

    test_strings = ["test.txt", "document.txt", "file.jpg", "archive.tar.gz"]

    # Проверяем консистентность WildcardPattern
    for test_str in test_strings:
        results = [p.matches(test_str) for p in (w1, w2, w3)]
        assert all(r == results[0] for r in results), \
            f"Несогласованность WildcardPattern для '{test_str}': {results}"

    # Проверяем консистентность RegexPattern
    for test_str in test_strings:
        results = [p.matches(test_str) for p in (r1, r2, r3)]
        assert all(r == results[0] for r in results), \
            f"Несогласованность RegexPattern для '{test_str}': {results}"


# ============ ТЕСТЫ НА ОШИБОЧНЫЕ СЛУЧАИ ============

def test_invalid_regex_pattern():
    """Тест обработки некорректных regex паттернов"""
    # Некорректный regex - неполная группа
    pattern = RegexPattern(r"^test[0-9]$")
    # Должен создаться без ошибок, но может не работать как ожидается
    assert pattern is not None

    # Более опасный случай - неправильный синтаксис
    with pytest.raises(ValueError):
        pattern = RegexPattern(r"^test[0-$")  # Некорректный диапазон
        # Если создался, проверяем, что не падает при использовании
        _ = pattern.matches("test1")
        # Результат может быть любым, главное - не исключение


def test_pattern_repr():
    """Тест строкового представления паттернов"""
    w_pattern = WildcardPattern("*.txt")
    r_pattern = RegexPattern(r"^.*\.txt$")

    # Проверяем, что repr работает
    assert repr(w_pattern) == "WildcardPattern(pattern='*.txt')"
    assert repr(r_pattern) == "RegexPattern(pattern='^.*\\\\.txt$')"

    # Проверяем, что паттерны можно сравнить (как строки)
    assert "*.txt" in str(w_pattern)
    assert "^.*\\\\.txt$" in str(r_pattern)
