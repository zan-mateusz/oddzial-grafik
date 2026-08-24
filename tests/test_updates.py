"""Testy aktualizacji programu. Serwis jest podstawiany — bez sieci."""
import hashlib
import json
from pathlib import Path

import pytest

from app.core import updates
from app.core.updates import Release, UpdateError

REPO = "przyklad/grafik"


def _release_json(version="1.1.0", assets=None):
    if assets is None:
        assets = [
            {"name": f"Grafik-Instalator-{version}.exe",
             "browser_download_url": f"https://example/inst-{version}.exe",
             "size": 90 * 1024 * 1024},
            {"name": f"Grafik-{version}-przenosny.exe",
             "browser_download_url": f"https://example/port-{version}.exe",
             "size": 42 * 1024 * 1024},
            {"name": "SHA256SUMS.txt",
             "browser_download_url": "https://example/SHA256SUMS.txt"},
        ]
    return json.dumps({
        "tag_name": f"v{version}", "body": "Poprawki liczenia urlopu.",
        "assets": assets,
    }).encode()


@pytest.fixture
def fake_service(monkeypatch):
    """Podstawia warstwę sieciową i notuje odpytane adresy."""
    responses: dict[str, bytes] = {}
    calls: list[str] = []

    def fetch(url):
        calls.append(url)
        if url not in responses:
            raise UpdateError(f"nieznany adres: {url}")
        return responses[url]

    monkeypatch.setattr(updates, "_fetch", fetch)
    return responses, calls


# --- porównywanie wersji ---------------------------------------------------

@pytest.mark.parametrize("candidate,current,expected", [
    ("1.0.1", "1.0.0", True),
    ("1.10.0", "1.9.0", True),      # porównanie liczbowe, nie tekstowe
    ("2.0", "1.9.9", True),
    ("1.0.0", "1.0.0", False),
    ("0.9.9", "1.0.0", False),
    ("1.0", "1.0.0", False),
    ("v1.2.0", "1.1.0", True),
])
def test_is_newer(candidate, current, expected):
    assert updates.is_newer(candidate, current) is expected


@pytest.mark.parametrize("text,expected", [
    ("1.2.3", (1, 2, 3)), ("v1.2.3", (1, 2, 3)), ("1.0.0-dev", (1, 0, 0)),
    ("", (0,)), ("bez-numeru", (0,)),
])
def test_parse_version(text, expected):
    assert updates.parse_version(text) == expected


# --- odpytanie serwisu ------------------------------------------------------

def test_finds_a_newer_release(fake_service, monkeypatch):
    responses, _ = fake_service
    responses[f"https://api.github.com/repos/{REPO}/releases/latest"] = _release_json()
    monkeypatch.setattr(updates, "__version__", "1.0.0")
    monkeypatch.setattr(updates, "install_kind", lambda: "installer")

    release = updates.latest_release(REPO)
    assert release.version == "1.1.0"
    assert "Instalator" in release.filename
    assert release.checksum_url.endswith("SHA256SUMS.txt")
    assert release.notes


def test_portable_build_gets_the_portable_asset(fake_service):
    responses, _ = fake_service
    responses[f"https://api.github.com/repos/{REPO}/releases/latest"] = _release_json()
    release = updates.latest_release(REPO, kind="portable")
    assert "przenosny" in release.filename


def test_no_update_when_versions_match(fake_service, monkeypatch):
    responses, _ = fake_service
    responses[f"https://api.github.com/repos/{REPO}/releases/latest"] = \
        _release_json(version="1.0.0")
    monkeypatch.setattr(updates, "install_kind", lambda: "installer")
    monkeypatch.setattr(updates, "is_newer", lambda v, c=None: False)
    assert updates.check_for_update(REPO) is None


def test_release_without_a_matching_file_is_reported(fake_service):
    responses, _ = fake_service
    responses[f"https://api.github.com/repos/{REPO}/releases/latest"] = _release_json(
        assets=[{"name": "notatki.txt", "browser_download_url": "https://example/x"}]
    )
    with pytest.raises(UpdateError, match="nie zawiera"):
        updates.latest_release(REPO, kind="installer")


@pytest.mark.parametrize("repo", ["", "   ", "bez-ukosnika", "/"])
def test_bad_repository_setting_is_reported_clearly(repo):
    with pytest.raises(UpdateError, match="Nie ustawiono|Uzupełnij"):
        updates.latest_release(repo)


def test_network_problems_produce_a_readable_message(monkeypatch):
    import urllib.error

    def boom(request, timeout=None):
        raise urllib.error.URLError("brak sieci")

    monkeypatch.setattr(updates.urllib.request, "urlopen", boom)
    with pytest.raises(UpdateError, match="internetem"):
        updates.latest_release(REPO)


