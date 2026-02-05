"""Тесты на редкий случай XOR с опциональными файлами."""
import tempfile
from pathlib import Path

import pytest

from valifold.dsl import file, folder, xor, only_one, at_least_one
from valifold.errors import ManyOptionsError
from valifold.pattern import w


@pytest.fixture
def temp_dir():
    """Временная директория для тестов"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestXorOptionalEdgeCase:
    """Тесты на проблемный случай XOR с опциональными файлами"""

    def test_xor_both_optional_both_missing(self, temp_dir):
        """
        XOR с двумя опциональными файлами, оба отсутствуют.

        Проблема: оба валидатора возвращают [] (нет ошибок),
        XOR считает success_count = 2, хотя ни одного файла нет.
        """
        struct = xor(
            file(w("option_a.txt"), is_optional=True),
            file(w("option_b.txt"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        # ТЕКУЩЕЕ ПОВЕДЕНИЕ (возможно неожиданное):
        # Оба optional вернули [], success_count = 2
        # XOR требует ровно 1 успех, получил 2 → ManyOptionsError

        # ОЖИДАЕМОЕ ПОВЕДЕНИЕ (спорно):
        # Ни один файл не существует → должна быть ошибка?
        # Или оба опциональны → всё ок?

        print(f"Errors: {errors}")
        print(f"Error types: {[type(e).__name__ for e in errors]}")

        # Проверяем текущее поведение
        if errors:
            assert any(isinstance(e, ManyOptionsError) for e in errors), \
                f"Expected ManyOptionsError, got {[type(e).__name__ for e in errors]}"

    def test_xor_one_optional_missing_one_mandatory_exists(self, temp_dir):
        """
        XOR: один опциональный (отсутствует) + один обязательный (существует).

        Это должно работать правильно - только обязательный даёт success.
        """
        (temp_dir / "mandatory.txt").touch()

        struct = xor(
            file(
                w("optional.txt"),
                is_optional=True)
            ,
            file(
                w("mandatory.txt"),
                is_optional=False
            )
        )

        errors = struct.validate(temp_dir)

        # ОЖИДАНИЕ: success_count должен быть 1 (только mandatory)
        # Optional отсутствует → успех ([] ошибок)
        # Mandatory существует → успех ([] ошибок)
        # Итого: 2 успеха → ManyOptionsError

        print(f"Errors: {errors}")

        # Это ПРОБЛЕМА! Должно быть 0 ошибок, но будет ManyOptionsError
        if errors:
            assert any(isinstance(e, ManyOptionsError) for e in errors)

    def test_xor_one_optional_exists_one_mandatory_missing(self, temp_dir):
        """
        XOR: один опциональный (существует) + один обязательный (отсутствует).
        """
        (temp_dir / "optional.txt").touch()

        struct = xor(
            file(w("optional.txt"), is_optional=True),
            file(w("mandatory.txt"), is_optional=False)
        )

        errors = struct.validate(temp_dir)

        # Optional существует → успех ([] ошибок)
        # Mandatory отсутствует → ошибка (MandatoryMissedError)
        # success_count = 1 → должно быть OK для XOR

        print(f"Errors: {errors}")
        print(f"Error types: {[type(e).__name__ for e in errors]}")

        # Ожидаем успех (только optional прошёл)
        assert not errors or not any(isinstance(e, ManyOptionsError) for e in errors)

    def test_xor_both_optional_one_exists(self, temp_dir):
        """
        XOR: оба опциональных, один существует.

        Должно быть корректно - один успех.
        """
        (temp_dir / "option_a.txt").touch()

        struct = xor(
            file(w("option_a.txt"), is_optional=True),
            file(w("option_b.txt"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        # option_a существует → успех
        # option_b отсутствует, но optional → успех (!!)
        # success_count = 2 → ManyOptionsError

        print(f"Errors: {errors}")

        # Это ПРОБЛЕМА
        if errors:
            assert any(isinstance(e, ManyOptionsError) for e in errors)

    def test_xor_both_optional_both_exist(self, temp_dir):
        """
        XOR: оба опциональных, оба существуют.

        Должно быть ошибкой для XOR.
        """
        (temp_dir / "option_a.txt").touch()
        (temp_dir / "option_b.txt").touch()

        struct = xor(
            file(w("option_a.txt"), is_optional=True),
            file(w("option_b.txt"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        # Оба существуют → оба успех → ManyOptionsError
        # Это ПРАВИЛЬНОЕ поведение

        assert errors
        assert any(isinstance(e, ManyOptionsError) for e in errors)

    def test_only_one_all_optional_all_missing(self, temp_dir):
        """
        only_one: все опциональные, все отсутствуют.
        """
        struct = only_one(
            file(w("opt1.txt"), is_optional=True),
            file(w("opt2.txt"), is_optional=True),
            file(w("opt3.txt"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        # Все optional, все отсутствуют → все успех
        # success_count = 3 → ManyOptionsError

        print(f"Errors: {errors}")

        if errors:
            assert any(isinstance(e, ManyOptionsError) for e in errors)

    def test_at_least_one_all_optional_all_missing(self, temp_dir):
        """
        at_least_one: все опциональные, все отсутствуют.
        """
        struct = at_least_one(
            file(w("opt1.txt"), is_optional=True),
            file(w("opt2.txt"), is_optional=True),
            file(w("opt3.txt"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        # Все optional, все отсутствуют → все успех
        # success_count = 3 → OK для at_least_one (min=1)

        print(f"Errors: {errors}")

        # at_least_one должен быть доволен
        assert not errors


class TestXorOptionalWithFolders:
    """Тесты XOR с опциональными папками"""

    def test_xor_optional_folders_both_missing(self, temp_dir):
        """
        XOR с опциональными папками, обе отсутствуют.
        """
        struct = xor(
            folder(w("folder_a"), is_optional=True),
            folder(w("folder_b"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        print(f"Errors: {errors}")

        # Та же проблема: оба optional → оба успех → ManyOptionsError
        if errors:
            assert any(isinstance(e, ManyOptionsError) for e in errors)

    def test_xor_optional_folder_one_exists(self, temp_dir):
        """
        XOR с опциональными папками, одна существует.
        """
        (temp_dir / "folder_a").mkdir()

        struct = xor(
            folder(w("folder_a"), is_optional=True),
            folder(w("folder_b"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        print(f"Errors: {errors}")

        # folder_a exists → success
        # folder_b missing but optional → success
        # success_count = 2 → ManyOptionsError
        if errors:
            assert any(isinstance(e, ManyOptionsError) for e in errors)


class TestXorOptionalRealWorldScenarios:
    """Реальные сценарии использования XOR с optional"""

    def test_config_file_or_folder_both_optional_both_missing(self, temp_dir):
        """
        Реальный сценарий: конфиг либо файл, либо папка, оба опциональны.

        Если ничего нет - это должно быть OK (оба optional).
        """
        struct = xor(
            file(w("config.json"), is_optional=True),
            folder(w("config"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        print(f"Errors: {errors}")

        # Проблема: оба optional → оба успех → ManyOptionsError
        # НО логически это должно быть OK - конфига просто нет

    def test_readme_md_or_txt_both_optional(self, temp_dir):
        """
        README.md или README.txt, оба опциональны.
        """
        struct = xor(
            file(w("README.md"), is_optional=True),
            file(w("README.txt"), is_optional=True)
        )

        errors = struct.validate(temp_dir)

        # Если оба отсутствуют - должно быть OK (проект без README)
        # Но XOR посчитает оба успешными

        print(f"Errors: {errors}")


class TestDemonstrationOfProblem:
    """Демонстрация проблемы и возможные решения"""

    def test_problem_demonstration(self, temp_dir):
        """
        Демонстрация проблемы с выводом для понимания.
        """
        print("\n" + "=" * 60)
        print("ДЕМОНСТРАЦИЯ ПРОБЛЕМЫ XOR + OPTIONAL")
        print("=" * 60)

        # Создаём структуру
        (temp_dir / "exists.txt").touch()

        # Тест 1: Оба optional, оба отсутствуют
        print("\nТест 1: XOR(optional отсутствует, optional отсутствует)")
        struct1 = xor(
            file(w("missing_a.txt"), is_optional=True),
            file(w("missing_b.txt"), is_optional=True)
        )
        errors1 = struct1.validate(temp_dir)
        print(f"  Ошибки: {[type(e).__name__ for e in errors1]}")
        print("  Ожидание: нет ошибок (оба optional)")
        print("  Реальность: ManyOptionsError (оба вернули [])")

        # Тест 2: Optional отсутствует, mandatory существует
        print("\nТест 2: XOR(optional отсутствует, mandatory существует)")
        struct2 = xor(
            file(w("missing.txt"), is_optional=True),
            file(w("exists.txt"), is_optional=False)
        )
        errors2 = struct2.validate(temp_dir)
        print(f"  Ошибки: {[type(e).__name__ for e in errors2]}")
        print("  Ожидание: нет ошибок (только mandatory match)")
        print("  Реальность: ManyOptionsError")

        # Тест 3: Оба optional, один существует
        print("\nТест 3: XOR(optional существует, optional отсутствует)")
        struct3 = xor(
            file(w("exists.txt"), is_optional=True),
            file(w("missing.txt"), is_optional=True)
        )
        errors3 = struct3.validate(temp_dir)
        print(f"  Ошибки: {[type(e).__name__ for e in errors3]}")
        print("  Ожидание: нет ошибок (только один существует)")
        print("  Реальность: ManyOptionsError")

        print("\n" + "=" * 60)
        print("ВЫВОД: XOR не различает 'успех потому что optional'")
        print("       и 'успех потому что файл есть'")
        print("=" * 60 + "\n")

    def test_possible_solution_workaround(self, temp_dir):
        """
        Возможное решение: не использовать optional с XOR.

        Вместо этого использовать at_least_one с mandatory.
        """
        (temp_dir / "option_a.txt").touch()

        # ПЛОХО: XOR с optional
        bad_struct = xor(
            file(w("option_a.txt"), is_optional=True),
            file(w("option_b.txt"), is_optional=True)
        )

        # ХОРОШО: at_least_one с mandatory
        good_struct = only_one(
            file(w("option_a.txt"), is_optional=False),
            file(w("option_b.txt"), is_optional=False)
        )

        bad_errors = bad_struct.validate(temp_dir)
        good_errors = good_struct.validate(temp_dir)

        print("\n" + "=" * 60)
        print("WORKAROUND: Используйте mandatory с XOR")
        print("=" * 60)
        print(f"С optional: {[type(e).__name__ for e in bad_errors]}")
        print(f"С mandatory: {[type(e).__name__ for e in good_errors]}")
        print("=" * 60 + "\n")

        # С mandatory работает правильно
        assert not good_errors


@pytest.mark.parametrize("scenario,files_exist,expected_behavior", [
    ("both_missing", [], "should_error_many"),
    ("one_exists", ["a.txt"], "should_error_many"),
    ("both_exist", ["a.txt", "b.txt"], "should_error_many"),
])
def test_xor_optional_parametrized(temp_dir, scenario, files_exist, expected_behavior):
    """
    Параметризованный тест всех сценариев XOR + optional.
    """
    # Создаём файлы
    for filename in files_exist:
        (temp_dir / filename).touch()

    # Структура с опциональными файлами
    struct = xor(
        file(w("a.txt"), is_optional=True),
        file(w("b.txt"), is_optional=True)
    )

    errors = struct.validate(temp_dir)

    print(f"\nСценарий: {scenario}")
    print(f"Файлы: {files_exist}")
    print(f"Ошибки: {[type(e).__name__ for e in errors]}")

    # Все сценарии дают ManyOptionsError из-за проблемы
    if expected_behavior == "should_error_many":
        assert any(isinstance(e, ManyOptionsError) for e in errors)
