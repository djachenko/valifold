import tempfile
from pathlib import Path

import pytest

from src.errors import (
    MandatoryMissedError, NotFileError, NotDirectoryError,
    NoSidecarError, AllValidationsFailedError, FewOptionsError,
    ManyOptionsError, ExtraItemsError
)
from src.functions import file, folder, sidecar, xor, only_one, at_least_one, anything
from src.pattern import w, r


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============ ТЕСТЫ НА ФАЙЛ ============

class TestFile:
    """Тесты валидатора file()"""

    def test_file_exists_is_file(self, temp_dir):
        """Файл существует и это файл"""
        name = "test.txt"
        test_file = temp_dir / name
        test_file.touch()

        struct = file(w(name))

        assert not struct.validate_as_root(test_file)

    def test_file_exists_is_not_file(self, temp_dir):
        """Файл существует, но это не файл (а директория)"""
        name = "test.txt"
        test_path = temp_dir / name
        test_path.mkdir()

        struct = file(w(name))
        result = struct.validate_as_root(test_path)

        assert result
        assert any(isinstance(error, NotFileError) for error in result)

    def test_file_not_exists_mandatory(self, temp_dir):
        """Файл не существует и обязательный"""
        name = "test.txt"
        test_file = temp_dir / name

        struct = file(w(name))
        result = struct.validate_as_root(test_file)

        assert result
        assert any(isinstance(error, MandatoryMissedError) for error in result)

    def test_file_not_exists_optional(self, temp_dir):
        """Файл не существует, но опциональный"""
        name = "test.txt"
        test_file = temp_dir / name

        struct = file(w(name), is_mandatory=False)

        assert not struct.validate_as_root(test_file)


# ============ ТЕСТЫ НА ПАПКУ ============

class TestFolder:
    """Тесты валидатора folder()"""

    def test_folder_exists_is_folder(self, temp_dir):
        """Папка существует и это папка"""
        name = "test_folder"
        test_folder = temp_dir / name
        test_folder.mkdir()

        struct = folder(w(name))

        assert not struct.validate_as_root(test_folder)

    def test_folder_exists_is_not_folder(self, temp_dir):
        """Папка существует, но это не папка (а файл)"""
        name = "test_folder"
        test_path = temp_dir / name
        test_path.touch()

        struct = folder(w(name))
        result = struct.validate_as_root(test_path)

        assert result
        assert any(isinstance(error, NotDirectoryError) for error in result)

    def test_folder_not_exists_mandatory(self, temp_dir):
        """Папка не существует и обязательная"""
        name = "test_folder"
        test_folder = temp_dir / name

        struct = folder(w(name))
        result = struct.validate_as_root(test_folder)

        assert result
        assert any(isinstance(error, MandatoryMissedError) for error in result)

    def test_folder_not_exists_optional(self, temp_dir):
        """Папка не существует, но опциональная"""
        name = "test_folder"
        test_folder = temp_dir / name

        struct = folder(w(name), is_mandatory=False)

        assert not struct.validate_as_root(test_folder)


# ============ ТЕСТЫ НА SIDECAR ============

