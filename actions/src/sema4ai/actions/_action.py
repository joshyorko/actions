import inspect
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, get_type_hints

from robocorp.log import ConsoleMessageKind, console_message
from robocorp.log.protocols import OptExcInfo

from sema4ai.actions._constants import SUPPORTED_TYPES_IN_SCHEMA
from sema4ai.actions._customization._plugin_manager import PluginManager
from sema4ai.actions._protocols import IAction, IContext, Status

if typing.TYPE_CHECKING:
    from sema4ai.actions._action_context import ActionContext, RequestContexts

_map_python_type_to_user_type = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def get_provider_and_scope_from_annotation_args(
    annotation_args, filename: str, name: str
) -> tuple[str, list[str]]:
    from typing import get_args, get_origin

    from sema4ai.actions._exceptions import ActionsCollectError

    error_message = f"""
Invalid OAuth2Secret annotation found.

The OAuth2Secret must be parametrized with 2 arguments,
the first being a Literal with the provider name
(i.e.: `Literal["google"]`)
and the second a list with one Literal with the (multiple) scopes that are required
(i.e.: `list[Literal["scope1", "scope2", ...]])

Full Example for a parameter named `google_secret` requiring google sheets
and google drive scopes:

google_secret: OAuth2Secret[
    Literal["google"],
    list[
        Literal[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ]
    ],
]

File with @action: {filename}
@action name: {name}
"""
    if not annotation_args or len(annotation_args) != 2:
        raise ActionsCollectError(error_message)

    provider = annotation_args[0]
    scopes = annotation_args[1]
    if get_origin(provider) != Literal:
        raise ActionsCollectError(f"First parameter is not a Literal.\n{error_message}")
    if get_origin(scopes) not in (list, List):
        raise ActionsCollectError(f"Second parameter is not a list.\n{error_message}")
    provider_args = get_args(provider)
    if not provider_args or len(provider_args) != 1:
        raise ActionsCollectError(
            f"First parameter does not have a single provider argument.\n{error_message}"
        )
    provider_str = provider_args[0]
    if not isinstance(provider_str, str):
        raise ActionsCollectError(
            f"First parameter Literal does not have a string.\n{error_message}"
        )

    scope_args = get_args(scopes)
    if not scope_args or len(scope_args) != 1:
        raise ActionsCollectError(
            f"Second parameter is not a list with a single Literal.\n{error_message}"
        )

    scope_args_literal = scope_args[0]
    if get_origin(scope_args_literal) != Literal:
        raise ActionsCollectError(
            f"Second parameter is not a list with a single Literal.\n{error_message}"
        )

    scope_strs = get_args(scope_args_literal)
    for entry in scope_strs:
        if not isinstance(entry, str):
            raise ActionsCollectError(
                f"Second parameter is not a list with a literal with strings.\n{error_message}"
            )

    return provider_str, list(scope_strs)


