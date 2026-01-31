# Valifold

Valifold is a library for validating file and folder structures. The entire configuration is described in Python code.

## Usage example

This code should validate this project structure:

```python
from pathlib import Path

from dsl import folder, file, anything
from pattern import w

# Define expected structure
structure = folder(
    w("valifold"),
    file(w("LICENSE.md")),
    file(w("README.md")),
    file(w(".gitignore")),

    folder(
        w(".git"),
        anything(),
    ),
    folder(
        w("tests"),
        file(w("__init__.py")),
        file(w("*.py")),
    ),
    folder(
        w("src"),
        file(w("__init__.py")),
        file(w("*.py")),
    ),
)

# Validate
errors = structure.validate_as_root(Path.cwd())

if not errors:
    print("✓ Valid structure")
else:
    for error in errors:
        print(f"✗ {error.formatted_message()}")
```

#### Advantages:

This is Python code. Therefore:
- Validators can be composed.
- Validators can be generated at runtime.
- Validators can be stored in variables and passed as parameters.
- You can implement custom validators by inheriting from base classes.

#### Disadvantages

This is Python code. Therefore, the config is harder to use as a separate artifact. Possible approaches:
- Simply describe the structure in code. Not flexible.
- Write config in a separate file and import via runpy. Slow.
- Parse config manually. Complex.

## Installation

```bash
pip install valifold
```

## Contents

Library contains several base and concrete classes. 
Base classes are not intended for direct use and thus are marked as abstract. Every concrete class has corresponding DSL builder func and can be interchangeably used both directly and via func.

Understanding how DSL functions map to validator classes:

| Purpose                                                                                       | Class              | DSL Function                                                |
|-----------------------------------------------------------------------------------------------|--------------------|-------------------------------------------------------------|
| Abstract class defining contract.                                                             | `Pattern`          | Must not be instantiated directly                           |
| Abstract class for string-based patterns                                                      | `BasePattern`      | Must not be instantiated directly                           |
| Shell-style pattern matching                                                                  | `WildcardPattern`  | `w("*.txt")`                                                |
| Regular expression matching                                                                   | `RegexPattern`     | `r(r"^\d+\.jpg$")`                                          |
| Abstract class defining validators contract                                                   | `Validator`    | Must not be instantiated directly                           |
| Abstract class defining contract for filestructure-_related_ validators                       | `Matcher`    | Must not be instantiated directly                           |
| Abstract class defining contract for validators that can represent validation starting point. | `RootValidator`    | Must not be instantiated directly                           |
| Abstract class defining contract for validators that represent some filestructure item.       | `SubstructureValidator`    | Must not be instantiated directly                           |
| Validator for individual files                                                                | `FileValidator`    | `file(pattern, is_optional=False)`                          |
| Validator for directories and their contents                                                  | `FolderValidator`  | `folder(pattern, *children, is_optional=False)`             |
| Validator for paired files                                                                    | `SidecarValidator` | `sidecar(main_pattern, sidecar_pattern)`                    |
| Logical validator checking if given number of checks passed                                   | `XorValidator`     | `xor(a, b)`, `only_one(*options)`, `at_least_one(*options)` |
| Logical validator, allowing any content                                                       | `AnyValidator`     | `anything()`                                                |

## Usage example

```python
from pathlib import Path
from valifold import file, folder, w

# Define expected structure
structure = folder(
    w("my_project"),
    file(w("README.md")),
    file(w("*.py")),
    folder(w("src"), file(w("*.py")))
)

# Validate
errors = structure.validate_as_root(Path("my_project"))

if not errors:
    print("✓ Valid structure")
else:
    for error in errors:
        print(f"✗ {error.formatted_message()}")
```

---

There are two basic concepts: patterns and validators: 

## Patterns

Patterns define filestructure items' names for matching.

### Wildcard pattern (`WildcardPattern` / `w`)

Uses shell-style wildcards for simple matching.

**Signature:**
```python
w(pattern: str) -> WildcardPattern

WildcardPattern(pattern: str)
```

**Syntax of pattern:**
- `*` - matches any number of characters
- `?` - matches exactly one character
- `[seq]` - matches any character in seq
- `[!seq]` - matches any character not in seq