class TestSidecar:
    """Тесты валидатора sidecar()"""

    def test_sidecar_exists_for_each(self, temp_dir):
        """Для каждого основного файла есть sidecar"""
        (temp_dir / "image_001.jpg").touch()
        (temp_dir / "image_001.json").touch()
        (temp_dir / "image_002.jpg").touch()
        (temp_dir / "image_002.json").touch()

        struct = sidecar(
            main_pattern=r(r'^image_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^image_(\d+)\.json$')
        )

        assert not struct.validate(temp_dir)

    def test_sidecar_has_extra(self, temp_dir):
        """Есть лишние sidecar файлы (без основных)"""
        (temp_dir / "image_001.jpg").touch()
        (temp_dir / "image_001.json").touch()
        (temp_dir / "image_002.json").touch()  # Лишний
        (temp_dir / "image_003.json").touch()  # Лишний

        struct = sidecar(
            main_pattern=r(r'^image_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^image_(\d+)\.json$')
        )

        # Лишние sidecar не являются ошибкой
        assert not struct.validate(temp_dir)

    def test_sidecar_missing_some(self, temp_dir):
        """Не хватает некоторых sidecar файлов"""
        (temp_dir / "image_001.jpg").touch()
        (temp_dir / "image_001.json").touch()
        (temp_dir / "image_002.jpg").touch()  # Без sidecar
        (temp_dir / "image_003.jpg").touch()  # Без sidecar

        struct = sidecar(
            main_pattern=r(r'^image_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^image_(\d+)\.json$')
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, NoSidecarError) for error in result)
        # Проверяем, что в ошибке упомянуты правильные файлы
        sidecar_errors = [e for e in result if isinstance(e, NoSidecarError)]
        assert len(sidecar_errors) == 1
        assert len(sidecar_errors[0].paths) == 2

    def test_sidecar_missing_all(self, temp_dir):
        """Не хватает вообще всех sidecar файлов"""
        (temp_dir / "image_001.jpg").touch()
        (temp_dir / "image_002.jpg").touch()
        (temp_dir / "image_003.jpg").touch()

        struct = sidecar(
            main_pattern=r(r'^image_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^image_(\d+)\.json$')
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, NoSidecarError) for error in result)
        sidecar_errors = [e for e in result if isinstance(e, NoSidecarError)]
        assert len(sidecar_errors[0].paths) == 3

    def test_sidecar_no_main_files(self, temp_dir):
        """Нет основных файлов, только sidecar"""
        (temp_dir / "image_001.json").touch()
        (temp_dir / "image_002.json").touch()

        struct = sidecar(
            main_pattern=r(r'^image_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^image_(\d+)\.json$')
        )

        # Нет основных файлов - нет ошибок
        assert not struct.validate(temp_dir)

    def test_sidecar_no_groups_in_patterns(self):
        """Нет групп в паттернах - ошибка при создании"""
        with pytest.raises(ValueError):
            sidecar(
                main_pattern=r(r'^image\.jpg$'),  # Нет групп
                sidecar_pattern=r(r'^image\.json$')
            )

    def test_sidecar_different_group_count(self):
        """Разное количество групп в паттернах - ошибка при создании"""
        with pytest.raises(ValueError):
            sidecar(
                main_pattern=r(r'^image_(\d+)\.jpg$'),  # 1 группа
                sidecar_pattern=r(r'^image_(\d+)_(\d+)\.json$')  # 2 группы
            )

    def test_sidecar_multiple_groups(self, temp_dir):
        """Работа с несколькими группами в паттернах"""
        (temp_dir / "session_01_image_001.jpg").touch()
        (temp_dir / "session_01_image_001.json").touch()
        (temp_dir / "session_02_image_005.jpg").touch()
        (temp_dir / "session_02_image_005.json").touch()

        struct = sidecar(
            main_pattern=r(r'^session_(\d+)_image_(\d+)\.jpg$'),
            sidecar_pattern=r(r'^session_(\d+)_image_(\d+)\.json$')
        )

        assert not struct.validate(temp_dir)


# ============ ТЕСТЫ НА XOR ============

class TestXor:
    """Тесты валидатора xor()"""

    def test_xor_both_failed(self, temp_dir):
        """Оба валидатора не выполнились"""
        struct = xor(
            file(w("option_a.txt")),
            file(w("option_b.txt"))
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, AllValidationsFailedError) for error in result)
        # Должны быть также ошибки от обоих дочерних валидаторов
        assert any(isinstance(error, MandatoryMissedError) for error in result)

    def test_xor_both_succeeded(self, temp_dir):
        """Оба валидатора выполнились - ошибка для XOR"""
        (temp_dir / "option_a.txt").touch()
        (temp_dir / "option_b.txt").touch()

        struct = xor(
            file(w("option_a.txt")),
            file(w("option_b.txt"))
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, ManyOptionsError) for error in result)

    def test_xor_only_one_succeeded(self, temp_dir):
        """Только один валидатор выполнился - успех для XOR"""
        (temp_dir / "option_a.txt").touch()

        struct = xor(
            file(w("option_a.txt")),
            file(w("option_b.txt"))
        )

        assert not struct.validate(temp_dir)


# ============ ТЕСТЫ НА ONLY_ONE ============

class TestOnlyOne:
    """Тесты валидатора only_one()"""

    def test_only_one_none(self, temp_dir):
        """Ни один не выполнился"""
        struct = only_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, AllValidationsFailedError) for error in result)

    def test_only_one_exactly_one(self, temp_dir):
        """Только один выполнился - успех"""
        (temp_dir / "option_b.txt").touch()

        struct = only_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        assert not struct.validate(temp_dir)

    def test_only_one_more_than_one(self, temp_dir):
        """Больше одного выполнилось"""
        (temp_dir / "option_a.txt").touch()
        (temp_dir / "option_c.txt").touch()

        struct = only_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, ManyOptionsError) for error in result)

    def test_only_one_all(self, temp_dir):
        """Все выполнились"""
        (temp_dir / "option_a.txt").touch()
        (temp_dir / "option_b.txt").touch()
        (temp_dir / "option_c.txt").touch()

        struct = only_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, ManyOptionsError) for error in result)


