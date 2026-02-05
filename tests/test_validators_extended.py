import tempfile
from pathlib import Path

import pytest

from valifold.errors import (
    MandatoryMissedError, NotFileError, NotDirectoryError,
    NoSidecarError, AllValidationsFailedError, ManyOptionsError, ExtraItemsError
)
from valifold.dsl import file, folder, sidecar, xor, only_one, at_least_one, anything
from valifold.pattern import w, r


@pytest.fixture
def temp_dir():
    """Временная директория для тестов"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def create_files():
    """Фикстура для создания файлов и папок"""

    def _create(base_dir: Path, structure: dict):
        """
        Создает структуру файлов и папок
        structure = {
            'files': ['file1.txt', 'file2.jpg'],
            'folders': ['folder1', 'folder2'],
            'nested': {
                'folder1': {
                    'files': ['nested.txt']
                }
            }
        }
        """

        for key, value in structure.items():
            new_path = base_dir / key

            if value is None:
                new_path.touch()

            if isinstance(value, dict):
                new_path.mkdir(parents=True, exist_ok=True)

                _create(new_path, value)

    return _create


# ============ ТЕСТЫ НА ФАЙЛ ============

class TestFile:
    """Тесты валидатора file()"""

    @pytest.mark.parametrize("pattern,filename", [
        (w("test.txt"), "test.txt"),
        (w("*.txt"), "anything.txt"),
        (r(r'^\d+\.jpg$'), "001.jpg"),
        (r(r'^data_\w+\.csv$'), "data_export.csv"),
    ])
    def test_file_exists_is_file(self, temp_dir, pattern, filename):
        """Файл существует и это файл - параметризованный тест"""
        test_file = temp_dir / filename
        test_file.touch()

        struct = file(pattern)

        assert not struct.validate_as_root(test_file)

    @pytest.mark.parametrize("pattern,filename", [
        (w("test.txt"), "test.txt"),
        (w("*.txt"), "document.txt"),
        (r(r'^\d+\.jpg$'), "123.jpg"),
    ])
    def test_file_exists_is_not_file(self, temp_dir, pattern, filename):
        """Файл существует, но это не файл (а директория)"""
        test_path = temp_dir / filename
        test_path.mkdir()

        struct = file(pattern)
        result = struct.validate_as_root(test_path)

        assert result
        assert any(isinstance(error, NotFileError) for error in result)

    @pytest.mark.parametrize("is_optional,should_have_errors", [
        (False, True),
        (True, False),
    ])
    def test_file_not_exists(self, temp_dir, is_optional, should_have_errors):
        """Файл не существует - тест с параметризацией обязательности"""
        name = "test.txt"
        test_file = temp_dir / name

        struct = file(
            w(name),
            is_optional=is_optional
        )
        result = struct.validate_as_root(test_file)

        if should_have_errors:
            assert result
            assert any(isinstance(error, MandatoryMissedError) for error in result)
        else:
            assert not result


# ============ ТЕСТЫ НА ПАПКУ ============

class TestFolder:
    """Тесты валидатора folder()"""

    @pytest.mark.parametrize("pattern,foldername", [
        (w("test"), "test"),
        (w("data_*"), "data_export"),
        (r(r'^\d{4}-\d{2}-\d{2}$'), "2024-01-15"),
    ])
    def test_folder_exists_is_folder(self, temp_dir, pattern, foldername):
        """Папка существует и это папка - параметризованный тест"""
        test_folder = temp_dir / foldername
        test_folder.mkdir()

        struct = folder(pattern)

        assert not struct.validate_as_root(test_folder)

    @pytest.mark.parametrize("pattern,foldername", [
        (w("test"), "test"),
        (w("data_*"), "data_export"),
    ])
    def test_folder_exists_is_not_folder(self, temp_dir, pattern, foldername):
        """Папка существует, но это не папка (а файл)"""
        test_path = temp_dir / foldername
        test_path.touch()

        struct = folder(pattern)
        result = struct.validate_as_root(test_path)

        assert result
        assert any(isinstance(error, NotDirectoryError) for error in result)

    @pytest.mark.parametrize("is_optional,should_have_errors", [
        (False, True),
        (True, False),
    ])
    def test_folder_not_exists(self, temp_dir, is_optional, should_have_errors):
        """Папка не существует - тест с параметризацией обязательности"""
        name = "test_folder"
        test_folder = temp_dir / name

        struct = folder(
            w(name),
            is_optional=is_optional
        )
        result = struct.validate_as_root(test_folder)

        if should_have_errors:
            assert result
            assert any(isinstance(error, MandatoryMissedError) for error in result)
        else:
            assert not result


# ============ ТЕСТЫ НА SIDECAR ============

class TestSidecar:
    """Тесты валидатора sidecar()"""

    @pytest.mark.parametrize("main_ext,sidecar_ext,files", [
        ("jpg", "json", [("image_001.jpg", "image_001.json"), ("image_002.jpg", "image_002.json")]),
        ("mp4", "srt", [("video_01.mp4", "video_01.srt")]),
        ("csv", "yaml", [("data_export.csv", "data_export.yaml"), ("data_backup.csv", "data_backup.yaml")]),
    ])
    def test_sidecar_exists_for_each(self, temp_dir, create_files, main_ext, sidecar_ext, files):
        """Для каждого основного файла есть sidecar - параметризованный тест"""
        file_list = []
        for main, side in files:
            file_list.extend([main, side])

        create_files(temp_dir, {'files': file_list})

        struct = sidecar(
            main_pattern=r(rf'^(.+)\.{main_ext}$'),
            sidecar_pattern=r(rf'^(.+)\.{sidecar_ext}$')
        )

        assert not struct.validate(temp_dir)

    @pytest.mark.parametrize("main_files,sidecar_files,expected_missing", [
        (["image_001.jpg", "image_002.jpg"], ["image_001.json"], 1),
        (["image_001.jpg", "image_002.jpg", "image_003.jpg"], ["image_001.json"], 2),
        (["image_001.jpg", "image_002.jpg", "image_003.jpg"], [], 3),
    ])
    def test_sidecar_missing(self, temp_dir, create_files, main_files, sidecar_files, expected_missing):
        """Не хватает некоторых sidecar файлов - параметризованный тест"""
        create_files(temp_dir, {name: None for name in main_files + sidecar_files})

        struct = sidecar(
            main_pattern=r(r'^(.+)\.jpg$'),
            sidecar_pattern=r(r'^(.+)\.json$')
        )

        result = struct.validate(temp_dir)

        assert result
        assert any(isinstance(error, NoSidecarError) for error in result)
        sidecar_errors = [e for e in result if isinstance(e, NoSidecarError)]
        assert len(sidecar_errors[0].paths) == expected_missing

    @pytest.mark.parametrize("main_files,sidecar_files", [
        ([], ["image_001.json", "image_002.json"]),
        ([], []),
    ])
    def test_sidecar_no_main_files(self, temp_dir, create_files, main_files, sidecar_files):
        """Нет основных файлов - нет ошибок"""
        create_files(temp_dir, {name: None for name in main_files + sidecar_files})

        struct = sidecar(
            main_pattern=r(r'^(.+)\.jpg$'),
            sidecar_pattern=r(r'^(.+)\.json$')
        )

        assert not struct.validate(temp_dir)

    @pytest.mark.parametrize("main_groups,sidecar_groups,should_fail", [
        (0, 0, True),  # Нет групп
        (1, 1, False),  # Одинаковое количество
        (2, 2, False),  # Одинаковое количество
        (1, 2, True),  # Разное количество
        (3, 1, True),  # Разное количество
    ])
    def test_sidecar_group_validation(self, main_groups, sidecar_groups, should_fail):
        """Валидация количества групп в паттернах"""
        main_pattern_str = r'^' + r'(\w+)_' * main_groups + r'image\.jpg$'
        sidecar_pattern_str = r'^' + r'(\w+)_' * sidecar_groups + r'image\.json$'

        if should_fail:
            with pytest.raises(ValueError):
                sidecar(
                    main_pattern=r(main_pattern_str),
                    sidecar_pattern=r(sidecar_pattern_str)
                )
        else:
            # Должно создаться без ошибок
            result = sidecar(
                main_pattern=r(main_pattern_str),
                sidecar_pattern=r(sidecar_pattern_str)
            )
            assert result is not None


# ============ ТЕСТЫ НА XOR ============

class TestXor:
    """Тесты валидатора xor()"""

    @pytest.mark.parametrize("create_a,create_b,expected_error", [
        (False, False, AllValidationsFailedError),  # Оба не выполнились
        (True, True, ManyOptionsError),  # Оба выполнились
        (True, False, None),  # Только A - успех
        (False, True, None),  # Только B - успех
    ])
    def test_xor_scenarios(self, temp_dir, create_a, create_b, expected_error):
        """Различные сценарии XOR - параметризованный тест"""
        if create_a:
            (temp_dir / "option_a.txt").touch()
        if create_b:
            (temp_dir / "option_b.txt").touch()

        struct = xor(
            file(w("option_a.txt")),
            file(w("option_b.txt"))
        )

        result = struct.validate(temp_dir)

        if expected_error:
            assert result
            assert any(isinstance(error, expected_error) for error in result)
        else:
            assert not result


# ============ ТЕСТЫ НА ONLY_ONE ============

class TestOnlyOne:
    """Тесты валидатора only_one()"""

    @pytest.mark.parametrize("files_to_create,expected_error", [
        ([], AllValidationsFailedError),  # Ни один
        (["option_a.txt"], None),  # Один - успех
        (["option_b.txt"], None),  # Другой один - успех
        (["option_a.txt", "option_b.txt"], ManyOptionsError),  # Два
        (["option_a.txt", "option_c.txt"], ManyOptionsError),  # Два других
        (["option_a.txt", "option_b.txt", "option_c.txt"], ManyOptionsError),  # Все три
    ])
    def test_only_one_scenarios(self, temp_dir, create_files, files_to_create, expected_error):
        """Различные сценарии only_one - параметризованный тест"""
        create_files(temp_dir, {name: None for name in files_to_create})

        struct = only_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        result = struct.validate(temp_dir)

        if expected_error:
            assert result
            assert any(isinstance(error, expected_error) for error in result)
        else:
            assert not result


# ============ ТЕСТЫ НА AT_LEAST_ONE ============

class TestAtLeastOne:
    """Тесты валидатора at_least_one()"""

    @pytest.mark.parametrize("files_to_create,should_pass", [
        ([], False),  # Ни один - ошибка
        (["option_a.txt"], True),  # Один - успех
        (["option_b.txt"], True),  # Другой один - успех
        (["option_a.txt", "option_b.txt"], True),  # Два - успех
        (["option_a.txt", "option_c.txt"], True),  # Два других - успех
        (["option_a.txt", "option_b.txt", "option_c.txt"], True),  # Все три - успех
    ])
    def test_at_least_one_scenarios(self, temp_dir, create_files, files_to_create, should_pass):
        """Различные сценарии at_least_one - параметризованный тест"""
        create_files(temp_dir, {name: None for name in files_to_create})

        struct = at_least_one(
            file(w("option_a.txt")),
            file(w("option_b.txt")),
            file(w("option_c.txt"))
        )

        result = struct.validate(temp_dir)

        if should_pass:
            assert not result
        else:
            assert result
            assert any(isinstance(error, AllValidationsFailedError) for error in result)


# ============ ТЕСТЫ НА ANYTHING ============

class TestAnything:
    """Тесты валидатора anything()"""

    @pytest.mark.parametrize("structure", [
        {},  # Пустая папка
        {
            'file1.txt': None
        },  # Один файл
        {
            'file1.txt': None,
            'file2.jpg': None,
            'data.csv': None
        },  # Несколько файлов
        {
            'subfolder1': {}
        },  # Одна папка
        {
            'sub1': {},
            'sub2': {},
            'sub3': {}
        },  # Несколько папок
        {
            'file.txt': None,
            'subfolder': {}
        },  # Смешанное
        {
            '.hidden': None,
            '123.456.789': None,
            'file with spaces.txt': None
        },  # Специальные имена
    ])
    def test_anything_scenarios(self, temp_dir, create_files, structure):
        """Anything принимает любое содержимое - параметризованный тест"""
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        create_files(test_folder, structure)

        struct = folder(w("test"), anything())

        assert not struct.validate_as_root(test_folder)


# ============ КОМПЛЕКСНЫЕ СЦЕНАРИИ ============

class TestComplexScenarios:
    """Тесты сложных комбинированных сценариев"""

    @pytest.mark.parametrize("depth,should_pass", [
        (1, True),
        (2, True),
        (3, True),
        (5, True),
    ])
    def test_nested_folders_depth(self, temp_dir, depth, should_pass):
        """Вложенные папки различной глубины"""
        current = temp_dir

        # Создаем структуру
        for i in range(depth):
            current = current / f"level{i}"
            current.mkdir()

        # Создаем файл в самой глубокой папке
        (current / "deep_file.txt").touch()

        # Строим валидатор
        validator = file(w("deep_file.txt"))

        for i in reversed(range(depth)):
            validator = folder(
                w(f"level{i}"),
                validator
            )

        result = validator.validate_as_root(temp_dir / "level0")

        assert (not result) == should_pass

    @pytest.mark.parametrize("extra_files,should_have_error", [
        ([], False),  # Нет лишних файлов
        (["extra.txt"], True),  # Один лишний
        (["extra1.txt", "extra2.dat"], True),  # Несколько лишних
        (["extra.txt", "another.dat", "random.xyz"], True),  # Много лишних
    ])
    def test_extra_files_in_folder(self, temp_dir, create_files, extra_files, should_have_error):
        """Папка с лишними файлами - параметризованный тест"""
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        create_files(test_folder, {name: None for name in ["required.txt"] + extra_files})

        struct = folder(
            w("test"),
            file(w("required.txt"))
        )
        result = struct.validate_as_root(test_folder)

        if should_have_error:
            assert result
            assert any(isinstance(error, ExtraItemsError) for error in result)
            extra_errors = [e for e in result if isinstance(e, ExtraItemsError)]
            assert len(extra_errors[0].paths) == len(extra_files)
        else:
            assert not result

    @pytest.mark.parametrize("pattern_pairs", [
        [(w("*.txt"), w("*.json"))],
        [(w("*.txt"), w("*.json"), w("*.csv"))],
        [(r(r'^\d+\.jpg$'), r(r'^[a-z]+\.png$'))],
    ])
    def test_multiple_patterns_same_folder(self, temp_dir, create_files, pattern_pairs):
        """Несколько паттернов в одной папке - параметризованный тест"""
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        # Создаем файлы для каждого паттерна
        files = []

        if w("*.txt") in pattern_pairs[0]:
            files.append("file1.txt")
        if w("*.json") in pattern_pairs[0]:
            files.append("config.json")
        if w("*.csv") in pattern_pairs[0]:
            files.append("data.csv")
        if r(r'^\d+\.jpg$') in pattern_pairs[0]:
            files.append("001.jpg")
        if r(r'^[a-z]+\.png$') in pattern_pairs[0]:
            files.append("image.png")

        create_files(test_folder, {name: None for name in files})

        validators = [file(pattern) for pattern in pattern_pairs[0]]
        struct = folder(w("test"), *validators)

        assert not struct.validate_as_root(test_folder)


# ============ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ============

class TestIntegration:
    """Интеграционные тесты с реалистичными сценариями"""

    def test_photo_project_structure(self, temp_dir, create_files):
        """Структура фотопроекта с sidecar файлами"""
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
        """Конфигурация: либо файл, либо папка"""
        # Вариант 1: файл конфигурации
        create_files(temp_dir, {"config.json": None})

        struct = xor(
            file(w("config.json")),
            folder(w("config"), file(w("*.yaml")))
        )

        assert not struct.validate(temp_dir)

    @pytest.mark.parametrize("structure_type", [
        "simple",
        "with_metadata",
        "with_archive"
    ])
    def test_data_folder_variants(self, temp_dir, create_files, structure_type):
        """Различные варианты структуры папки данных"""
        data_folder = temp_dir / "data"
        data_folder.mkdir()

        if structure_type == "simple":
            create_files(data_folder, {
                'dataset.csv': None,
            })
            validators = [
                file(w("*.csv")),
            ]
        elif structure_type == "with_metadata":
            create_files(data_folder, {
                'dataset.csv': None,
                'metadata.json': None,
            })
            validators = [
                file(w("*.csv")),
                file(w("metadata.json")),
            ]
        else:  # with_archive
            create_files(data_folder, {
                'dataset.csv': None,
                'metadata.json': None,
                'backup.zip': None,
            })
            validators = [
                file(w("*.csv")),
                file(w("metadata.json")),
                file(w("*.zip"), is_optional=True)
            ]

        struct = folder(
            w("data"),
            *validators
        )

        assert not struct.validate_as_root(data_folder)


# ============ ТЕСТЫ НА ПРОИЗВОДИТЕЛЬНОСТЬ ============

class TestPerformance:
    """Тесты производительности (без реальных замеров, но с большими объемами)"""

    @pytest.mark.parametrize("file_count", [10, 50, 100])
    def test_many_files_validation(self, temp_dir, create_files, file_count):
        """Валидация папки с большим количеством файлов"""
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        files = [f"file_{i:04d}.txt" for i in range(file_count)]
        create_files(test_folder, {name: None for name in files})

        struct = folder(w("test"), file(w("*.txt")))

        assert not struct.validate_as_root(test_folder)

    @pytest.mark.parametrize("pair_count", [5, 20, 50])
    def test_many_sidecar_pairs(self, temp_dir, create_files, pair_count):
        """Валидация большого количества пар sidecar файлов"""
        test_folder = temp_dir / "test"
        test_folder.mkdir()

        files = []
        for i in range(pair_count):
            files.extend([f"image_{i:04d}.jpg", f"image_{i:04d}.json"])

        create_files(test_folder, {'files': files})

        struct = folder(
            w("test"),
            sidecar(
                main_pattern=r(r'^(.+)\.jpg$'),
                sidecar_pattern=r(r'^(.+)\.json$')
            )
        )

        assert not struct.validate_as_root(test_folder)


# ============ ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ MARKS ============

@pytest.mark.slow
class TestSlowOperations:
    """Медленные тесты, помеченные для опционального запуска"""

    def test_deeply_nested_validation(self, temp_dir, create_files):
        """Очень глубокая вложенность (медленный тест)"""
        current = temp_dir
        depth = 20

        for i in range(depth):
            current = current / f"level{i}"
            current.mkdir()

        (current / "deep.txt").touch()

        # Просто проверяем, что система справляется
        assert (temp_dir / "level0").exists()


@pytest.mark.edge_case
class TestEdgeCases:
    """Граничные случаи, помеченные отдельно"""

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
        """Файлы со специальными символами в именах"""
        test_file = temp_dir / filename
        test_file.touch()

        struct = file(w("*"))

        assert not struct.validate_as_root(test_file)


# ============ ТЕСТЫ С FIXTURES ============

@pytest.fixture
def standard_project_structure(temp_dir, create_files):
    """Стандартная структура проекта для переиспользования"""
    create_files(temp_dir, {
        'README.md': None,
        'requirements.txt': None,
        'src': {
            'main.py': None,
            '__init__.py': None
        },
        'tests': {
            'test_main.py': None
        },
        'docs': {
            'index.md': None
        }
    })
    return temp_dir


class TestWithFixtures:
    """Тесты использующие переиспользуемые фикстуры"""

    def test_project_has_readme(self, standard_project_structure):
        """Проверка наличия README в стандартной структуре"""
        struct = file(w("README.md"))
        assert not struct.validate(standard_project_structure)

    def test_project_has_src(self, standard_project_structure):
        """Проверка наличия папки src в стандартной структуре"""
        struct = folder(
            w("src"),
            file(w("*.py"))
        )
        assert not struct.validate(standard_project_structure)
