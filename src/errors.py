from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, List


@dataclass(frozen=True)
class ValifoldError:
    paths: List[Path]
    message: str | None = None
    default_message: ClassVar[str | None] = None

    def __post_init__(self):
        assert self.message or self.default_message is not None

    def formatted_message(self, root_path: Path | None = None) -> str:
        if root_path:
            string_paths = [str(path.relative_to(root_path)) for path in self.paths]
        else:
            string_paths = [path.name for path in self.paths]

        formatted_paths = " and ".join([
            ",".join(string_paths[:-1]),
            string_paths[-1],
        ])

        message_format = self.message or self.default_message
        return message_format.format(paths=formatted_paths)


class MandatoryMissedError(ValifoldError):
    default_message = "Mandatory paths {paths} are missed"


class NotFileError(ValifoldError):
    default_message = "{paths} is not a file"


class NotDirectoryError(ValifoldError):
    default_message = "{paths} is not a directory"


class ExtraItemsError(ValifoldError):
    default_message = "Extra items found: {paths}"


class AllValidationsFailedError(ValifoldError):
    default_message = "{path} failed all validations"


class FewOptionsError(ValifoldError):
    default_message = "{path} matches too few options"


class ManyOptionsError(ValifoldError):
    default_message = "{path} matches too many options"


class NoSidecarError(ValifoldError):
    default_message = "{path} do not have sidecar"