# --- pobieranie i suma kontrolna -------------------------------------------

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self._offset = 0
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, size=-1):
        chunk = self._payload[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def payload_service(monkeypatch):
    payload = b"udawany instalator" * 5000
    digest = hashlib.sha256(payload).hexdigest()

    monkeypatch.setattr(
        updates.urllib.request, "urlopen",
        lambda request, timeout=None: _FakeResponse(payload),
    )
    return payload, digest


def _release(checksum_url="https://example/SHA256SUMS.txt"):
    return Release(
        version="1.1.0", notes="", download_url="https://example/inst.exe",
        filename="Grafik-Instalator-1.1.0.exe", size=0, checksum_url=checksum_url,
    )


def test_download_writes_the_file_and_reports_progress(
    payload_service, tmp_path, monkeypatch
):
    payload, digest = payload_service
    monkeypatch.setattr(
        updates, "expected_checksum", lambda url, name: digest
    )
    seen: list[tuple[int, int]] = []
    path = updates.download(_release(), tmp_path, progress=lambda a, b: seen.append((a, b)))

    assert path.exists() and path.read_bytes() == payload
    assert seen and seen[-1][0] == len(payload)
    # Plik tymczasowy nie może zostać po udanym pobraniu.
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_a_file_with_a_wrong_checksum(
    payload_service, tmp_path, monkeypatch
):
    monkeypatch.setattr(updates, "expected_checksum", lambda url, name: "0" * 64)
    with pytest.raises(UpdateError, match="suma kontrolna|sumą kontrolną"):
        updates.download(_release(), tmp_path)
    # Odrzucony plik nie może zostać na dysku.
    assert not list(tmp_path.iterdir())


def test_download_proceeds_when_no_checksum_is_published(
    payload_service, tmp_path, monkeypatch
):
    monkeypatch.setattr(updates, "expected_checksum", lambda url, name: None)
    path = updates.download(_release(checksum_url=""), tmp_path)
    assert path.exists()


def test_download_can_be_cancelled(payload_service, tmp_path):
    with pytest.raises(UpdateError, match="przerwane"):
        updates.download(_release(), tmp_path, cancelled=lambda: True)
    assert not list(tmp_path.iterdir())


def test_checksum_file_is_parsed(fake_service):
    responses, _ = fake_service
    responses["https://example/SHA256SUMS.txt"] = (
        b"aaaa  Grafik-1.1.0-przenosny.exe\n"
        b"bbbb  Grafik-Instalator-1.1.0.exe\n"
    )
    found = updates.expected_checksum(
        "https://example/SHA256SUMS.txt", "Grafik-Instalator-1.1.0.exe"
    )
    assert found == "bbbb"


def test_missing_checksum_entry_returns_none(fake_service):
    responses, _ = fake_service
    responses["https://example/SHA256SUMS.txt"] = b"aaaa  co-innego.exe\n"
    assert updates.expected_checksum(
        "https://example/SHA256SUMS.txt", "Grafik-Instalator-1.1.0.exe"
    ) is None


# --- rodzaj instalacji ------------------------------------------------------

def test_running_from_source_cannot_self_update():
    assert updates.install_kind() == "source"
    assert not updates.can_self_update()


def test_installer_is_not_run_outside_windows(tmp_path, monkeypatch):
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"x")
    monkeypatch.setattr(updates.sys, "platform", "darwin")
    with pytest.raises(UpdateError, match="Windows"):
        updates.run_installer(installer)


def test_installer_missing_file_is_reported(tmp_path):
    with pytest.raises(UpdateError, match="Nie znaleziono"):
        updates.run_installer(tmp_path / "nie-ma.exe")


# --- reguły pytania użytkownika --------------------------------------------

def test_check_frequency_and_dismissal(tmp_path):
    import datetime as dt

    from app.db import Database
    from app.ui import update_dialog as ud

    db = Database(tmp_path / "t.db")
    assert ud.should_check_today(db)          # nigdy nie sprawdzano
    ud.mark_checked(db)
    assert not ud.should_check_today(db)      # dziś już sprawdzono

    yesterday = (dt.date.today() - dt.timedelta(days=2)).isoformat()
    db.set_setting("update_last_check", yesterday)
    assert ud.should_check_today(db)

    db.set_setting("update_check_enabled", "0")
    assert not ud.should_check_today(db)      # wyłączone w ustawieniach

    assert not ud.was_dismissed(db, "1.1.0")
    ud.dismiss(db, "1.1.0")
    assert ud.was_dismissed(db, "1.1.0")
    # Odmowa dotyczy tylko tej wersji — o nowszą zapytamy ponownie.
    assert not ud.was_dismissed(db, "1.2.0")
    db.close()


def test_corrupted_last_check_date_forces_a_check(tmp_path):
    from app.db import Database
    from app.ui import update_dialog as ud

    db = Database(tmp_path / "t.db")
    db.set_setting("update_last_check", "nonsens")
    assert ud.should_check_today(db)
    db.close()
