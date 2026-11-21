"""
Local test harness for OCS Python Evaluator code strings.

The OCS Python Evaluator (``apps/evaluations/evaluators.py`` ``PythonEvaluator``)
calls evaluator code with:

    main(input, output, context, full_history, generated_response, **kwargs)

where ``**kwargs`` carries:
    participant_data  – dict captured at message time
    session_state     – dict captured at message time (EvaluationMessage.session_state;
                         this is the PERSISTENT session state written by set_session_state_key,
                         NOT temp_state; temp_state from set_temp_state_key is ephemeral and
                         never appears here — nodes.py:1167 vs 1190)

This harness validates code against that signature and executes it with the
same RestrictedPython sandbox parameters used by ``_PinnedExecutor`` in
``ocs/tests/sandbox.py``, adapted for the evaluator argument list.

Primary source: apps/evaluations/evaluators.py lines 185–241, 200–206
OCS commit: 9f5c25476555ff74a167c6a14832ce798832847a

Usage::

    from ocs.evaluations.evaluator_harness import EvaluatorHarness
    harness = EvaluatorHarness(code_string)
    result = harness.run(input={...}, output={}, context={...},
                         generated_response="...", session_state={...})
"""

import datetime
import inspect
import json
import re
import time
from typing import Any

from RestrictedPython import (
    compile_restricted,
    limited_builtins,
    safe_builtins,
    utility_builtins,
)
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import guarded_iter_unpack_sequence

# OCS PythonEvaluator._get_function_args()
# Source: apps/evaluations/evaluators.py line 206
_EVALUATOR_ARGS = [
    "input",
    "output",
    "context",
    "full_history",
    "generated_response",
    "**kwargs",
]

# Allowed imports inside evaluator code (same as the OCS sandbox allow-list)
_ALLOWED_MODULES = {"json", "re", "datetime", "time", "random"}


class EvaluatorCodeError(Exception):
    """Raised when evaluator code fails OCS Python Evaluator validation or execution."""


class EvaluatorHarness:
    """
    Compile and execute OCS Python Evaluator code strings locally.

    Mirrors the behaviour of ``PythonEvaluator.run()`` without requiring a live
    OCS/Django environment.  Useful for TDD verification of evaluator code
    strings before they are pasted into the OCS UI.

    Does NOT guarantee identical RestrictedPython behaviour to the production
    OCS host (which uses a newer ``restricted_write`` guard from
    ``python_execution.py``), but provides sufficient coverage for signature,
    logic, and fail-closed testing.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        self._validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        try:
            byte_code = compile_restricted(self.code, filename="<inline code>", mode="exec")
        except SyntaxError as exc:
            raise EvaluatorCodeError(str(exc)) from exc

        custom_locals: dict[str, Any] = {}
        exec(byte_code, {}, custom_locals)  # noqa: S102

        if "main" not in custom_locals:
            raise EvaluatorCodeError("You must define a 'main' function")

        for name, item in custom_locals.items():
            if name != "main" and inspect.isfunction(item):
                raise EvaluatorCodeError("You can only define a single function 'main' at the top level.")

        self._validate_signature(custom_locals["main"])

    def _validate_signature(self, main_fn: Any) -> None:
        """Validate main() matches the OCS PythonEvaluator signature exactly."""
        sig = inspect.signature(main_fn)
        params = list(sig.parameters.values())

        if len(params) != len(_EVALUATOR_ARGS):
            raise EvaluatorCodeError(
                f"main() must have signature main({', '.join(_EVALUATOR_ARGS)}). Got {len(params)} parameter(s)."
            )

        for i, (param, expected) in enumerate(zip(params, _EVALUATOR_ARGS, strict=False)):
            if expected.startswith("**"):
                exp_name = expected[2:]
                if param.kind != inspect.Parameter.VAR_KEYWORD or param.name != exp_name:
                    raise EvaluatorCodeError(f"Parameter {i + 1} should be **{exp_name}")
            else:
                if param.name != expected or param.kind not in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    raise EvaluatorCodeError(f"Parameter {i + 1} should be '{expected}'")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _builtins(self) -> dict[str, Any]:
        builtins: dict[str, Any] = safe_builtins.copy()
        builtins.update(
            {
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "all": all,
                "any": any,
                "datetime": datetime,
                "dict": dict,
                "isinstance": isinstance,
                "enumerate": enumerate,
                "float": float,
            }
        )
        builtins.update(utility_builtins)
        builtins.update(limited_builtins)
        allowed = _ALLOWED_MODULES

        def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name not in allowed:
                raise ImportError(f"Importing '{name}' is not allowed")
            return __import__(name, *args, **kwargs)

        builtins["__import__"] = guarded_import
        return builtins

    def _all_globals(self) -> dict[str, Any]:
        return {
            "__builtins__": self._builtins(),
            "json": json,
            "re": re,
            "datetime": datetime,
            "time": time,
            "_getitem_": default_guarded_getitem,
            "_getiter_": default_guarded_getiter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_write_": lambda x: x,
        }

    def run(  # noqa: PLR0913
        self,
        input: dict,  # noqa: A002
        output: dict,
        context: dict,
        full_history: str = "",
        generated_response: str = "",
        participant_data: dict | None = None,
        session_state: dict | None = None,
    ) -> dict:
        """Execute the evaluator and return its result dict.

        Mirrors ``PythonEvaluator.compile_and_execute_code()`` argument passing.
        ``participant_data`` and ``session_state`` are passed as **kwargs inside
        the evaluator's main().
        """
        custom_locals: dict[str, Any] = {}
        exec(  # noqa: S102
            compile_restricted(self.code, filename="<inline_code>", mode="exec"),
            self._all_globals(),
            custom_locals,
        )
        result = custom_locals["main"](
            input,
            output,
            context,
            full_history,
            generated_response,
            participant_data=participant_data or {},
            session_state=session_state or {},
        )
        if not isinstance(result, dict):
            raise EvaluatorCodeError(f"Evaluator main() must return a dict; got {type(result).__name__}")
        return result
