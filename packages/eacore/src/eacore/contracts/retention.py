from enum import StrEnum


class RetentionClass(StrEnum):
    RELEASE = "release"
    AUDIT = "audit"
    TRANSIENT = "transient"
    SENSITIVE_REFERENCE = "sensitive_reference"
