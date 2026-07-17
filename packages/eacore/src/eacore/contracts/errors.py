class EACoreError(Exception):
    """Base error for neutral-kernel failures."""


class CompatibilityError(EACoreError):
    """Raised when a persisted contract cannot be read compatibly."""


class UnsupportedMajorVersionError(CompatibilityError):
    """Raised when a contract major version is unsupported."""


class IntegrityError(EACoreError):
    """Raised when canonical content does not match its integrity metadata."""


class ConflictingIdentifierError(IntegrityError):
    """Raised when one stable identifier is reused with different content."""


class TransitionInvariantError(EACoreError):
    """Raised when a proposed outcome violates a universal invariant."""


class ManifestPathError(EACoreError):
    """Raised when a manifest path escapes its configured root."""
