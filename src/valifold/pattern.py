import fnmatch
import re
from abc import abstractmethod, ABC
from dataclasses import dataclass
from functools import cached_property
from re import Match


class Pattern(ABC):
    @abstractmethod
    def matches(self, name: str) -> bool:
        ...


@dataclass(frozen=True)
class BasePattern(Pattern):
    pattern: str

    def __post_init__(self):
        if not isinstance(self.pattern, str):
            raise TypeError(f"Pattern must be string, got {type(self.pattern)}")


class RegexPattern(BasePattern):
    def __post_init__(self):
        super().__post_init__()

        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {self.pattern}") from e

    @cached_property
    def _compiled(self) -> re.Pattern[str]:
        return re.compile(self.pattern)

    @property
    def group_count(self) -> int:
        return self._compiled.groups

    def match(self, name: str) -> Match[str] | None:
        return self._compiled.match(name)

    def matches(self, name: str) -> bool:
        return bool(self.match(name))


class WildcardPattern(BasePattern):
    def matches(self, name: str) -> bool:
        return fnmatch.fnmatch(name, self.pattern)


def w(pattern: str) -> WildcardPattern:
    return WildcardPattern(pattern)


def r(pattern: str) -> RegexPattern:
    return RegexPattern(pattern)
