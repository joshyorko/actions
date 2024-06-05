import typing
from enum import Enum
from typing import (
    Any,
    Generic,
    Literal,
    Optional,
    Protocol,
    Sequence,
    TypedDict,
    TypeVar,
)

if typing.TYPE_CHECKING:
    from fastapi.applications import FastAPI

T = TypeVar("T")


class Sentinel(Enum):
    SENTINEL = 0


class ActionResultDict(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Any


class ActionResult(Generic[T]):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Optional[T]

    def __init__(
        self, success: bool, message: Optional[str] = None, result: Optional[T] = None
    ):
        self.success = success
        self.message = message
        self.result = result

    def as_dict(self) -> ActionResultDict:
        return {"success": self.success, "message": self.message, "result": self.result}

    def __str__(self):
        return (
            f"ActionResult(success={self.success!r}, message={self.message!r}, "
            f"result={self.result!r})"
        )

    __repr__ = __str__


class RCCActionResult(ActionResult[str]):
    # A string-representation of the command line.
    command_line: str

    def __init__(
        self,
        command_line: str,
        success: bool,
        message: Optional[str] = None,
        result: Optional[str] = None,
    ):
        ActionResult.__init__(self, success, message, result)
        self.command_line = command_line


class IBeforeStartCallback(Protocol):
    def __call__(self, app: "FastAPI") -> bool:
        """
        Args:
            app: The (fully-configured) fast api app

        Returns: True if it's ok to continue starting up or
            False if the startup process should be stopped.
        """


def check_implements(x: T) -> T:
    """
    Helper to check if a class implements some protocol.

    :important: It must be the last method in a class due to
                https://github.com/python/mypy/issues/9266

        Example:

    def __typecheckself__(self) -> None:
        _: IExpectedProtocol = check_implements(self)

    Mypy should complain if `self` is not implementing the IExpectedProtocol.
    """
    return x


class ArgumentsNamespace(Protocol):
    """
    This is the argparse.Namespace with the arguments provided by the user.
    """

    command: Literal[
        "download-rcc",
        "package",
        "import",
        "start",
        "version",
        "new",
        "migrate",
        "env",
        "cloud",
    ]
    verbose: bool


class ArgumentsNamespaceNew(ArgumentsNamespace):
    command: Literal["new"]
    name: str
    template: str
    new_command: Literal["list-templates"]


class ArgumentsNamespaceNewTemplates(ArgumentsNamespace):
    command: Literal["new"]
    new_command: Literal["list-templates"]
    json: bool


class ArgumentsNamespaceEnv(ArgumentsNamespace):
    command: Literal["env"]
    env_command: Literal["clean-tools-caches"]


class ArgumentsNamespaceDownloadRcc(ArgumentsNamespace):
    command: Literal["download-rcc"]
    file: str


class ArgumentsNamespacePackage(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["update"] | Literal["build"]


class ArgumentsNamespacePackageUpdate(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["update"]
    dry_run: bool
    no_backup: bool


class ArgumentsNamespacePackageBuild(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["build"]
    output_dir: str
    datadir: str
    override: bool


class ArgumentsNamespacePackageExtract(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["extract"]
    output_dir: str
    override: bool


class ArgumentsNamespacePackageMetadata(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["metadata"]
    output_file: Optional[str]


class ArgumentsNamespaceMigrateImportOrStart(ArgumentsNamespace):
    command: Literal["migrate", "import", "start"]
    datadir: str
    db_file: str


class ArgumentsNamespaceMigrate(ArgumentsNamespaceMigrateImportOrStart):
    command: Literal["migrate"]


class ArgumentsNamespaceBaseImportOrStart(ArgumentsNamespaceMigrateImportOrStart):
    command: Literal["import", "start"]
    dir: Sequence[str]
    skip_lint: bool
    whitelist: str


class ArgumentsNamespaceImport(ArgumentsNamespaceBaseImportOrStart):
    command: Literal["import"]


class ArgumentsNamespaceStart(ArgumentsNamespaceBaseImportOrStart):
    command: Literal["start"]
    actions_sync: bool
    expose: bool
    expose_allow_reuse: bool
    api_key: str


class ArgumentsNamespacePackagePush(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["publish"]
    access_credentials: Optional[str]
    hostname: Optional[str]
    organization_id: str
    package_path: str
    json: bool


class ArgumentsNamespacePackageStatus(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["state"]
    access_credentials: Optional[str]
    hostname: Optional[str]
    organization_id: str
    package_id: str
    json: bool


class ArgumentsNamespacePackageChangelog(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["set-changelog"]
    access_credentials: Optional[str]
    organization_id: str
    package_id: str
    json: bool
    change_log: str


class ArgumentsNamespacePackagePublish(ArgumentsNamespace):
    command: Literal["package"]
    package_command: Literal["publish"]
    organization_name: Optional[str]
    access_credentials: Optional[str]
    hostname: Optional[str]
    package_path: str
    change_log: str


class ArgumentsNamespaceCloud(ArgumentsNamespace):
    command: Literal["cloud"]
    cloud_command: Literal["login"]


class ArgumentsNamespaceCloudlogin(ArgumentsNamespace):
    command: Literal["cloud"]
    cloud_command: Literal["login"]
    access_credentials: Optional[str]
    hostname: Optional[str]


class ArgumentsNamespaceCloudVerifyLogin(ArgumentsNamespace):
    command: Literal["cloud"]
    cloud_command: Literal["verify-login"]
    json: bool


class ArgumentsNamespaceCloudOrganizations(ArgumentsNamespace):
    command: Literal["cloud"]
    cloud_command: Literal["list-organizations"]
    access_credentials: Optional[str]
    hostname: Optional[str]
    json: bool


class AsyncActionCallResult(TypedDict):
    run_id: str