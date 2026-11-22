"""Behaviour of the Mac widget installer: what it checks, installs and runs, and when it stops."""

import json
import subprocess
from pathlib import Path

import pytest

import install_mac_widget as installer

PACKAGE = Path(__file__).resolve().parent.parent / "widgets" / "scriptwidget" / "quote-of-the-day"


class Recorder:
    """Stands in for running commands, and remembers which ones were run."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.commands: list[list[str]] = []
        self.fail_on = fail_on

    def __call__(self, command: list[str]) -> None:
        self.commands.append(command)
        if self.fail_on and self.fail_on in command:
            raise subprocess.CalledProcessError(1, command)


def tools(*installed: str):
    """A `which` that finds only the given tools; brew installs make scriptwidget appear."""
    found = set(installed)

    def which(name: str) -> str | None:
        return f"/opt/homebrew/bin/{name}" if name in found else None

    def runner_hook(command: list[str]) -> None:
        if command[1:3] == ["install", installer.CLI_FORMULA]:
            found.add("scriptwidget")

    return which, runner_hook


def mac() -> tuple[str, str]:
    return "Darwin", "27.0.1"


@pytest.fixture
def app(tmp_path: Path) -> Path:
    path = tmp_path / "ScriptWidget.app"
    path.mkdir()
    return path


class TestChecksTheMac:
    def test_accepts_macos_26_and_later(self):
        installer.check_macos("Darwin", "26.0")
        installer.check_macos("Darwin", "27.0.1")

    @pytest.mark.parametrize(
        ("system", "version", "message"),
        [("Linux", "", "on a Mac"), ("Darwin", "15.6", "macOS 26"), ("Darwin", "", "macOS 26")],
    )
    def test_rejects_other_systems_and_older_macos(self, system, version, message):
        with pytest.raises(installer.SetupError, match=message):
            installer.check_macos(system, version)

    def test_reports_the_problem_and_stops(self, capsys):
        runner = Recorder()

        assert installer.main(system=lambda: ("Linux", ""), runner=runner) == 1
        assert runner.commands == []
        assert "on a Mac" in capsys.readouterr().err


class TestInstallsTheCommandLineTool:
    def test_uses_an_existing_install(self):
        which, _ = tools("brew", "scriptwidget")
        runner = Recorder()

        assert installer.ensure_cli(which, runner) == "/opt/homebrew/bin/scriptwidget"
        assert runner.commands == []

    def test_installs_it_with_homebrew(self):
        which, hook = tools("brew")
        runner = Recorder()

        def run(command: list[str]) -> None:
            runner(command)
            hook(command)

        assert installer.ensure_cli(which, run) == "/opt/homebrew/bin/scriptwidget"
        assert runner.commands == [["/opt/homebrew/bin/brew", "install", installer.CLI_FORMULA]]

    def test_needs_homebrew(self):
        which, _ = tools()
        with pytest.raises(installer.SetupError, match=r"brew\.sh"):
            installer.ensure_cli(which, Recorder())

    def test_notices_when_homebrew_did_not_provide_it(self):
        which, _ = tools("brew")
        with pytest.raises(installer.SetupError, match="PATH"):
            installer.ensure_cli(which, Recorder())


class TestChecksTheApp:
    def test_finds_the_first_installed_copy(self, tmp_path, app):
        assert installer.find_app((tmp_path / "missing.app", app)) == app
        assert installer.find_app((tmp_path / "missing.app",)) is None

    def test_uses_an_installed_app(self, app):
        runner = Recorder()

        assert installer.ensure_app(app, runner) == app
        assert runner.commands == []

    def test_opens_the_app_store_and_stops_when_missing(self):
        runner = Recorder()

        with pytest.raises(installer.SetupError, match="run this script again"):
            installer.ensure_app(None, runner)
        assert runner.commands == [["open", installer.APP_STORE_URL]]


@pytest.fixture
def library(tmp_path: Path) -> Path:
    path = tmp_path / "Scripts"
    path.mkdir()
    return path


class TestFindsTheLibrary:
    def test_uses_the_library_once_the_app_has_made_it(self, library):
        assert installer.ensure_library(library) == library

    def test_asks_to_open_the_app_with_icloud_on(self, tmp_path):
        with pytest.raises(installer.SetupError, match="iCloud Drive"):
            installer.ensure_library(tmp_path / "missing")


class TestInstallsTheWidget:
    def test_checks_it_then_copies_it_into_the_library(self, library):
        runner = Recorder()

        target = installer.install_widget("scriptwidget", PACKAGE, library, runner)

        assert target == library / "Quote of the Day"
        assert runner.commands == [["scriptwidget", "check", str(PACKAGE)]]
        assert (target / "main.jsx").read_text() == (PACKAGE / "main.jsx").read_text()

    def test_replaces_an_older_version(self, library):
        old = library / "Quote of the Day"
        old.mkdir()
        (old / "leftover.js").write_text("old")

        installer.install_widget("scriptwidget", PACKAGE, library, Recorder())

        assert sorted(path.name for path in old.iterdir()) == ["main.jsx", "widget.json"]

    def test_installs_nothing_when_the_check_fails(self, library):
        with pytest.raises(subprocess.CalledProcessError):
            installer.install_widget("scriptwidget", PACKAGE, library, Recorder(fail_on="check"))
        assert list(library.iterdir()) == []

    def test_downloads_the_package_without_a_clone(self, tmp_path):
        urls: list[str] = []

        def download(url: str) -> bytes:
            urls.append(url)
            return url.encode()

        package = installer.fetch_package(tmp_path, download)

        assert sorted(path.name for path in package.iterdir()) == ["main.jsx", "widget.json"]
        assert urls == [
            f"{installer.RAW_BASE}/quote-of-the-day/{name}" for name in installer.PACKAGE_FILES
        ]
        assert (package / "main.jsx").read_bytes() == urls[1].encode()

    def test_package_name_matches_the_library_folder(self):
        manifest = json.loads((PACKAGE / "widget.json").read_text())
        source = (PACKAGE / "main.jsx").read_text()

        assert manifest["name"] == installer.WIDGET_NAME
        assert manifest["entry"] == "main.jsx"
        assert manifest["networkDomains"] == ["alexpizarroj.github.io"]
        assert "https://alexpizarroj.github.io/quotes/today.json" in source


class TestRunsEverything:
    def test_sets_up_from_a_clone_and_prints_the_last_steps(self, app, library, capsys):
        which, _ = tools("brew", "scriptwidget")
        runner = Recorder()

        status = installer.main(
            system=mac, which=which, runner=runner, app=app, scripts_dir=library
        )

        assert status == 0
        assert runner.commands == [
            ["/opt/homebrew/bin/scriptwidget", "check", str(installer.LOCAL_PACKAGE)]
        ]
        assert (library / "Quote of the Day" / "widget.json").exists()
        assert "Edit Widgets" in capsys.readouterr().out

    def test_downloads_the_package_when_run_without_a_clone(self, tmp_path, app, library):
        which, _ = tools("scriptwidget")

        status = installer.main(
            system=mac,
            which=which,
            runner=Recorder(),
            app=app,
            scripts_dir=library,
            local_package=tmp_path / "missing",
            downloader=lambda _url: b"{}",
        )

        assert status == 0
        assert (library / "Quote of the Day" / "widget.json").read_bytes() == b"{}"

    def test_stops_before_installing_without_the_library(self, tmp_path, app, capsys):
        which, _ = tools("scriptwidget")
        runner = Recorder()

        status = installer.main(
            system=mac, which=which, runner=runner, app=app, scripts_dir=tmp_path / "missing"
        )

        assert status == 1
        assert runner.commands == []
        assert "iCloud Drive" in capsys.readouterr().err

    def test_reports_a_failed_command(self, app, library, capsys):
        which, _ = tools("scriptwidget")
        runner = Recorder(fail_on="check")

        status = installer.main(
            system=mac, which=which, runner=runner, app=app, scripts_dir=library
        )

        assert status == 1
        assert "This command failed" in capsys.readouterr().err

    def test_runs_commands_and_raises_on_failure(self):
        installer.run(["true"])
        with pytest.raises(subprocess.CalledProcessError):
            installer.run(["false"])

    def test_reads_this_system(self):
        system, version = installer.this_system()
        assert system
        assert isinstance(version, str)

    def test_downloads_over_https(self, monkeypatch):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self) -> bytes:
                return b"content"

        opened: list[str] = []
        monkeypatch.setattr(
            installer.urllib.request,
            "urlopen",
            lambda url, **_: opened.append(url) or Response(),
        )

        assert installer.download("https://example.com/file") == b"content"
        assert opened == ["https://example.com/file"]
