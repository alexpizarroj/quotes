"""Set up the quote of the day as a native macOS desktop widget, using ScriptWidget.

From a clone:   python3 scripts/install_mac_widget.py
Without one:    python3 -c "$(curl -fsSL https://raw.githubusercontent.com/alexpizarroj/quotes/main/scripts/install_mac_widget.py)"

Safe to run again: each step is skipped when it is already done, and the widget is replaced with
the latest version. It needs macOS 26 or later and Homebrew. It installs the ScriptWidget
command-line tool, checks that the ScriptWidget app is installed (opening its App Store page if
not), validates the widget and copies it into the app's iCloud library, which also syncs it to
your other Macs. Adding the widget to the desktop is the one step macOS can't automate; the script
prints how.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/alexpizarroj/quotes/main/widgets/scriptwidget"
PACKAGE_NAME = "quote-of-the-day"
PACKAGE_FILES = ("widget.json", "main.jsx")
# The app names a widget's folder after the "name" in its widget.json.
WIDGET_NAME = "Quote of the Day"
CLI_FORMULA = "everettjf/tap/scriptwidget-cli"
APP_STORE_URL = "macappstore://apps.apple.com/app/id1555600758"
APP_PATHS = (Path("/Applications/ScriptWidget.app"), Path.home() / "Applications/ScriptWidget.app")
# Where the Mac app keeps its widgets when iCloud Drive is on (its default).
SCRIPTS_DIR = Path.home() / "Library/Mobile Documents/iCloud~ScriptWidget/Documents/Scripts"
MINIMUM_MACOS = 26

LOCAL_PACKAGE = Path(__file__).resolve().parent.parent / "widgets" / "scriptwidget" / PACKAGE_NAME

FINAL_STEPS = f"""\
"{WIDGET_NAME}" is now in ScriptWidget's library. If the app was already open and doesn't list it,
quit and reopen it. Then add the widget to the desktop:
  1. Right-click the desktop and choose "Edit Widgets…"
  2. Search for ScriptWidget and drag a widget of the size you like onto the desktop
  3. Right-click the widget, choose "Edit Widget" and pick "{WIDGET_NAME}"
"""


class SetupError(Exception):
    """A problem the person running the script has to fix before trying again."""


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)  # noqa: S603 - fixed commands, no shell


def step(message: str) -> None:
    print(f"\n==> {message}")


def check_macos(system: str, version: str) -> None:
    if system != "Darwin":
        raise SetupError("This script sets up a macOS widget; run it on a Mac.")
    major = int(version.split(".", maxsplit=1)[0] or 0)
    if major < MINIMUM_MACOS:
        raise SetupError(f"ScriptWidget needs macOS {MINIMUM_MACOS} or later; this is {version}.")


def ensure_cli(which: Callable[[str], str | None], runner: Callable[[list[str]], None]) -> str:
    """Return the path of the scriptwidget tool, installing it with Homebrew if needed."""
    found = which("scriptwidget")
    if found:
        print(f"Already installed: {found}")
        return found
    brew = which("brew")
    if not brew:
        raise SetupError("Homebrew is required. Install it from https://brew.sh and run again.")
    runner([brew, "install", CLI_FORMULA])
    found = which("scriptwidget")
    if not found:
        raise SetupError("Homebrew finished, but the scriptwidget command isn't on the PATH.")
    return found


def find_app(paths: tuple[Path, ...] = APP_PATHS) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def ensure_app(app: Path | None, runner: Callable[[list[str]], None]) -> Path:
    """Return the ScriptWidget app, or open its App Store page and stop if it's missing."""
    if app:
        print(f"Already installed: {app}")
        return app
    runner(["open", APP_STORE_URL])
    raise SetupError(
        "The ScriptWidget app isn't installed. Its App Store page is open: "
        "install it, open it once, then run this script again."
    )


def ensure_library(scripts_dir: Path) -> Path:
    """Return the app's widget library, which exists once the app has been opened."""
    if not scripts_dir.is_dir():
        raise SetupError(
            "ScriptWidget's iCloud library wasn't found. Make sure iCloud Drive is on, "
            "open ScriptWidget once, then run this script again."
        )
    return scripts_dir


def fetch_package(destination: Path, download: Callable[[str], bytes]) -> Path:
    """Download the widget package, for when the script runs without a clone of the repo."""
    package = destination / PACKAGE_NAME
    package.mkdir(parents=True)
    for name in PACKAGE_FILES:
        (package / name).write_bytes(download(f"{RAW_BASE}/{PACKAGE_NAME}/{name}"))
    return package


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - fixed https URL
        return response.read()


def install_widget(
    cli: str, package: Path, scripts_dir: Path, runner: Callable[[list[str]], None]
) -> Path:
    """Validate the package, then copy it into the library, replacing any older version."""
    runner([cli, "check", str(package)])
    target = scripts_dir / WIDGET_NAME
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(package, target)
    print(f"Installed: {target}")
    return target


def fail(message: str) -> int:
    # Flush the progress so far first, so the error appears after it when output is piped.
    sys.stdout.flush()
    print(f"\n{message}", file=sys.stderr)
    return 1


def this_system() -> tuple[str, str]:
    return platform.system(), platform.mac_ver()[0]


def main(  # noqa: PLR0913 - each argument lets the tests stand in for the real system
    *,
    system: Callable[[], tuple[str, str]] = this_system,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[[list[str]], None] = run,
    app: Path | None = None,
    scripts_dir: Path = SCRIPTS_DIR,
    local_package: Path = LOCAL_PACKAGE,
    downloader: Callable[[str], bytes] = download,
) -> int:
    try:
        check_macos(*system())
        step("ScriptWidget command-line tool")
        cli = ensure_cli(which, runner)
        step("ScriptWidget app")
        ensure_app(app or find_app(), runner)
        library = ensure_library(scripts_dir)
        step(f"Installing the {WIDGET_NAME} widget")
        with tempfile.TemporaryDirectory(prefix="quote-widget-") as workdir:
            package = (
                local_package
                if local_package.is_dir()
                else fetch_package(Path(workdir), downloader)
            )
            install_widget(cli, package, library, runner)
    except SetupError as error:
        return fail(str(error))
    except subprocess.CalledProcessError as error:
        return fail(f"This command failed: {' '.join(error.cmd)}")
    step("Last step, by hand")
    print(FINAL_STEPS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
