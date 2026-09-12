"""Pure helpers for validating Amigurumi AI update metadata."""
import urllib.parse

APP_VERSION = "0.7.4"


def version_tuple(version):
    try:
        return tuple(int(x) for x in str(version).split('.')[:4])
    except Exception:
        return (0,)


def validate_update_manifest(manifest, current_version=APP_VERSION):
    latest = str(manifest.get('version', '')).strip()
    url = str(manifest.get('installer_url', '')).strip()
    sha = str(manifest.get('sha256', '')).strip()
    parsed = urllib.parse.urlparse(url)
    valid_sha = len(sha) == 64 and all(c in '0123456789abcdefABCDEF' for c in sha)
    if latest and parsed.scheme == 'https' and parsed.netloc and valid_sha and version_tuple(latest) > version_tuple(current_version):
        return latest, url, sha
    return None
