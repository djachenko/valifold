from src.pattern import Pattern, RegexPattern
from src.validators import AnyValidator, Validator, XorValidator, SidecarValidator, FileValidator, FolderValidator


def file(pattern: Pattern, is_mandatory: bool = True) -> FileValidator:
    return FileValidator(
        pattern=pattern,
        is_mandatory=is_mandatory,
    )


def folder(pattern: Pattern, *children: Validator, is_mandatory: bool = True) -> FolderValidator:
    return FolderValidator(
        pattern=pattern,
        is_mandatory=is_mandatory,
        children=list(children),
    )


def sidecar(main_pattern: RegexPattern, sidecar_pattern: RegexPattern) -> SidecarValidator:
    return SidecarValidator(
        main_pattern=main_pattern,
        sidecar_pattern=sidecar_pattern,
    )


def xor(a: Validator, b: Validator) -> XorValidator:
    return only_one(a, b)


def only_one(*options: Validator) -> XorValidator:
    return XorValidator(
        children=list(options),
        min_checks=1,
        max_checks=1
    )


def at_least_one(*options: Validator) -> XorValidator:
    return XorValidator(
        children=list(options),
        min_checks=1,
        max_checks=None
    )


def anything() -> AnyValidator:
    return AnyValidator()
