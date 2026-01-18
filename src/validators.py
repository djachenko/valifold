from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import List

from pattern import Pattern, RegexPattern


@dataclass(frozen=True)
class Error:
    paths: List[Path]

    @classmethod
    def message(cls) -> str:
        ...


class Validator:
    def validate(self, path: Path) -> List[Error]:
        ...


class Matcher:
    def matches(self, name: str) -> bool:
        ...


@dataclass(frozen=True)
class SubstructureValidator(Validator, Matcher):
    pattern: Pattern
    is_mandatory: bool

    def matches(self, name: str) -> bool:
        return self.pattern.matches(name)

    def validate(self, parent_path: Path) -> List[Error]:
        errors = []
        count = 0

        for item in parent_path.iterdir():
            if self.matches(item.name):
                count += 1
                errors += self.validate_structure(item)

        if count == 0:
            errors.append(f"There is no match for '{self.pattern}' in '{parent_path}'")

        return errors

    def validate_structure(self, self_path: Path) -> List[Error]:
        ...


class FileValidator(SubstructureValidator):
    def validate_structure(self, self_path: Path) -> List[Error]:
        errors = []

        if not self_path.is_file():
            errors.append(f"'{self_path}' is not a file")

        return errors


@dataclass(frozen=True)
class FolderValidator(SubstructureValidator):
    children: List[Validator]

    def validate_structure(self, self_path: Path) -> List[Error]:
        if not self_path.is_dir():
            return [f"'{self_path}' is not a directory"]

        errors = []
        structure_children = []

        for child in self.children:
            errors += child.validate(self_path)

            if isinstance(child, Matcher):
                structure_children.append(child)

        for item in self_path.iterdir():
            if not any(child.matches(item.name) for child in structure_children):
                errors.append(f"'{item}' is extra")

        return errors


@dataclass(frozen=True)
class XorValidator(Validator, Matcher):
    children: List[Validator]
    min_checks: int
    max_checks: int | None

    def __post_init__(self):
        assert self.min_checks >= 0

        if self.max_checks is not None:
            assert self.max_checks > 0
            assert self.min_checks <= self.max_checks

    @cached_property
    def __matching_children(self) -> List[SubstructureValidator]:
        return [child for child in self.children if isinstance(child, SubstructureValidator)]

    def matches(self, name: str) -> bool:
        return any(child.matches(name) for child in self.__matching_children)

    def validate(self, self_path: Path) -> List[Error]:
        error_lists = [child.validate(self_path) for child in self.children]
        success_count = 0

        for error_list in error_lists:
            if not error_list:
                success_count += 1

        errors = []

        if success_count == 0:
            errors.append(f"'{self_path}' failed all validations")

            for error_list in error_lists:
                errors += error_list
        elif success_count < self.min_checks:
            errors.append(f"'{self_path}' matches too few options")
        elif self.max_checks and success_count > self.max_checks:
            errors.append(f"'{self_path}' matches too many options")

        return errors


class AnyValidator(Validator, Matcher):
    def matches(self, name: str) -> bool:
        return True

    def validate(self, path: Path) -> List[Error]:
        return []


@dataclass(frozen=True)
class SidecarValidator(Validator):
    main_pattern: RegexPattern
    sidecar_pattern: RegexPattern

    def __post_init__(self):
        assert self.main_pattern.group_count > 0
        assert self.main_pattern.group_count == self.sidecar_pattern.group_count

    def validate(self, path: Path) -> List[Error]:
        main_matches = set()
        side_matches = set()
        main_map = {}

        for item in path.iterdir():
            main_match = self.main_pattern.match(item.name)

            if main_match:
                groups = main_match.groups()
                main_matches.add(groups)
                main_map[groups] = item

            side_match = self.sidecar_pattern.match(item.name)

            if side_match:
                side_matches.add(side_match.groups())

        errors = []

        for mismatch in main_matches.difference(side_matches):
            item = main_map[mismatch]

            errors.append(f"'{item}' does not have sidecar")

        return errors