**Examples:**

```python
from valifold import w

# Match any .txt file
w("*.txt")
# Matches: file.txt, document.txt, test.txt
# Doesn't match: file.pdf, readme.md

# Match files with specific prefix
w("test_*.py")
# Matches: test_utils.py, test_core.py, test_main.py
# Doesn't match: utils.py, main_test.py

# Match exactly 3 characters
w("file_???.jpg")
# Matches: file_001.jpg, file_abc.jpg
# Doesn't match: file_1.jpg, file_0001.jpg

# Match date pattern
w("2024-??-??.log")
# Matches: 2024-01-15.log, 2024-12-31.log
# Doesn't match: 2023-01-15.log, 2024-1-5.log

# Match with character class
w("file_[0-9][0-9][0-9].txt")
# Matches: file_001.txt, file_123.txt
# Doesn't match: file_abc.txt, file_1.txt
```

**When to use:** Simple patterns, most common use cases, easier to read.

---

### Regex pattern (`RegexPattern` / `r`)

Uses regular expressions for complex matching.

**Signature:**
```python
r(pattern: str) -> RegexPattern

RegexPattern(pattern: str)
```

**Examples:**

```python
from valifold import r

# Match 4-digit numbers with .jpg extension
r(r"^\d{4}\.jpg$")
# Matches: 0001.jpg, 1234.jpg, 9999.jpg
# Doesn't match: 001.jpg, 12345.jpg, abcd.jpg

# Match test files
r(r"^test_\w+\.py$")
# Matches: test_utils.py, test_core_logic.py, test_123.py
# Doesn't match: tests.py, utils_test.py, test_.py

# Match date folders (YYYY-MM-DD)
r(r"^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
# Matches: 2024-01-15, 2023-12-31, 2020-06-30
# Doesn't match: 2024-13-01, 2024-00-15, 24-01-15

# Match semantic versions
r(r"^v\d+\.\d+\.\d+$")
# Matches: v1.0.0, v2.15.3, v10.2.45
# Doesn't match: 1.0.0, v1.0, version-1.0.0

# Match files with uppercase start
r(r"^[A-Z][a-zA-Z0-9_]*\.txt$")
# Matches: Main.txt, MyFile.txt, A123.txt
# Doesn't match: main.txt, _file.txt, 123.txt
```

**When to use:** Complex patterns, precise validation, dates/versions, specific character requirements.

---

## Validators

Validators define the structure and rules for files and folders.

### File validator (`FileValidator` /  `file`)

Validates individual files.

**Signature:**
```python
file(pattern: Pattern, is_optional: bool = False) -> FileValidator

FileValidator(pattern: Pattern, is_optional: bool)
```

**Parameters:**
- `pattern` - Pattern to match file name (created with `w()` or `r()`)
- `is_optional` - If `True`, file doesn't have to exist (default: `False`)

**Description:**

The file validator checks that:
1. A file matching the pattern exists
2. The matched path is actually a file (not a directory)

If `is_optional=True`, the validator passes even if no matching file exists.

**Examples:**

```python
from valifold import file, w, r

# Required file with exact name
file(w("README.md"))
# ✓ README.md exists and is a file
# ✗ README.md is missing
# ✗ README.md exists but is a directory

# Required file with wildcard
file(w("*.py"))
# ✓ At least one .py file exists
# ✗ No .py files exist
# ✗ Only directories with .py names exist

# Optional file
file(w("LICENSE"), is_optional=True)
# ✓ LICENSE exists and is a file
# ✓ LICENSE doesn't exist (that's OK)
# ✗ LICENSE exists but is a directory

# Required file with regex pattern
file(r(r"^\d{4}-\d{2}-\d{2}\.log$"))
# ✓ 2024-01-15.log exists
# ✗ No matching log files
# ✗ 24-01-15.log (doesn't match pattern)

# Multiple files with pattern
file(w("config_*.json"))
# ✓ config_dev.json exists (and possibly others)
# ✗ No config_*.json files exist
```

**Real-world examples:**

```python
# Project must have README
file(w("README.md"))

# Optional backup file
file(
    w("backup.zip"), 
    is_optional=True
)

# At least one Python file
file(w("*.py"))

# Specific log file format
file(r(r"^app_\d{8}\.log$"))  # app_20240115.log

# Configuration file
file(w("config.json"))
```

