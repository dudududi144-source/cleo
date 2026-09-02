from __future__ import annotations

from cleo._utils import find_similar_names


class CleoError(Exception):
    """
    Base Cleo exception.
    """

    exit_code: int | None = None


class CleoLogicError(CleoError):
    """
    Raised when there is error in command arguments
    and/or options configuration logic.
    """


class CleoRuntimeError(CleoError):
    """
    Raised when command is called with invalid options or arguments.
    """


class CleoValueError(CleoError):
    """
    Raised when wrong value was given to Cleo components.
    """


class CleoNoSuchOptionError(CleoError):
    """
    Raised when command does not have given option.
    """


class CleoUserError(CleoError):
    """
    Base exception for user errors.
    """


class CleoMissingArgumentsError(CleoUserError):
    """
    Raised when called command was not given required arguments.
    """


class ExitCodeError(CleoUserError):
    """
    Raised by a command to signal the application that it should exit with
    a specific non-default exit code.

    The application catches this exception and exits with ``exit_code``
    instead of the generic ``1`` it would use for any other exception.

    The provided ``exit_code`` must be in the valid range ``1..255``
    (POSIX process exit status codes). Constructing the class with a
    value outside this range raises ``ValueError``.
    """

    def __init__(self, exit_code: int) -> None:
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise ValueError(
                f"Exit code must be an int, got {type(exit_code).__name__}"
            )

        if exit_code < 1 or exit_code > 255:
            raise ValueError(
                f"Exit code {exit_code} is not in the valid range 1..255"
            )

        super().__init__(f"Command exited with code {exit_code}")
        self.exit_code = exit_code


def _suggest_similar_names(name: str, names: list[str]) -> str | None:
    if not names:
        return None

    suggested_names = find_similar_names(name, names)

    if not suggested_names:
        return None

    newline_separator = "\n    "
    return "Did you mean " + newline_separator.join(
        (
            ("this?" if len(suggested_names) == 1 else "one of these?"),
            newline_separator.join(suggested_names),
        )
    )


class CleoCommandNotFoundError(CleoUserError):
    """
    Raised when called command does not exist.
    """

    def __init__(self, name: str, commands: list[str] | None = None) -> None:
        message = f'The command "{name}" does not exist.'
        if commands:
            suggestions = _suggest_similar_names(name, commands)
            if suggestions:
                message += "\n\n" + suggestions
        super().__init__(message)


class CleoNamespaceNotFoundError(CleoUserError):
    """
    Raised when called namespace has no commands.
    """

    def __init__(self, name: str, namespaces: list[str] | None = None) -> None:
        message = f'There are no commands in the "{name}" namespace.'
        if namespaces:
            suggestions = _suggest_similar_names(name, namespaces)
            if suggestions:
                message += "\n\n" + suggestions
        super().__init__(message)
