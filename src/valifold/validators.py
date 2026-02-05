from abc import abstractmethod, ABC
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from valifold.errors import ValifoldError, MandatoryMissedError, NotDirectoryError, ExtraItemsError, ManyOptionsError, \
    FewOptionsError, AllValidationsFailedError, NotFileError, NoSidecarError
from valifold.pattern import Pattern, RegexPattern


class Validator(ABC):
    @abstractmethod
    def validate(self, path: Path) -> list[ValifoldError]:
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
    is_optional: bool

    def matches(self, name: str) -> bool:
        return self.pattern.matches(name)

    def validate(self, parent: Path) -> list[ValifoldError]:
        errors = []
        count = 0

        for child in parent.iterdir():
            if self.matches(child.name):
                count += 1
                errors += self.validate_structure(child)

        if count == 0 and not self.is_optional:
            errors.append(MandatoryMissedError([parent], f"There is no match for '{self.pattern}' in '{{path}}'"))

        return errors

    def validate_as_root(self, path: Path) -> list[ValifoldError]:
        errors = []

        if self.matches(path.name) and path.exists():
            errors.extend(self.validate_structure(path))
        elif not self.is_optional:
            errors.append(MandatoryMissedError([path]))

        return errors

    @abstractmethod
    def validate_structure(self, path: Path) -> list[ValifoldError]:
        ...


class FileValidator(SubstructureValidator):
    def validate_structure(self, self_path: Path) -> list[ValifoldError]:
        errors: list[ValifoldError] = []

        if not self_path.is_file():
            errors.append(NotFileError([self_path]))

        return errors


@dataclass(frozen=True)
class FolderValidator(SubstructureValidator):
    children: list[Validator]

    @cached_property
    def _structure_children(self) -> list[Matcher]:
        return [child for child in self.children if isinstance(child, Matcher)]

    def validate_structure(self, self_path: Path) -> list[ValifoldError]:
        if not self_path.is_dir():
            return [NotDirectoryError([self_path])]

        errors = []

        for child in self.children:
            errors += child.validate(self_path)

        extra_items = []

        for item in self_path.iterdir():
            if not any(child.matches(item.name) for child in self._structure_children):
                extra_items.append(item)

        if extra_items:
            errors.append(ExtraItemsError(extra_items))

        return errors


@dataclass(frozen=True)
class XorValidator(Validator, Matcher):
    children: list[Validator]
    min_checks: int
    max_checks: int | None

    def __post_init__(self):
        if not self.min_checks >= 0:
            raise ValueError(f"Minimum number of checks should be greater than or equal to 0,"
                             f" but {self.min_checks} is given")

        if self.max_checks is not None:
            if not self.max_checks > 0:
                raise ValueError(f"Maximum number of checks should be greater than 0, but {self.max_checks} is given")

            if not self.min_checks <= self.max_checks:
                raise ValueError(f"Maximum number of checks should be greater than or equal to minimum number,"
                                 f"but {self.max_checks} and {self.min_checks} are given correspondingly")

    @cached_property
    def _matching_children(self) -> list[SubstructureValidator]:
        return [child for child in self.children if isinstance(child, SubstructureValidator)]

    def matches(self, name: str) -> bool:
        return any(child.matches(name) for child in self._matching_children)

    def validate(self, parent: Path) -> list[ValifoldError]:
        error_lists = [child.validate(parent) for child in self.children]
        success_count = 0

        for error_list in error_lists:
            if not error_list:
                success_count += 1

        errors: list[ValifoldError] = []

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

    def validate(self, path: Path) -> list[ValifoldError]:
        return []


@dataclass(frozen=True)
class SidecarValidator(Validator):
    main_pattern: RegexPattern
    sidecar_pattern: RegexPattern

    def __post_init__(self):
        if not self.main_pattern.group_count > 0:
            raise ValueError("Main pattern should have at least one capture group")

        if not self.sidecar_pattern.group_count > 0:
            raise ValueError("Sidecar pattern should have at least one capture group")

        if not self.main_pattern.group_count == self.sidecar_pattern.group_count:
            raise ValueError("Main and sidecar pattern should have equal count of capture groups")

    def validate(self, path: Path) -> list[ValifoldError]:
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

        errors: list[ValifoldError] = []

        if mismatched_items := [main_map[mismatch] for mismatch in main_matches.difference(side_matches)]:
            errors.append(NoSidecarError(mismatched_items))

        return errors
