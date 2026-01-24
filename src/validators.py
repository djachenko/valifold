from abc import abstractmethod, ABC
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import List

from src.pattern import Pattern, RegexPattern
from src.errors import ValifoldError, MandatoryMissedError, NotDirectoryError, ExtraItemsError, ManyOptionsError, \
    FewOptionsError, AllValidationsFailedError, NotFileError, NoSidecarError


class Validator(ABC):
    @abstractmethod
    def validate(self, path: Path) -> List[ValifoldError]:
        ...


class Matcher(ABC):
    @abstractmethod
    def matches(self, name: str) -> bool:
        ...


class RootValidator(ABC):
    @abstractmethod
    def validate_as_root(self, path: Path) -> list[ValifoldError]:
        ...


@dataclass(frozen=True)
class SubstructureValidator(Validator, Matcher, RootValidator, ABC):
    pattern: Pattern
    is_mandatory: bool

    def matches(self, name: str) -> bool:
        return self.pattern.matches(name)

    def validate(self, parent: Path) -> list[ValifoldError]:
        errors = []
        count = 0

        for child in parent.iterdir():
            if self.matches(child.name):
                count += 1
                errors += self.validate_structure(child)

        if count == 0 and self.is_mandatory:
            errors.append(MandatoryMissedError([parent], f"There is no match for '{self.pattern}' in '{{path}}'"))

        return errors

    def validate_as_root(self, path: Path) -> list[ValifoldError]:
        errors = []

        if self.matches(path.name) and path.exists():
            errors.extend(self.validate_structure(path))
        elif self.is_mandatory:
            errors.append(MandatoryMissedError([path]))

        return errors

    @abstractmethod
    def validate_structure(self, path: Path) -> list[ValifoldError]:
        ...


class FileValidator(SubstructureValidator):
    def validate_structure(self, self_path: Path) -> List[ValifoldError]:
        errors = []

        if not self_path.is_file():
            errors.append(NotFileError([self_path]))

        return errors


@dataclass(frozen=True)
class FolderValidator(SubstructureValidator):
    children: List[Validator]

    def validate_structure(self, self_path: Path) -> List[ValifoldError]:
        if not self_path.is_dir():
            return [NotDirectoryError([self_path])]

        errors = []
        structure_children = []

        for child in self.children:
            errors += child.validate(self_path)

            if isinstance(child, Matcher):
                structure_children.append(child)

        extra_items = []

        for item in self_path.iterdir():
            if not any(child.matches(item.name) for child in structure_children):
                extra_items.append(item)

        if extra_items:
            errors.append(ExtraItemsError(extra_items))

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

    def validate(self, parent: Path) -> List[ValifoldError]:
        error_lists = [child.validate(parent) for child in self.children]
        success_count = 0

        for error_list in error_lists:
            if not error_list:
                success_count += 1

        errors = []

        if success_count == 0:
            errors.append(AllValidationsFailedError([parent]))

            for error_list in error_lists:
                errors += error_list
        elif success_count < self.min_checks:
            errors.append(FewOptionsError([parent]))
        elif self.max_checks and success_count > self.max_checks:
            errors.append(ManyOptionsError([parent]))

        return errors


class AnyValidator(Validator, Matcher):
    def matches(self, name: str) -> bool:
        return True

    def validate(self, path: Path) -> List[ValifoldError]:
        return []


@dataclass(frozen=True)
class SidecarValidator(Validator):
    main_pattern: RegexPattern
    sidecar_pattern: RegexPattern

    def __post_init__(self):
        assert self.main_pattern.group_count > 0
        assert self.main_pattern.group_count == self.sidecar_pattern.group_count

    def validate(self, path: Path) -> List[ValifoldError]:
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

        if mismatched_items := [main_map[mismatch] for mismatch in main_matches.difference(side_matches)]:
            errors.append(NoSidecarError(mismatched_items))

        return errors