# ============ ТЕСТЫ НА AT_LEAST_ONE ============

class TestAtLeastOne:
    """Тесты валидатора at_least_one()"""

    def test_at_least_one_none(self, temp_dir):
        """Ни один не выполнился"""
        struct = at_least_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, AllValidationsFailedError) for error in result)

    def test_at_least_one_exactly_one(self, temp_dir):
        """Только один выполнился - успех"""
        (temp_dir / "option_b.txt").touch()

        struct = at_least_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        assert not struct.validate(temp_dir)

    def test_at_least_one_more_than_one(self, temp_dir):
        """Больше одного выполнилось - успех"""
        (temp_dir / "option_a.txt").touch()
        (temp_dir / "option_c.txt").touch()

        struct = at_least_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        assert not struct.validate(temp_dir)

    def test_at_least_one_all(self, temp_dir):
        """Все выполнились - успех"""
        (temp_dir / "option_a.txt").touch()
        (temp_dir / "option_b.txt").touch()
        (temp_dir / "option_c.txt").touch()

        struct = at_least_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        assert not struct.validate(temp_dir)


# ============ ТЕСТЫ НА ANYTHING ============

class TestAnything:
    """Тесты валидатора anything()"""

    def test_anything_empty_folder(self, temp_dir):
        """Пустая папка"""
        struct = folder(w("test"), anything())
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        assert not struct.validate_as_root(test_folder)

    def test_anything_with_files(self, temp_dir):
        """Папка с файлами"""
        struct = folder(w("test"), anything())
        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "file1.txt").touch()
        (test_folder / "file2.jpg").touch()
        (test_folder / "random_name.dat").touch()

        assert not struct.validate_as_root(test_folder)

    def test_anything_with_folders(self, temp_dir):
        """Папка с подпапками"""
        struct = folder(w("test"), anything())
        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "subfolder1").mkdir()
        (test_folder / "subfolder2").mkdir()

        assert not struct.validate_as_root(test_folder)

    def test_anything_mixed(self, temp_dir):
        """Папка со смешанным содержимым"""
        struct = folder(w("test"), anything())
        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "file.txt").touch()
        (test_folder / "folder").mkdir()
        (test_folder / ".hidden").touch()
        (test_folder / "123.456.789").touch()

        assert not struct.validate_as_root(test_folder)


# ============ ДОПОЛНИТЕЛЬНЫЕ СЦЕНАРИИ ============