**Possible errors:**
- `MandatoryMissedError` - Required file is missing
- `NotFileError` - Path exists but is a directory, not a file

---

### Folder validator (`FolderValidator` / `folder`) 

Validates directories and their contents.

**Signature:**
```python
folder(
    pattern: Pattern,
    *children: Validator,
    is_optional: bool = False
) -> FolderValidator

FolderValidator(
    pattern: Pattern,
    is_optional: bool,
    children: List[Validator]
)
```

**Parameters:**
- `pattern` - Pattern to match folder name
- `*children` - Zero or more validators for folder contents
- `is_optional` - If `True`, folder doesn't have to exist (default: `False`)

**Description:**

The folder validator checks that:
1. A folder matching the pattern exists
2. The matched path is actually a directory (not a file)
3. The folder contents match all child validators
4. No extra files/folders exist that aren't matched by any child validator

If `is_optional=True`, the validator passes even if no matching folder exists.

**Examples:**

```python
from valifold import folder, file, w, r

# Empty folder (any contents allowed)
folder(w("temp"))
# ✓ temp/ exists and is a directory
# ✗ temp/ is missing
# ✗ temp exists but is a file

# Folder with specific file
folder(
    w("docs"),
    file(w("index.md"))
)
# ✓ docs/ exists and contains index.md
# ✗ docs/ is missing
# ✗ docs/index.md is missing
# ✗ docs/ contains extra files not defined

# Folder with multiple files
folder(
    w("config"),
    file(w("*.yaml")),
    file(w("README.md"), is_optional=True)
)
# ✓ config/ with at least one .yaml and optionally README.md
# ✗ config/ with no .yaml files
# ✗ config/ with extra non-yaml, non-readme files

# Nested folders
folder(
    w("src"),
    file(w("__init__.py")),
    file(w("*.py")),
    folder(
        w("tests"),
        file(w("test_*.py"))
    )
)
# ✓ src/ with __init__.py, .py files, and tests/ subfolder
# ✗ Missing any required part
# ✗ Extra files in src/ or src/tests/

# Optional folder
folder(w("cache"), is_optional=True)
# ✓ cache/ exists
# ✓ cache/ doesn't exist (that's OK)
# ✗ cache exists but is a file

# Folder with regex pattern
folder(
    r(r"^20\d{2}-\d{2}-\d{2}$"),
    file(w("*.jpg"))
)
# ✓ 2024-01-15/ exists and contains .jpg files
# ✗ No matching date folder
# ✗ Date folder exists but no .jpg files
```

**Real-world examples:**

```python
# Python package structure
folder(
    w("my_package"),
    file(w("__init__.py")),
    file(w("*.py")),
    folder(
        w("tests"),
        file(w("test_*.py"))
    )
)

# Documentation folder
folder(
    w("docs"),
    file(w("index.md")),
    folder(
        w("api"), 
        file(w("*.md")), 
        is_optional=True
    ),
    folder(
        w("guides"), 
        file(w("*.md")), 
        is_optional=True
    )
)

# Data science project
folder(
    w("data"),
    folder(w("raw")),
    folder(w("processed")),
    folder(w("interim"), is_optional=True)
)

# Date-organized folders
folder(
    r(r"^20\d{2}-\d{2}-\d{2}$"),
    file(w("*.csv")),
    file(w("metadata.json"))
)
```

**Common errors:**
- `MandatoryMissedError` - Required folder is missing
- `NotDirectoryError` - Path exists but is a file, not a directory
- `ExtraItemsError` - Folder contains files/folders not matched by any child validator

---

### Sidecar validator (`SidecarValidator` /  `sidecar`)

Validates paired files with matching names but different extensions.

**Signature:**
```python
sidecar(
    main_pattern: RegexPattern,
    sidecar_pattern: RegexPattern
) -> SidecarValidator

SidecarValidator(
    main_pattern: RegexPattern,
    sidecar_pattern: RegexPattern
)
```

**Parameters:**
- `main_pattern` - Regex pattern for main files (must have capture groups)
- `sidecar_pattern` - Regex pattern for sidecar files (must have same number of capture groups)

