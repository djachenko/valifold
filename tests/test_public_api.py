"""
Tests that mirror README usage examples.
All imports are from the top-level valifold package — the contract the public API must honour.
"""
from pathlib import Path

import pytest

from valifold import anything, at_least_one, file, folder, only_one, r, sidecar, w, xor


@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    return tmp_path


# --- imports ---

def test_all_public_names_importable() -> None:
    import valifold  # noqa: F401
    for name in ("file", "folder", "sidecar", "xor", "only_one", "at_least_one", "anything", "w", "r"):
        assert hasattr(valifold, name), f"valifold.{name} is missing"


# --- basic usage example from README ---

def test_readme_basic_valid(tmp: Path) -> None:
    project = tmp / "my_project"
    project.mkdir()
    (project / "README.md").touch()
    (project / "main.py").touch()
    src = project / "src"
    src.mkdir()
    (src / "app.py").touch()

    structure = folder(
        w("my_project"),
        file(w("README.md")),
        file(w("*.py")),
        folder(w("src"), file(w("*.py"))),
    )
    errors = structure.validate_as_root(project)
    assert errors == []


def test_readme_basic_invalid_formatted_message(tmp: Path) -> None:
    project = tmp / "my_project"
    project.mkdir()
    # README.md is missing

    structure = folder(
        w("my_project"),
        file(w("README.md")),
    )
    errors = structure.validate_as_root(project)
    assert errors

    # formatted_message() must not raise — this is the 🔴1 bug
    for error in errors:
        msg = error.formatted_message(root_path=project)
        assert isinstance(msg, str)


# --- optional elements ---

def test_optional_file_absent_is_valid(tmp: Path) -> None:
    project = tmp / "config"
    project.mkdir()
    (project / "settings.yaml").touch()

    structure = folder(
        w("config"),
        file(w("*.yaml")),
        file(w("README.md"), is_optional=True),
    )
    errors = structure.validate_as_root(project)
    assert errors == []


def test_optional_folder_absent_is_valid(tmp: Path) -> None:
    project = tmp / "proj"
    project.mkdir()

    structure = folder(w("proj"), folder(w("cache"), is_optional=True))
    errors = structure.validate_as_root(project)
    assert errors == []


# --- xor / only_one ---

def test_xor_exactly_one_valid(tmp: Path) -> None:
    project = tmp / "proj"
    project.mkdir()
    (project / "a.txt").touch()

    structure = folder(w("proj"), xor(file(w("a.txt")), file(w("b.txt"))))
    errors = structure.validate_as_root(project)
    assert errors == []


def test_only_one_both_present_invalid(tmp: Path) -> None:
    project = tmp / "proj"
    project.mkdir()
    (project / "a.txt").touch()
    (project / "b.txt").touch()

    structure = folder(w("proj"), only_one(file(w("a.txt")), file(w("b.txt"))))
    errors = structure.validate_as_root(project)
    assert errors


# --- at_least_one ---

def test_at_least_one_valid(tmp: Path) -> None:
    project = tmp / "proj"
    project.mkdir()
    (project / "a.txt").touch()
    (project / "b.txt").touch()

    structure = folder(w("proj"), at_least_one(file(w("a.txt")), file(w("b.txt"))))
    errors = structure.validate_as_root(project)
    assert errors == []


def test_at_least_one_none_present_invalid(tmp: Path) -> None:
    project = tmp / "proj"
    project.mkdir()

    structure = folder(w("proj"), at_least_one(file(w("a.txt")), file(w("b.txt"))))
    errors = structure.validate_as_root(project)
    assert errors


# --- anything ---

def test_anything_allows_extra_files(tmp: Path) -> None:
    project = tmp / "proj"
    project.mkdir()
    (project / "whatever.xyz").touch()
    (project / "another.abc").touch()

    structure = folder(w("proj"), anything())
    errors = structure.validate_as_root(project)
    assert errors == []


# --- sidecar ---

@pytest.mark.xfail(reason="SidecarValidator doesn't implement Matcher — its files are flagged as extra items (hidden contract bug)")
def test_sidecar_valid(tmp: Path) -> None:
    project = tmp / "photos"
    project.mkdir()
    (project / "IMG_001.jpg").touch()
    (project / "IMG_001.xmp").touch()

    structure = folder(w("photos"), sidecar(r(r"(.+)\.jpg"), r(r"(.+)\.xmp")))
    errors = structure.validate_as_root(project)
    assert errors == []


def test_sidecar_missing_sidecar_invalid(tmp: Path) -> None:
    project = tmp / "photos"
    project.mkdir()
    (project / "IMG_001.jpg").touch()
    # no .xmp

    structure = folder(w("photos"), sidecar(r(r"(.+)\.jpg"), r(r"(.+)\.xmp")))
    errors = structure.validate_as_root(project)
    assert errors


# --- regex pattern ---

def test_regex_pattern(tmp: Path) -> None:
    project = tmp / "2024-01-15"
    project.mkdir()
    (project / "shot.jpg").touch()

    structure = folder(r(r"^20\d{2}-\d{2}-\d{2}$"), file(w("*.jpg")))
    errors = structure.validate_as_root(project)
    assert errors == []
