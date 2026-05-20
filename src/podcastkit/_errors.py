from __future__ import annotations

from ._exit_codes import ExitCode


class PodcastKitError(Exception):
    """Base error for podcastkit commands. Always includes an actionable hint."""

    def __init__(
        self,
        message: str,
        *,
        code: ExitCode = ExitCode.GENERAL_ERROR,
        hint: str | None = None,
        hints: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.hint = hint
        self.hints = hints


class InvalidArgsError(PodcastKitError):
    def __init__(self, message: str, *, hint: str | None = None, hints: list[str] | None = None) -> None:
        super().__init__(message, code=ExitCode.INVALID_ARGS, hint=hint, hints=hints)


class NotFoundError(PodcastKitError):
    def __init__(self, message: str, *, hint: str | None = None, hints: list[str] | None = None) -> None:
        super().__init__(message, code=ExitCode.NOT_FOUND, hint=hint, hints=hints)


class PreconditionError(PodcastKitError):
    def __init__(self, message: str, *, hint: str | None = None, hints: list[str] | None = None) -> None:
        super().__init__(message, code=ExitCode.PRECONDITION_FAILED, hint=hint, hints=hints)


class UpstreamError(PodcastKitError):
    def __init__(self, message: str, *, hint: str | None = None, hints: list[str] | None = None) -> None:
        super().__init__(message, code=ExitCode.UPSTREAM_ERROR, hint=hint, hints=hints)