**Description:**

The sidecar validator ensures that for every file matching the main pattern, there exists a corresponding file matching the sidecar pattern with the same captured groups.

Both patterns must:
- Be regex patterns (created with `r()`)
- Have at least one capture group `(...)`
- Have the same number of capture groups

The captured parts must match between main and sidecar files.

**Examples:**

```python
from valifold import sidecar, r

# Each .jpg must have a .json metadata file
sidecar(
    main_pattern=r(r"^(.+)\.jpg$"),
    sidecar_pattern=r(r"^(.+)\.json$")
)
# ✓ photo_001.jpg + photo_001.json
# ✓ photo_002.jpg + photo_002.json
# ✗ photo_003.jpg exists, but photo_003.json is missing

# Each video must have subtitles
sidecar(
    main_pattern=r(r"^(.+)\.mp4$"),
    sidecar_pattern=r(r"^(.+)\.srt$")
)
# ✓ episode_01.mp4 + episode_01.srt
# ✗ episode_02.mp4 exists without episode_02.srt

# Database backup pairs
sidecar(
    main_pattern=r(r"^backup_(\d{8})\.sql$"),
    sidecar_pattern=r(r"^backup_(\d{8})\.sha256$")
)
# ✓ backup_20240115.sql + backup_20240115.sha256
# ✗ backup_20240116.sql without .sha256 checksum

# Multiple capture groups
sidecar(
    main_pattern=r(r"^(\w+)_(\d{3})\.raw$"),
    sidecar_pattern=r(r"^(\w+)_(\d{3})\.xml$")
)
# ✓ photo_001.raw + photo_001.xml
# ✓ image_042.raw + image_042.xml
# ✗ photo_001.raw without photo_001.xml
# ✗ photo_001.raw + image_001.xml (names don't match)
```

**Real-world examples:**

```python
# Photo metadata
sidecar(
    main_pattern=r(r"^(.+)\.jpg$"),
    sidecar_pattern=r(r"^(.+)\.json$")
)

# Video subtitles
sidecar(
    main_pattern=r(r"^(.+)\.mp4$"),
    sidecar_pattern=r(r"^(.+)\.srt$")
)

# RAW + processed pairs
sidecar(
    main_pattern=r(r"^(.+)\.raw$"),
    sidecar_pattern=r(r"^(.+)\.jpg$")
)

# Data + metadata
sidecar(
    main_pattern=r(r"^data_(\d+)\.csv$"),
    sidecar_pattern=r(r"^data_(\d+)\.yaml$")
)

# Document + signature
sidecar(
    main_pattern=r(r"^(.+)\.pdf$"),
    sidecar_pattern=r(r"^(.+)\.sig$")
)
```

**Important notes:**
- Only checks files that match the main pattern.
- Extra sidecar files (without main files) are allowed.
- Both patterns must use regex (not wildcards).
- Capture groups must be identical between patterns.

**Common errors:**
- `NoSidecarError` - Main file exists but corresponding sidecar file is missing
- `ValueError` - If patterns don't have capture groups or have different numbers of groups

---

### XOR Validator (`XorValidator` / `xor(a, b)`, `only_one(*options)`, `at_least_one(*options)`)

Ensures exactly one (or a specific number) of the given options is valid.

**Signature:**
```python
xor(a: Validator, b: Validator) -> XorValidator
only_one(*options: Validator) -> XorValidator
at_least_one(*options: Validator) -> XorValidator

XorValidator(
    children: list[Validator],
    min_checks: int,
    max_checks: int | None
)
```

**Parameters:**
- `a`, `b` - Two validators (for `xor`)
- `*options` - Multiple validators (for `only_one` and `at_least_one`)
- `children` - Subvalidators that will be run against corresponding folder (for `XorValidator`).
- `min_checks` - Minimum number of checks to success for validator to pass (for `XorValidator`).
- `max_checks` - Maximum number of checks to success for validator to pass (for `XorValidator`). Not checked if `None` is given.

**Description:**

XOR validators provide conditional logic:
- `xor(a, b)` - Exactly one of `a` or `b` must be valid (alias for `only_one`)
- `only_one(...)` - Exactly one of the options must be valid
- `at_least_one(...)` - One or more options must be valid

