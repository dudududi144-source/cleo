from __future__ import annotations

import pytest

from cleo.application import Application
from cleo.commands.command import Command
from cleo.exceptions import CleoError
from cleo.exceptions import CleoUserError
from cleo.exceptions import ExitCodeError
from cleo.testers.application_tester import ApplicationTester


class _ExitCodeCommand(Command):
    """
    A command that raises ``ExitCodeError(<code>)``.

    The code is provided so the same command class can be reused to test
    every supported (or rejected) exit code.
    """

    def __init__(self, code: int = 1) -> None:
        super().__init__()
        self._code = code

    @property
    def name(self) -> str:  # type: ignore[override]
        return "boom"

    def handle(self) -> int:
        raise ExitCodeError(self._code)


class _RaisingCommand(Command):
    """
    A command that raises a plain (non-cleo) exception to verify the
    default application behaviour is unchanged.
    """

    def __init__(self, exc: Exception | None = None) -> None:
        super().__init__()
        self._exc = exc if exc is not None else ValueError("boom-default")

    @property
    def name(self) -> str:  # type: ignore[override]
        return "bad"

    def handle(self) -> int:
        raise self._exc


def test_exit_code_error_is_exported_from_cleo_exceptions() -> None:
    # The class must be importable from cleo.exceptions.
    from cleo.exceptions import ExitCodeError as Imported

    assert Imported is ExitCodeError


def test_exit_code_error_is_a_user_error() -> None:
    # ExitCodeError must inherit CleoUserError so the application uses the
    # same "simple" rendering as for other user errors.
    assert issubclass(ExitCodeError, CleoUserError)
    assert issubclass(ExitCodeError, CleoError)
    assert issubclass(ExitCodeError, Exception)


def test_exit_code_error_stores_exit_code_attribute() -> None:
    error = ExitCodeError(42)

    assert error.exit_code == 42


def test_application_exits_with_custom_code_when_command_raises_exit_code_error() -> None:
    app = Application()
    app.add(_ExitCodeCommand(code=42))

    tester = ApplicationTester(app)
    code = tester.execute("boom")

    assert code == 42


def test_application_exits_with_custom_code_for_various_codes() -> None:
    for custom_code in (1, 2, 7, 100, 127, 200, 255):
        app = Application()
        app.add(_ExitCodeCommand(code=custom_code))

        tester = ApplicationTester(app)
        code = tester.execute("boom")

        assert code == custom_code, (
            f"expected exit code {custom_code}, got {code}"
        )


def test_application_default_exit_code_is_one_for_non_cleo_exception() -> None:
    app = Application()
    app.add(_RaisingCommand(ValueError("boom-default")))

    tester = ApplicationTester(app)
    code = tester.execute("bad")

    assert code == 1


def test_application_default_exit_code_is_one_for_runtime_error() -> None:
    app = Application()
    app.add(_RaisingCommand(RuntimeError("boom-runtime")))

    tester = ApplicationTester(app)
    code = tester.execute("bad")

    assert code == 1


def test_application_default_exit_code_for_keyboard_interrupt_is_one() -> None:
    app = Application()
    app.add(_RaisingCommand(KeyboardInterrupt()))

    tester = ApplicationTester(app)
    code = tester.execute("bad")

    assert code == 1


def test_exit_code_error_rejects_zero() -> None:
    with pytest.raises(Exception):
        ExitCodeError(0)


def test_exit_code_error_rejects_negative_codes() -> None:
    with pytest.raises(Exception):
        ExitCodeError(-1)

    with pytest.raises(Exception):
        ExitCodeError(-100)


def test_exit_code_error_rejects_codes_above_255() -> None:
    with pytest.raises(Exception):
        ExitCodeError(256)

    with pytest.raises(Exception):
        ExitCodeError(300)

    with pytest.raises(Exception):
        ExitCodeError(1000)


def test_exit_code_error_accepts_boundary_values() -> None:
    low = ExitCodeError(1)
    high = ExitCodeError(255)

    assert low.exit_code == 1
    assert high.exit_code == 255


def test_exit_code_error_rejects_non_integer() -> None:
    with pytest.raises(Exception):
        ExitCodeError(1.5)  # type: ignore[arg-type]

    with pytest.raises(Exception):
        ExitCodeError("1")  # type: ignore[arg-type]

    with pytest.raises(Exception):
        ExitCodeError(None)  # type: ignore[arg-type]


def test_exit_code_error_can_be_raised_and_caught() -> None:
    # Standard raise / catch contract.
    with pytest.raises(ExitCodeError) as exc_info:
        raise ExitCodeError(7)

    assert exc_info.value.exit_code == 7


def test_application_does_not_raise_exit_code_error_when_catching_enabled() -> None:
    # When catch_exceptions is enabled (the default), the application must
    # swallow the ExitCodeError and return its exit_code instead of letting
    # the exception propagate out of run().
    app = Application()
    app.add(_ExitCodeCommand(code=13))

    assert app.are_exceptions_caught() is True

    tester = ApplicationTester(app)
    code = tester.execute("boom")

    assert code == 13


def test_application_propagates_exit_code_error_when_catching_disabled() -> None:
    # When catch_exceptions is disabled, the ExitCodeError must propagate
    # out of the application unchanged so users can decide how to handle
    # it (the user can read ``error.exit_code`` themselves).
    app = Application()
    app.catch_exceptions(False)
    app.add(_ExitCodeCommand(code=99))

    tester = ApplicationTester(app)

    with pytest.raises(ExitCodeError) as exc_info:
        tester.execute("boom")

    assert exc_info.value.exit_code == 99