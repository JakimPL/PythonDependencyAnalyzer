"""Test scope resolution in exception handling blocks with imports and shadowing."""

from typing import Any


def basic_exception_handling() -> None:
    outer_variable = "outer"

    try:
        try_variable = "try_block"
        result = int("not_a_number")
    except ValueError as exception:
        except_variable = "except_block"
        error_message = str(exception)
    else:
        else_variable = "else_block"
    finally:
        finally_variable = "finally_block"


def exception_with_shadowing() -> None:
    shadowed_name: Any = "initial"

    try:
        shadowed_name = "in_try"
        operation_result = 1 / 0
    except ZeroDivisionError as zero_div_exception:
        handler_variable = str(zero_div_exception)
        shadowed_name = "in_except"
    else:
        shadowed_name = "in_else"
    finally:
        shadowed_name = "in_finally"

    after_blocks = shadowed_name


def nested_exception_blocks() -> None:
    outer_scope = "outer"

    try:
        outer_try = "outer_try"

        try:
            inner_try = "inner_try"
            risky_operation = 1 / 0
        except ZeroDivisionError as inner_exception:
            inner_except = str(inner_exception)
        finally:
            inner_finally = "inner_finally"

    except Exception as outer_exception:
        outer_except = str(outer_exception)
    finally:
        outer_finally = "outer_finally"


def exception_with_imports() -> None:
    try:
        import json
        from pathlib import Path

        try_json = json.dumps({"key": "value"})
        try_path = Path("/tmp")
    except ImportError as import_exception:
        import sys

        except_sys = sys.version
        except_error = str(import_exception)
    else:
        import os
        from typing import Dict

        else_environ: Dict[str, str] = os.environ.copy()
    finally:
        import re
        from datetime import datetime

        finally_pattern = re.compile(r"\d+")
        finally_time = datetime.now()


def multiple_exception_types() -> None:
    handling_variable = "initial"

    try:
        try_variable = "trying"
        potentially_failing_operation = int("42")
    except ValueError as value_error:
        value_error_handler = str(value_error)
        handling_variable = "value_error"
    except TypeError as type_error:
        type_error_handler = str(type_error)
        handling_variable = "type_error"
    except (KeyError, IndexError) as key_or_index_error:
        combined_handler = str(key_or_index_error)
        handling_variable = "key_or_index"
    except Exception as general_exception:
        general_handler = str(general_exception)
        handling_variable = "general"
    else:
        else_handler = "success"
        handling_variable = "else"
    finally:
        finally_handler = "cleanup"
        handling_variable = "finally"


def exception_in_comprehension() -> None:
    outer_value = "outer"

    try:
        comprehension_with_exceptions = [item for item in range(10) if (checked := item > 5) or outer_value]
    except Exception as comprehension_exception:
        exception_in_comprehension_handler = str(comprehension_exception)


def exception_in_nested_function() -> None:
    outer_exception_variable = "outer"

    def inner_with_exception() -> None:
        inner_variable = "inner"

        try:
            inner_try = "inner_try"
            inner_operation = 1 / 0
        except ZeroDivisionError as inner_zero_error:
            inner_except = str(inner_zero_error)
            access_outer = outer_exception_variable
        finally:
            inner_finally = "inner_finally"

    try:
        outer_try = "outer_try"
        inner_with_exception()
    except Exception as outer_exception:
        outer_except = str(outer_exception)


def exception_with_walrus_operator() -> None:
    try:
        if (try_walrus := compute_risky_value()) > 0:
            try_result = try_walrus
    except Exception as exception:
        if (except_walrus := handle_error(exception)) is not None:
            except_result = except_walrus
    else:
        if (else_walrus := finalize_success()) is not None:
            else_result = else_walrus
    finally:
        if (finally_walrus := cleanup_resources()) is not None:
            finally_result = finally_walrus


def compute_risky_value() -> int:
    return 42


def handle_error(error: Any) -> Any:
    return None


def finalize_success() -> Any:
    return None


def cleanup_resources() -> Any:
    return None