**Examples:**

**Basic XOR:**
```python
from valifold import xor, file, w

# Either config.json OR config.yaml, not both
xor(
    file(w("config.json")),
    file(w("config.yaml"))
)
# ✓ Only config.json exists
# ✓ Only config.yaml exists
# ✗ Both files exist
# ✗ Neither file exists
```

**Only One:**
```python
from valifold import only_one, file, folder, w

# Exactly one README format
only_one(
    file(w("README.md")),
    file(w("README.txt")),
    file(w("README.rst"))
)
# ✓ Only README.md exists
# ✗ Both README.md and README.txt exist
# ✗ No README files exist

# Either setup.py OR pyproject.toml
only_one(
    file(w("setup.py")),
    file(w("pyproject.toml"))
)
# ✓ Only setup.py exists
# ✓ Only pyproject.toml exists
# ✗ Both exist (ambiguous setup)
# ✗ Neither exists (can't install)

# Config as file OR folder
only_one(
    file(w("config.json")),
    folder(
        w("config"), 
        file(w("*.yaml"))
    )
)
# ✓ config.json file exists
# ✓ config/ folder with .yaml files exists
# ✗ Both config.json and config/ exist
# ✗ Neither exists
```

**At Least One:**
```python
from valifold import at_least_one, file, w

# At least one source code file
at_least_one(
    file(w("*.py")),
    file(w("*.js")),
    file(w("*.rs"))
)
# ✓ At least one .py file exists
# ✓ Both .py and .js files exist
# ✓ All three types exist
# ✗ No source files exist

# At least one documentation format
at_least_one(
    file(w("*.md")),
    file(w("*.txt")),
    file(w("*.rst"))
)
# ✓ README.md exists
# ✓ Both .md and .txt files exist
# ✗ No documentation files

# At least one data format
at_least_one(
    file(w("*.csv")),
    file(w("*.json")),
    file(w("*.xml"))
)
# ✓ data.csv exists
# ✓ Multiple formats exist
# ✗ No data files
```

**Real-world examples:**

```python
# Python project setup (old vs new style)
only_one(
    file(w("setup.py")),
    file(w("pyproject.toml"))
)

# License file (various formats)
only_one(
    file(w("LICENSE")),
    file(w("LICENSE.md")),
    file(w("LICENSE.txt"))
)

# Config location
only_one(
    file(w("config.json")),
    file(w("config.yaml")),
    folder(w("config"))
)

# At least one test file
at_least_one(
    file(w("test_*.py")),
    file(w("*_test.py"))
)

# At least one image format
at_least_one(
    file(w("*.jpg")),
    file(w("*.png")),
    file(w("*.webp"))
)

# Documentation must exist
at_least_one(
    file(w("README.md")),
    folder(w("docs"))
)
```

**Important notes:**
- All options are fully validated, not just checked for existence
- Use `only_one` when options are mutually exclusive
- Use `at_least_one` when multiple options can coexist
- Nested validators inside XOR options are fully validated

**Common errors:**
- `AllValidationsFailedError` - None of the options passed validation
- `ManyOptionsError` - More than one option passed (for `only_one`/`xor`)
- `FewOptionsError` - Not enough options matched (for `at_least_one` with min > 1)

---

### Anything Validator

Allows any files or folders without validation.

**Signature:**
```python
anything() -> AnyValidator

AnyValidator()
```

**Parameters:** None

**Description:**

The anything validator matches any file or folder and always passes validation. It's used to explicitly allow any unspecified content in a folder.


**Examples:** 

```python
from valifold import anything, folder, file, w

# Allow any content in temp folder
folder(
    w("temp"),
    anything()
)
# ✓ temp/ with any files and folders
# ✓ temp/ empty
# ✓ temp/ with any structure

# Project with flexible assets
folder(
    w("project"),
    file(w("README.md")),
    folder(
        w("assets"),
        anything()  # Any images, fonts, etc.
    )
)

# Cache folder can have anything
folder(
    w("cache"),
    anything()
)
# No validation of cache contents

# Build output folder
folder(
    w("build"),
    anything()  # Generated files, any structure
)
```

