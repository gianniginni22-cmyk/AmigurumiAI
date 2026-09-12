from app.update_utils import validate_update_manifest, version_tuple


def test_version_tuple():
    assert version_tuple("0.7.4") == (0, 7, 4)
    assert version_tuple("0.7.4.1") == (0, 7, 4, 1)


def test_manifest_accepts_https_newer_version():
    m = {"version": "99.0.0", "installer_url": "https://github.com/example/release.exe", "sha256": "a" * 64}
    assert validate_update_manifest(m, "0.7.4") == ("99.0.0", m["installer_url"], m["sha256"])


def test_manifest_rejects_http():
    m = {"version": "99.0.0", "installer_url": "http://example.com/a.exe", "sha256": "a" * 64}
    assert validate_update_manifest(m, "0.7.4") is None


def test_manifest_rejects_bad_sha():
    m = {"version": "99.0.0", "installer_url": "https://example.com/a.exe", "sha256": "bad"}
    assert validate_update_manifest(m, "0.7.4") is None


def test_manifest_rejects_same_or_older_version():
    for version in ("0.7.4", "0.7.3", "0.6.0"):
        m = {"version": version, "installer_url": "https://example.com/a.exe", "sha256": "a" * 64}
        assert validate_update_manifest(m, "0.7.4") is None
