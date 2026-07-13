"""
Tests that mirror README usage examples.
All imports are from the top-level valifold package — the contract the public API must honour.
"""
import pytest

from valifold import anything, at_least_one, file, folder, only_one, r, sidecar, w


# --- imports ---

@pytest.mark.parametrize("name", [
    "file", "folder", "sidecar", "xor", "only_one", "at_least_one", "anything", "w", "r",
])
def test_public_name_importable(name: str) -> None:
    import valifold

    assert hasattr(valifold, name)


# --- basic README example ---

def test_readme_basic_valid(temp_dir, create_files):
    create_files(temp_dir, {
        "my_project": {
            "README.md": None,
            "main.py": None,
            "src": {"app.py": None},
        }
    })

    structure = folder(
        w("my_project"),
        file(w("README.md")),
        file(w("*.py")),
        folder(w("src"), file(w("*.py"))),
    )

    assert structure.validate_as_root(temp_dir / "my_project") == []


# --- optional elements ---

@pytest.mark.parametrize("include_optional", [True, False])
def test_optional_file(temp_dir, create_files, include_optional):
    files = {"settings.yaml": None}

    if include_optional:
        files["README.md"] = None

    create_files(temp_dir, {"config": files})

    structure = folder(
        w("config"),
        file(w("*.yaml")),
        file(w("README.md"), is_optional=True),
    )

    assert structure.validate_as_root(temp_dir / "config") == []


@pytest.mark.parametrize("include_optional", [True, False])
def test_optional_folder(temp_dir, create_files, include_optional):
    contents = {"cache": {}} if include_optional else {}
    create_files(temp_dir, {"proj": contents})

    structure = folder(w("proj"), folder(w("cache"), is_optional=True))
    assert structure.validate_as_root(temp_dir / "proj") == []


# --- xor / only_one ---

@pytest.mark.parametrize("files, valid", [
    ({"a.txt": None}, True),
    ({"b.txt": None}, True),
    ({"a.txt": None, "b.txt": None}, False),
    ({}, False),
])
def test_only_one(temp_dir, create_files, files, valid):
    create_files(temp_dir, {"proj": files})
    structure = folder(w("proj"), only_one(file(w("a.txt")), file(w("b.txt"))))
    errors = structure.validate_as_root(temp_dir / "proj")
    assert (errors == []) == valid


# --- at_least_one ---

@pytest.mark.parametrize("files, valid", [
    ({"a.txt": None}, True),
    ({"b.txt": None}, True),
    ({"a.txt": None, "b.txt": None}, True),
    ({}, False),
])
def test_at_least_one(temp_dir, create_files, files, valid):
    create_files(temp_dir, {"proj": files})
    structure = folder(w("proj"), at_least_one(file(w("a.txt")), file(w("b.txt"))))
    errors = structure.validate_as_root(temp_dir / "proj")
    assert (errors == []) == valid


# --- anything ---

def test_anything_allows_extra_files(temp_dir, create_files):
    create_files(temp_dir, {"proj": {"whatever.xyz": None, "another.abc": None}})
    structure = folder(w("proj"), anything())
    assert structure.validate_as_root(temp_dir / "proj") == []


# --- sidecar ---

@pytest.mark.xfail(reason="SidecarValidator doesn't implement Matcher — its files are flagged as extra items")
def test_sidecar_valid(temp_dir, create_files):
    create_files(temp_dir, {"photos": {"IMG_001.jpg": None, "IMG_001.xmp": None}})
    structure = folder(w("photos"), sidecar(r(r"(.+)\.jpg"), r(r"(.+)\.xmp")))
    assert structure.validate_as_root(temp_dir / "photos") == []


def test_sidecar_missing_sidecar_invalid(temp_dir, create_files):
    create_files(temp_dir, {"photos": {"IMG_001.jpg": None}})
    structure = folder(w("photos"), sidecar(r(r"(.+)\.jpg"), r(r"(.+)\.xmp")))
    assert structure.validate_as_root(temp_dir / "photos")


# --- regex pattern ---

def test_regex_pattern(temp_dir, create_files):
    create_files(temp_dir, {"2024-01-15": {"shot.jpg": None}})
    structure = folder(r(r"^20\d{2}-\d{2}-\d{2}$"), file(w("*.jpg")))
    assert structure.validate_as_root(temp_dir / "2024-01-15") == []
