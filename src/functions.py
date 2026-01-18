from pattern import Pattern, RegexPattern
from validators import Validator, FolderValidator, FileValidator, SidecarValidator, XorValidator, AnyValidator


def folder(pattern: Pattern, *children: Validator, is_mandatory: bool = True) -> Validator:
    return FolderValidator(
        pattern=pattern,
        is_mandatory=is_mandatory,
        children=list(children),
    )


def file(pattern: Pattern, is_mandatory: bool = True) -> Validator:
    return FileValidator(
        pattern=pattern,
        is_mandatory=is_mandatory,
    )


def sidecar(main_pattern: RegexPattern, sidecar_pattern: RegexPattern) -> Validator:
    return SidecarValidator(
        main_pattern=main_pattern,
        sidecar_pattern=sidecar_pattern,
    )


def xor(a: Validator, b: Validator) -> Validator:
    return only_one(a, b)


def only_one(*options: Validator) -> XorValidator:
    return XorValidator(
        children=list(options),
        min_checks=1,
        max_checks=1
    )


def at_least_one(*options: Validator) -> Validator:
    return XorValidator(
        children=list(options),
        min_checks=1,
        max_checks=None
    )


def anything() -> Validator:
    return AnyValidator()
