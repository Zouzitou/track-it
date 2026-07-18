class TrackItError(Exception):
    """Base class for expected application failures."""


class VideoOpenError(TrackItError):
    pass


class UnsupportedVideoError(TrackItError):
    pass


class FrameDecodeError(TrackItError):
    pass


class ModelUnavailableError(TrackItError):
    pass


class ModelIntegrityError(TrackItError):
    pass


class BackendCompatibilityError(TrackItError):
    pass


class TrackingCancelled(TrackItError):
    pass


class TrackingOutOfMemory(TrackItError):
    pass


class ExportConfigurationError(TrackItError):
    pass


class ExportProcessError(TrackItError):
    pass


class ProjectValidationError(TrackItError):
    pass


class ProjectMigrationError(TrackItError):
    pass


class CacheCorruptionError(TrackItError):
    pass


class InsufficientDiskSpaceError(TrackItError):
    pass