class Action:
    def __init__(
        self,
        pm: PluginManager,
        module_name: str,
        module_file: str,
        method: typing.Callable,
        options: Optional[Dict] = None,
    ):
        self._pm = pm
        self.module_name = module_name
        self.filename = module_file or "<filename unavailable>"
        self.method = method
        self.message = ""
        self.exc_info: Optional[OptExcInfo] = None
        self._status = Status.NOT_RUN
        self.result = None
        self.options = options or None

    @property
    def name(self):
        return self.method.__code__.co_name

    @property
    def lineno(self):
        return self.method.__code__.co_firstlineno

    def run(self, **kwargs):
        sig = inspect.signature(self.method)
        try:
            sig.bind(**kwargs)
        except Exception as e:
            raise RuntimeError(
                f"It's not possible to call the action: '{self.name}' because the passed arguments don't match the action signature.\nError: {e}"
            )
        return self.method(**kwargs)

    def _build_properties(
        self,
        method_name: str,
        param_name: Optional[str],
        param_type: Any,
        description: str,
        kind: Literal["parameter", "return"],
    ) -> Dict[str, Any]:
        """
        Args:
            method_name: The name of the method for which properties are being built.
            param_name: The parameter name (may be None if it's a return)
            param_type: The type of the property (gotten by introspection).
            description: The description for the property.
            kind: Whether this is a parameter or a return.
        """
        from sema4ai.actions._exceptions import InvalidArgumentsError

        if not param_type:
            param_type_clsname = "string"
        else:
            if param_type not in SUPPORTED_TYPES_IN_SCHEMA:
                if not hasattr(param_type, "model_json_schema"):
                    # Not a pydantic type (nor anything with a `model_json_schema`).
                    # We need to convert it to a pydantic type.

                    from sema4ai.actions._raw_types_handler import (
                        _obtain_raw_types_handler,
                    )

                    if param_name is None:
                        param_name = "return_value"

                    try:
                        param_type = _obtain_raw_types_handler(param_name, param_type)
                    except Exception:
                        raise InvalidArgumentsError(
                            f"Error. It was not possible to create the schema for: '{param_name}' in '{method_name}'. Type: {repr(param_type)}."
                        )

                if hasattr(param_type, "model_json_schema"):
                    # Support for pydantic
                    from sema4ai.actions._remove_refs import replace_refs

                    # Note: we inline the references and remove the definitions
                    # because this schema can be added as a part of a larger schema
                    # and in doing so the position of the references will reference
                    # an invalid path.
                    ret = replace_refs(param_type.model_json_schema(by_alias=False))
                    ret.pop("$defs", None)
                    if description:
                        ret["description"] = description
                    if param_name:
                        ret["title"] = param_name.replace("_", " ").title()
                    return ret

                param_type_clsname = (
                    f"Error. The {kind} type '{param_type.__name__}' in '{method_name}' is not supported. "
                    f"Supported {kind} types: str, int, float, bool or pydantic.BaseModel."
                )
            else:
                param_type_clsname = _map_python_type_to_user_type[param_type]

        properties = {
            "type": param_type_clsname,
            "description": description,
        }

        if param_name:
            properties["title"] = param_name.replace("_", " ").title()
        return properties

    @property
    def managed_params_schema(self) -> Dict[str, Any]:
        from typing import get_args

        from sema4ai.actions._commands import _get_managed_param_type, _is_managed_param

        managed_params_schema: Dict[str, Any] = {}
        sig = inspect.signature(self.method)

        param_name_to_description = self._get_param_name_to_description()
        for param in sig.parameters.values():
            if _is_managed_param(self._pm, param.name, param=param):
                tp = _get_managed_param_type(self._pm, param.name, param=param).__name__

                dct: dict[str, Any] = {"type": tp}

                # Note: the description may be overridden in the datasource.
                desc = param_name_to_description.get(param.name)
                if desc:
                    dct["description"] = desc

                if tp == "OAuth2Secret":
                    # In this case we need to make some introspection to get additional information
                    # on the type (provider, scopes, ...)
                    annotation_args = get_args(param.annotation)
                    (
                        provider_str,
                        scope_strs,
                    ) = get_provider_and_scope_from_annotation_args(
                        annotation_args, self.filename, self.name
                    )
                    dct["provider"] = provider_str
                    dct["scopes"] = scope_strs

                elif tp == "DataSource":
                    # Just mark that a datasource is needed here, no need to add additional information
                    # (the metadata on the actual datasources will be added as a separate node in the
                    # metadata, not bound to arguments).
                    pass

                managed_params_schema[param.name] = dct

        return managed_params_schema

    def _get_param_name_to_description(self) -> dict[str, str]:
        import docstring_parser

        param_name_to_description: Dict[str, str] = {}
        doc = getattr(self.method, "__doc__", "")
        if doc:
            contents = docstring_parser.parse(doc)
            for docparam in contents.params:
                if docparam.description:
                    param_name_to_description[docparam.arg_name] = docparam.description

        return param_name_to_description

    @property
    def input_schema(self) -> Dict[str, Any]:
        from sema4ai.actions._commands import _is_managed_param

        sig = inspect.signature(self.method)
        method_name = self.method.__code__.co_name
        type_hints = get_type_hints(self.method)

        param_name_to_description: dict[
            str, str
        ] = self._get_param_name_to_description()

        properties: Dict[str, Any] = {}
        required: List[str] = []

        schema = {
            "properties": properties,
            "type": "object",
        }

        for param in sig.parameters.values():
            if _is_managed_param(self._pm, param.name, param=param):
                continue
            param_type = type_hints.get(param.name)
            description = param_name_to_description.get(param.name, "")
            param_properties = self._build_properties(
                method_name, param.name, param_type, description, "parameter"
            )
            properties[param.name] = param_properties

            if param.default is inspect.Parameter.empty:
                required.append(param.name)
            else:
                default = param.default
                if hasattr(default, "model_dump"):
                    # Support for pydantic
                    default = default.model_dump(mode="json")
                param_properties["default"] = default

        if required:
            schema["required"] = required

        return schema

    @property
    def output_schema(self) -> Dict[str, Any]:
        import docstring_parser

        method_name = self.method.__code__.co_name
        type_hints = get_type_hints(self.method)

        doc = getattr(self.method, "__doc__", "")
        description = ""
        if doc:
            contents = docstring_parser.parse(doc)
            returns = contents.returns
            if returns and returns.description:
                description = returns.description

        schema = self._build_properties(
            method_name, None, type_hints.get("return"), description, "return"
        )
        return schema

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, value: Status):
        self._status = Status(value)

    @property
    def failed(self):
        return self._status == Status.FAIL

    def __typecheckself__(self) -> None:
        from sema4ai.actions._protocols import check_implements

        _: IAction = check_implements(self)

    def __str__(self):
        return f"Action({self.name}, status: {self.status})"

    __repr__ = __str__


