import fnmatch
import re
from dataclasses import dataclass
from functools import cached_property
from re import Match


class Pattern:
    def matches(self, name: str) -> bool:
        ...


@dataclass(frozen=True)
class BasePattern(Pattern):
    pattern: str

    def __post_init__(self):
        assert isinstance(self.pattern, str)


class RegexPattern(BasePattern):
    @cached_property
    def __compiled(self) -> re.Pattern[str]:
        return re.compile(self.pattern)

    @property
    def group_count(self) -> int:
        return self.__compiled.groups

    def match(self, name: str) -> Match[str] | None:
        return self.__compiled.match(name)

    def matches(self, name: str) -> bool:
        return bool(self.match(name))


class WildcardPattern(BasePattern):
    def matches(self, name: str) -> bool:
        return fnmatch.fnmatch(name, self.pattern)


def w(pattern: str) -> WildcardPattern:
    return WildcardPattern(pattern)


def r(pattern: str) -> RegexPattern:
    return RegexPattern(pattern)
