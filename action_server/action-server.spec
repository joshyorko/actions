# -*- mode: python ; coding: utf-8 -*-

import argparse
import os
import pprint
import sys
import warnings

# Suppress pkg_resources deprecation warnings from dependencies
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

# Prevent PyInstaller from using the NLTK runtime hook
import PyInstaller.config
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.log import logger
from PyInstaller.utils.hooks import (
    collect_all,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

PyInstaller.config.CONF["excludes"] = ["_pyi_rth_nltk"]

sys.setrecursionlimit(sys.getrecursionlimit() * 5)

logger.info("Collecting action_server dependencies...")
action_server_datas, _action_server_binaries, action_server_hiddenimports = collect_all(
    "actions.server"
)

logger.info("Collecting actions_http dependencies...")
actions_http_datas, _actions_http_binaries, actions_http_hiddenimports = collect_all(
    "actions_http"
)

# Collect redis submodules for control-room-lite mode
logger.info("Collecting redis submodules...")
redis_hiddenimports = collect_submodules("redis")
for h in redis_hiddenimports:
    logger.info(f"Collected redis hiddenimport: {h}")

fastapi_hiddenimports = collect_submodules("fastapi")
psutil_hiddenimports = collect_submodules("psutil")
actions_hiddenimports = collect_submodules("actions")
starlette_hiddenimports = collect_submodules("starlette")
mcp_hiddenimports = collect_submodules("mcp")

# psycopg imports its binary implementation dynamically at runtime.
psycopg_hiddenimports = [
    *collect_submodules("psycopg"),
    *collect_submodules("psycopg_binary"),
]
psycopg_binaries = collect_dynamic_libs("psycopg_binary")
new_datas = []
rcc_datas = [
    data
    for data in action_server_datas
    if data[1] == "actions/server/bin" and os.path.basename(data[0]).startswith("rcc-")
]
for data in action_server_datas:
    if ".mypy_cache" in data[0]:
        continue
    if "__pycache__" in data[0]:
        continue
    if not data[0].endswith(".py") and data not in rcc_datas:
        continue
    logger.info(f"Collected data: {data}")
    new_datas.append(data)
action_server_datas = new_datas


for hiddenimport in action_server_hiddenimports:
    logger.info(f"Collected hiddenimport: {hiddenimport}")

# Parse args to the specfile
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
parser.add_argument("--onefile", action="store_true")
parser.add_argument("--name", type=str, default="action-server")
options = parser.parse_args()

# Log arguments using PyInstaller's logging system
logger.info("=== Build Arguments ===")
logger.info(f"Debug mode: {options.debug}")
logger.info(f"Onefile mode: {options.onefile}")
logger.info(f"Output name: {options.name}")
logger.info("=====================")

logger.info("Starting main Analysis...")

logger.info("Collecting action server submodules...")

a = Analysis(
    ["src/actions/server/__main__.py"],
    pathex=[],
    datas=[
        *action_server_datas,
        *actions_http_datas,
    ],
    binaries=[
        *_action_server_binaries,
        *_actions_http_binaries,
        *psycopg_binaries,
        ("src/actions/server/templates/action-templates.zip", "actions/server/templates"),
        ("src/actions/server/templates/action-templates.yaml", "actions/server/templates"),
    ],
    hiddenimports=[
        *action_server_hiddenimports,
        *actions_http_hiddenimports,
        *redis_hiddenimports,
        *fastapi_hiddenimports,
        *psutil_hiddenimports,
        *actions_hiddenimports,
        *starlette_hiddenimports,
        *mcp_hiddenimports,
        *psycopg_hiddenimports,
        "uvicorn",
        "fastapi",
        "sqlite3",
        "_sqlite3",
        "termcolor",
        "pydantic.deprecated.decorator",
    ],
    hookspath=["pyinstaller-hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "pyarrow"],  # Exclude to avoid NumPy 2.x compatibility errors during analysis
    noarchive=False,
    optimize=0,
)

logger.info("=== Packaging Components ===")
pyz = PYZ(a.pure)

# Executable args
exe_args = [pyz, a.scripts]
if options.onefile:
    exe_args.append(a.binaries)
    exe_args.append(a.datas)
if options.debug:
    exe_args.append([("v", None, "OPTION")])
else:
    exe_args.append([])

# Executable kwargs
exe_kwargs = {
    "name": options.name,
    "bootloader_ignore_signals": False,
    "strip": False,
    "upx": True,
    "console": True,
    "disable_windowed_traceback": False,
    "argv_emulation": False,
    "target_arch": None,
    "codesign_identity": os.environ.get("MACOS_SIGNING_CERT_NAME"),
    "entitlements_file": "./entitlements.mac.plist"
    if os.path.exists("./entitlements.mac.plist")
    else None,
}
if options.debug:
    exe_kwargs["debug"] = True
else:
    exe_kwargs["debug"] = False
if options.onefile:
    exe_kwargs["upx_exclude"] = []
    exe_kwargs["runtime_tmpdir"] = None
else:
    exe_kwargs["exclude_binaries"] = True

logger.info("=== Building Executable ===")
pp = pprint.PrettyPrinter(indent=2)
logger.debug(f"Building executable with the following args:\n{pp.pformat(exe_args)}")
logger.debug(
    f"Building executable with the following kwargs:\n{pp.pformat(exe_kwargs)}"
)

exe = EXE(
    *exe_args,
    **exe_kwargs,
)

if not options.onefile:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=options.name,
    )