**Real-world examples:**

```python
# Project with unrestricted assets
folder(
    w("static"),
    folder(
        w("css"), 
        file(w("*.css"))
    ), 
    folder(
        w("js"), 
        file(w("*.js"))
    ), 
    folder(
        w("images"), 
        anything()  # Any image files 
    )  
)

# Cache directory
folder(
    w(".cache"),
    anything()
)

# User uploads
folder(
    w("uploads"),
    anything()  # Users can upload any files
)

# Build artifacts
folder(
    w("dist"),
    anything()  # Compiled output, any structure
)

# Temporary files
folder(
    w("tmp"),
    anything()
)
```

**When to use:**
- Folders with dynamically generated content
- User-uploaded files
- Cache directories
- Build output directories
- Any location where you don't want to enforce structure

**Important notes:**
- Always passes validation
- Matches any file or folder name
- Doesn't enforce any structure
- Use sparingly - only where structure truly doesn't matter

---

## Complete Examples

### Python Package

```python
from valifold import folder, file, only_one, w

structure = folder(
    w("my_package"),
    
    # Required files
    file(w("README.md")),
    file(w("LICENSE")),
    
    # Either old or new setup style
    only_one(
        file(w("setup.py")),
        file(w("pyproject.toml"))
    ),
    
    # Optional files
    file(w("requirements.txt"), is_optional=True),
    file(w(".gitignore"), is_optional=True),
    
    # Source folder
    folder(
        w("src"),
        file(w("__init__.py")),
        file(w("*.py"))
    ),
    
    # Tests folder
    folder(
        w("tests"),
        file(w("__init__.py"), is_optional=True),
        file(w("test_*.py"))
    ),
    
    # Optional docs
    folder(
        w("docs"),
        file(w("*.md")),
        is_optional=True
    )
)
```

### Photo Archive with Metadata

```python
from valifold import folder, file, sidecar, w, r

structure = folder(
    w("photos"),
    
    # Date-organized folders
    folder(
        r(r"^20\d{2}-\d{2}-\d{2}$"),  # 2024-01-15
        
        # Images and metadata
        file(w("*.jpg")),
        file(w("*.json")),
        
        # Each photo must have metadata
        sidecar(
            main_pattern=r(r"^(.+)\.jpg$"),
            sidecar_pattern=r(r"^(.+)\.json$")
        ),
        
        # Optional README
        file(w("README.md"), is_optional=True)
    ),
    
    # Optional archive folder
    folder(
        w("archive"),
        file(w("*.zip")),
        is_optional=True
    )
)
```

### Web Application

```python
from valifold import folder, file, xor, anything, w

structure = folder(
    w("webapp"),
    
    # Main app file
    file(w("app.py")),
    
    # Config: file or folder
    xor(
        file(w("config.json")),
        folder(w("config"), file(w("*.yaml")))
    ),
    
    # Static assets
    folder(
        w("static"),
        folder(w("css"), file(w("*.css"))),
        folder(w("js"), file(w("*.js"))),
        folder(w("images"), anything())  # Any images
    ),
    
    # Templates
    folder(
        w("templates"),
        file(w("*.html"))
    ),
    
    # Optional uploads
    folder(
        w("uploads"),
        anything(),
        is_optional=True
    )
)
```

---

## Error Handling

```python
from pathlib import Path
from valifold import folder, file, w

structure = folder(
    w("project"),
    file(w("README.md"))
)

errors = structure.validate_as_root(Path("project"))

if errors:
    for error in errors:
        print(f"Error: {error.formatted_message()}")
        print(f"Type: {type(error).__name__}")
        print(f"Paths: {error.paths}")
```

**Error Types:**
- `MandatoryMissedError` - Required file/folder missing
- `NotFileError` - Path is not a file
- `NotDirectoryError` - Path is not a directory  
- `ExtraItemsError` - Unexpected files/folders found
- `NoSidecarError` - Sidecar file missing
- `AllValidationsFailedError` - No XOR options passed
- `ManyOptionsError` - Too many XOR options matched
- `FewOptionsError` - Too few options matched

---

## License

MIT License - see [LICENSE.md](LICENSE.md)

## Author

Igor Djachenko