class _ActionContext:
    _current_action: Optional[IAction] = None
    _current_action_context: Optional["ActionContext"] = None
    _current_requests_contexts: Optional["RequestContexts"] = None


def set_current_action(action: Optional[IAction]):
    _ActionContext._current_action = action


def get_current_action() -> Optional[IAction]:
    return _ActionContext._current_action


def set_current_action_context(action_context: Optional["ActionContext"]):
    _ActionContext._current_action_context = action_context


def get_current_action_context() -> Optional["ActionContext"]:
    return _ActionContext._current_action_context


def set_current_requests_contexts(requests_contexts: Optional["RequestContexts"]):
    _ActionContext._current_requests_contexts = requests_contexts


def get_current_requests_contexts() -> Optional["RequestContexts"]:
    return _ActionContext._current_requests_contexts


def get_x_action_invocation_context() -> str:
    request_contexts = get_current_requests_contexts()
    if request_contexts is None or request_contexts.invocation_context is None:
        return "{}"  # The value is the x-action-invocation-context to be used in the header

    return request_contexts.invocation_context.initial_data


class Context:
    # Some regular message (generated by the framework).
    KIND_REGULAR = ConsoleMessageKind.REGULAR

    # Some message which deserves a bit more attention (generated by the framework).
    KIND_IMPORTANT = ConsoleMessageKind.IMPORTANT

    # The action name is being written (generated by the framework).
    KIND_TASK_NAME = ConsoleMessageKind.TASK_NAME

    # Some error message (generated by the framework).
    KIND_ERROR = ConsoleMessageKind.ERROR

    # Some traceback message (generated by the framework).
    KIND_TRACEBACK = ConsoleMessageKind.TRACEBACK

    # Some user message which was being sent to the stdout.
    KIND_STDOUT = ConsoleMessageKind.STDOUT

    # Some user message which was being sent to the stderr.
    KIND_STDERR = ConsoleMessageKind.STDERR

    def __init__(
        self, print_result: bool = False, json_output_file: Optional[str] = None
    ):
        self._msg_len_target = 80
        self._print_result = print_result
        self._json_output_file = json_output_file

    def _show_header(self, parts: List[Tuple[str, str]]) -> int:
        """
        Returns:
            The final number of chars used in the full header.
        """
        if not parts:
            self.show("=" * self._msg_len_target)
            return self._msg_len_target

        total_len = sum(len(msg) for (msg, _) in parts)

        # + 2 for the spacing before after the '='.
        diff = self._msg_len_target - (total_len + 2)

        start_sep_chars = 3
        end_sep_chars = 3
        if diff > 0:
            start_sep_chars = int(diff / 2)
            end_sep_chars = diff - start_sep_chars

        final_len = 0
        msg_start = f"{'=' * start_sep_chars} "
        final_len += len(msg_start)
        self.show(msg_start, end="")

        for msg, kind in parts:
            final_len += len(msg)
            self.show(msg, end="", kind=kind)

        msg_end = f" {'=' * end_sep_chars}"
        final_len += len(msg_end)
        self.show(msg_end)

        return final_len

    def show(
        self, msg: str, end: str = "\n", kind=KIND_REGULAR, flush: Optional[bool] = None
    ):
        """
        Shows a message to the user.

        Args:
            msg: The message to be shown.
            end: The end char to be added to the message.
            kind: The kind of the message.
            flush: Whether we should flush after sending the message (if None
                   it's flushed if the end char ends with '\n').
        """
        if end:
            msg = f"{msg}{end}"
        console_message(msg, kind, flush=flush)

    def show_error(self, msg: str, flush: Optional[bool] = None):
        self.show(msg, kind=self.KIND_ERROR, flush=flush)

    def _before_action_run(self, action: IAction):
        self._msg_len_target = 80
        self._msg_len_target = self._show_header(
            [("Running: ", self.KIND_REGULAR), (action.name, self.KIND_TASK_NAME)]
        )

    def _after_action_run(self, action: IAction):
        import json
        import traceback

        msg = ""
        if action.message:
            msg = f"\n{action.message}"

        status_kind = self.KIND_REGULAR
        if action.status == Status.FAIL:
            status_kind = self.KIND_ERROR

        show = self.show

        result = action.result

        show(f"{action.name}", end="", kind=self.KIND_TASK_NAME)
        show(" status: ", end="")
        show(f"{action.status.value}", kind=status_kind)

        if msg:
            show(f"{msg}", kind=status_kind)

            if action.exc_info and action.exc_info[0]:
                self._show_header(
                    [
                        ("Full Traceback (running ", self.KIND_REGULAR),
                        (action.name, self.KIND_TASK_NAME),
                        (")", self.KIND_REGULAR),
                    ]
                )

                self.show(
                    "".join(traceback.format_exception(*action.exc_info)),
                    kind=self.KIND_TRACEBACK,
                )

        contents_to_write = {}
        print_result = bool(self._print_result and result is not None)

        if print_result or self._json_output_file:
            result = action.result
            dump = result
            if hasattr(result, "model_dump"):
                # Support for pydantic
                dump = result.model_dump(mode="json")

            contents_to_write = {
                "result": dump,
                "message": action.message,
                "status": action.status.value,
            }

        if self._json_output_file:
            p = Path(self._json_output_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(contents_to_write))

        if print_result:
            show("result:", kind=self.KIND_IMPORTANT)
            use_pydantic = False
            try:
                result_as_json_str = json.dumps(contents_to_write["result"], indent=4)
            except Exception:
                raise RuntimeError(
                    f"The resulting value: {result} cannot be converted to JSON. Using pydantic: {use_pydantic}."
                )

            show(
                result_as_json_str,
                flush=True,
            )
            # Also validate the return type in this case by recreating the class based on the return annotation.
            try:
                sig = inspect.signature(action.method)
                return_annotation = sig.return_annotation
                if return_annotation is not sig.empty and return_annotation is not None:
                    if hasattr(return_annotation, "model_validate"):
                        return_annotation.model_validate(dump)
                    else:
                        if not isinstance(dump, return_annotation):
                            raise RuntimeError("Invalid return type.")
                else:
                    show(
                        "Note: Unable to validate return type (no return type annotation found in method signature).",
                        kind=self.KIND_ERROR,
                    )

            except Exception as e:
                msg = (
                    f"Although the action: '{action.name}' ran properly, it returned a value of type {type(result)} whereas the expected return type is {return_annotation}.\n"
                    f'Action location:\n  File "{action.method.__code__.co_filename}", line {action.method.__code__.co_firstlineno}, in {action.method.__code__.co_name}\n'
                    f"Validation error: {e}"
                )
                show(msg, kind=self.KIND_ERROR)

        self._show_header([])

    @contextmanager
    def register_lifecycle_prints(self):
        from sema4ai.actions._hooks import after_action_run, before_action_run

        with before_action_run.register(
            self._before_action_run
        ), after_action_run.register(self._after_action_run):
            yield

    def __typecheckself__(self) -> None:
        from sema4ai.actions._protocols import check_implements

        _: IContext = check_implements(self)