class TestComplexScenarios:
    """Тесты сложных комбинированных сценариев"""

    def test_nested_folders(self, temp_dir):
        """Вложенные папки с валидацией"""
        struct = folder(
            w("root"),
            folder(w("data"), file(w("*.csv"))),
            folder(w("config"), file(w("settings.json")))
        )

        root = temp_dir / "root"
        root.mkdir()
        data = root / "data"
        data.mkdir()
        (data / "file1.csv").touch()
        config = root / "config"
        config.mkdir()
        (config / "settings.json").touch()

        assert not struct.validate_as_root(root)

    def test_optional_files_in_folder(self, temp_dir):
        """Папка с опциональными файлами"""
        struct = folder(
            w("test"),
            file(w("required.txt")),
            file(w("optional.txt"), is_mandatory=False)
        )

        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "required.txt").touch()

        assert not struct.validate_as_root(test_folder)

    def test_extra_files_in_folder(self, temp_dir):
        """Папка с лишними файлами"""
        struct = folder(
            w("test"),
            file(w("required.txt"))
        )

        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "required.txt").touch()
        (test_folder / "extra.txt").touch()
        (test_folder / "another.dat").touch()

        result = struct.validate_as_root(test_folder)

        assert result
        assert any(isinstance(error, ExtraItemsError) for error in result)

    def test_multiple_patterns_same_folder(self, temp_dir):
        """Несколько паттернов в одной папке"""
        struct = folder(
            w("test"),
            file(w("*.txt")),
            file(w("*.json")),
            file(w("README.md"))
        )

        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "file1.txt").touch()
        (test_folder / "file2.txt").touch()
        (test_folder / "config.json").touch()
        (test_folder / "README.md").touch()

        assert not struct.validate_as_root(test_folder)

    def test_xor_with_folders(self, temp_dir):
        """XOR с папками вместо файлов"""
        struct = xor(
            folder(w("option_a"), file(w("*.txt"))),
            folder(w("option_b"), file(w("*.json")))
        )

        option_a = temp_dir / "option_a"
        option_a.mkdir()
        (option_a / "file.txt").touch()

        assert not struct.validate(temp_dir)

    def test_deeply_nested_structure(self, temp_dir):
        """Глубоко вложенная структура"""
        struct = folder(
            w("level1"),
            folder(
                w("level2"),
                folder(
                    w("level3"),
                    file(w("deep_file.txt"))
                )
            )
        )

        level1 = temp_dir / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()
        level3 = level2 / "level3"
        level3.mkdir()
        (level3 / "deep_file.txt").touch()

        assert not struct.validate_as_root(level1)

    def test_sidecar_in_folder(self, temp_dir):
        """Sidecar валидация внутри папки"""
        struct = folder(
            w("images"),
            anything(),
            # file(w("*.jpg")),
            sidecar(
                main_pattern=r(r'^(.+)\.jpg$'),
                sidecar_pattern=r(r'^(.+)\.json$')
            )
        )

        images = temp_dir / "images"
        images.mkdir()
        (images / "photo1.jpg").touch()
        (images / "photo1.json").touch()
        (images / "photo2.jpg").touch()
        (images / "photo2.json").touch()

        result = struct.validate_as_root(images)
        assert not result

    def test_anything_with_specific_files(self, temp_dir):
        """Anything в сочетании со специфичными файлами"""
        struct = folder(
            w("test"),
            file(w("required.txt")),
            anything()
        )

        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "required.txt").touch()
        (test_folder / "random1.dat").touch()
        (test_folder / "random2.xyz").touch()
        (test_folder / "subfolder").mkdir()

        assert not struct.validate_as_root(test_folder)

    def test_multiple_sidecar_groups(self, temp_dir):
        """Несколько групп sidecar в одной папке"""
        struct = folder(
            w("data"),
            anything(),
            sidecar(
                main_pattern=r(r'^image_(\d+)\.jpg$'),
                sidecar_pattern=r(r'^image_(\d+)\.json$')
            ),
            sidecar(
                main_pattern=r(r'^video_(\d+)\.mp4$'),
                sidecar_pattern=r(r'^video_(\d+)\.srt$')
            )
        )

        data = temp_dir / "data"
        data.mkdir()
        (data / "image_001.jpg").touch()
        (data / "image_001.json").touch()
        (data / "video_001.mp4").touch()
        (data / "video_001.srt").touch()

        assert not struct.validate_as_root(data)


# ============ ТЕСТЫ НА ГРАНИЧНЫЕ СЛУЧАИ ============

class TestEdgeCases:
    """Тесты граничных случаев"""

    def test_empty_folder_no_requirements(self, temp_dir):
        """Пустая папка без требований"""
        struct = folder(w("test"))
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        assert not struct.validate_as_root(test_folder)

    def test_folder_with_only_optional_children(self, temp_dir):
        """Папка только с опциональными детьми"""
        struct = folder(
            w("test"),
            file(w("optional1.txt"), is_mandatory=False),
            file(w("optional2.txt"), is_mandatory=False)
        )

        test_folder = temp_dir / "test"
        test_folder.mkdir()

        assert not struct.validate_as_root(test_folder)

    def test_regex_pattern_with_special_chars(self, temp_dir):
        """Regex паттерн со специальными символами в именах"""
        struct = file(r(r'^test\[1\]\.txt$'))
        test_file = temp_dir / "test[1].txt"
        test_file.touch()

        assert not struct.validate_as_root(test_file)

    def test_wildcard_multiple_files_match(self, temp_dir):
        """Wildcard паттерн совпадает с несколькими файлами"""
        struct = folder(
            w("test"),
            file(w("*.txt"))
        )

        test_folder = temp_dir / "test"
        test_folder.mkdir()
        (test_folder / "file1.txt").touch()
        (test_folder / "file2.txt").touch()
        (test_folder / "file3.txt").touch()

        assert not struct.validate_as_root(test_folder)

    def test_at_least_one_with_mixed_types(self, temp_dir):
        """at_least_one с файлами и папками"""
        struct = at_least_one(
            file(w("config.txt")),
            folder(w("config_dir"), file(w("settings.json")))
        )

        config_dir = temp_dir / "config_dir"
        config_dir.mkdir()
        (config_dir / "settings.json").touch()

        assert not struct.validate(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])