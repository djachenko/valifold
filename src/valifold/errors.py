from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class ValifoldError:
    paths: list[Path]
    message: str | None = None
    default_message: ClassVar[str | None] = None

    @property
    def _message_format(self) -> str:
        return self.message or self.default_message or ""

    def __post_init__(self):
        if not self.paths:
            raise ValueError("Paths must not be empty")

        if not self._message_format:
            raise ValueError("Message or default message should be not empty or None")

    def formatted_message(self, root_path: Path | None = None) -> str:
        if root_path:
            string_paths = [str(path.relative_to(root_path)) for path in self.paths]
        else:
            string_paths = [path.name for path in self.paths]

        if len(string_paths) > 1:
            formatted_paths = " and ".join([
                ", ".join(string_paths[:-1]),
                string_paths[-1],
            ])
        else:
            formatted_paths = string_paths[0]

        return self._message_format.format(paths=formatted_paths)


class MandatoryMissedError(ValifoldError):
    default_message = "Mandatory paths {paths} are missed"


class NotFileError(ValifoldError):
    default_message = "{paths} is not a file"


class NotDirectoryError(ValifoldError):
    default_message = "{paths} is not a directory"


class ExtraItemsError(ValifoldError):
    default_message = "Extra items found: {paths}"


class AllValidationsFailedError(ValifoldError):
    default_message = "{paths} failed all validations"


class FewOptionsError(ValifoldError):
    default_message = "{paths} matches too few options"


class ManyOptionsError(ValifoldError):
    default_message = "{paths} matches too many options"


class NoSidecarError(ValifoldError):
    default_message = "{paths} do not have sidecar"
