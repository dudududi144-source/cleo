from __future__ import annotations

import pytest

from cleo.application import Application
from cleo.commands.command import Command
from cleo.exceptions import CleoError
from cleo.exceptions import ExitCodeError
from cleo.testers.application_tester import ApplicationTester


class _ExitCodeCommand(Command):
    """
    A tiny command whose ``handle`` raises an arbitrary exception.

    Set the :attr:`to_raise` attribute on an instance to control what is
    raised at execution time.
    """

    name = "exit-code-raiser"
    to_raise: Exception | None = None

    def handle(self) -> int:
        assert self.to_raise is not None
        raise self.to_raise


class _SimpleCommand(Command):
    """
    A command whose ``handle`` raises an :class:`ExitCodeError` with the
    configured ``code``.
    """

    name = "boom"
    code: int = 42

    def handle(self) -> int:
        raise ExitCodeError(self.code)


def _make_tester(command: Command) -> ApplicationTester:
    app = Application()
    app.add(command)
    return ApplicationTester(app)


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------


def test_exit_code_error_is_a_cleo_error() -> None:
    """``ExitCodeError`` must be a subclass of the public ``CleoError``."""
    assert issubclass(ExitCodeError, CleoError)
    assert issubclass(ExitCodeError, Exception)


def test_exit_code_error_stores_exit_code_attribute() -> None:
    """The provided exit code must be accessible as ``exc.exit_code``."""
    exc = ExitCodeError(42)
    assert exc.exit_code == 42


@pytest.mark.parametrize("code", [1, 42, 100, 254, 255])
def test_exit_code_error_accepts_valid_codes(code: int) -> None:
    """Codes in the closed interval ``1..255`` are accepted."""
    exc = ExitCodeError(code)
    assert exc.exit_code == code
    assert isinstance(exc, ExitCodeError)


@pytest.mark.parametrize("code", [-1, 0, 256, 300, 1000])
def test_exit_code_error_rejects_codes_below_one(code: int) -> None:
    """Any code outside ``1..255`` must raise at construction time."""
    with pytest.raises(ValueError):
        ExitCodeError(code)


def test_exit_code_error_rejects_zero() -> None:
    """Zero is outside the valid range (1..255) and must raise."""
    with pytest.raises(ValueError):
        ExitCodeError(0)


def test_exit_code_error_rejects_three_hundred() -> None:
    """A clearly-out-of-range value must raise."""
    with pytest.raises(ValueError):
        ExitCodeError(300)


# ---------------------------------------------------------------------------
# Application-level integration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", [1, 2, 42, 100, 255])
def test_application_exit_code_for_exit_code_error(code: int) -> None:
    """A command raising ``ExitCodeError(code)`` must make the app exit with ``code``."""
    cmd = _SimpleCommand()
    cmd.code = code
    tester = _make_tester(cmd)

    assert tester.execute("boom") == code


def test_application_default_exit_code_for_unrelated_exception() -> None:
    """An unrelated exception must still produce exit code 1."""
    cmd = _ExitCodeCommand()
    cmd.to_raise = ValueError("not an ExitCodeError")
    tester = _make_tester(cmd)

    assert tester.execute("exit-code-raiser") == 1


def test_application_default_exit_code_for_runtime_error() -> None:
    """A bare ``RuntimeError`` must keep the default behavior of exit code 1."""
    cmd = _ExitCodeCommand()
    cmd.to_raise = RuntimeError("kaboom")
    tester = _make_tester(cmd)

    assert tester.execute("exit-code-raiser") == 1


def test_application_renders_trace_for_exit_code_error() -> None:
    """
    Raising ``ExitCodeError`` from a command must still produce the standard
    error rendering (same rendering as for any other uncaught exception).
    """
    cmd = _SimpleCommand()
    tester = _make_tester(cmd)

    assert tester.execute("boom") == 42

    error_output = tester.io.fetch_error()
    # The simple trace renders the exception's string form, which for our
    # ``ExitCodeError(42)`` is "Command exited with code 42".
    assert "Command exited with code 42" in error_output


def test_application_renders_trace_for_default_exception() -> None:
    """The default rendering must remain unchanged for a regular exception."""
    cmd = _ExitCodeCommand()
    cmd.to_raise = ValueError("boom-default")
    tester = _make_tester(cmd)

    assert tester.execute("exit-code-raiser") == 1

    error_output = tester.io.fetch_error()
    # Simple trace renders the exception's string form, which is the message
    # passed to the constructor.
    assert "boom-default" in error_output


# ---------------------------------------------------------------------------
# Edge case: a raised ExitCodeError whose exit_code is the boundary value
# ---------------------------------------------------------------------------


def test_application_exit_code_lower_boundary() -> None:
    """The lower boundary value 1 must be honored exactly."""
    cmd = _SimpleCommand()
    cmd.code = 1
    tester = _make_tester(cmd)

    assert tester.execute("boom") == 1


def test_application_exit_code_upper_boundary() -> None:
    """The upper boundary value 255 must be honored exactly."""
    cmd = _SimpleCommand()
    cmd.code = 255
    tester = _make_tester(cmd)

    assert tester.execute("boom") == 255