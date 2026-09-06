"""Fetch only small pinned library wheels and inspect metadata/license bytes without imports."""

import argparse
import hashlib
import io
import json
import tomllib
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
PACKAGES = {
    "mlx-lm-lora": ("3.1.2", "MIT", "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"),
    "mlx-tune": ("0.6.0", "Apache-2.0", "f45b671981baeeb94b5a5e2142d1df171c707035c7f05a99f83d63c77f3610f0"),
    "datasets": ("3.6.0", "Apache 2.0", "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    assert urlparse(url).scheme == "https"
    assert urlparse(url).hostname in {"pypi.org", "files.pythonhosted.org"}
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(10 * 1024**2 + 1)
    assert len(data) <= 10 * 1024**2
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-site-packages", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    packages = tomllib.loads((ROOT / "uv.lock").read_text())["package"]
    for name, (version, declared_license, license_digest) in PACKAGES.items():
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        raw = fetch(url)
        (args.evidence_dir / f"{name}-{version}-pypi.json").write_bytes(raw)
        metadata = json.loads(raw)
        assert metadata["info"]["version"] == version
        assert metadata["info"]["license"] == declared_license
        (package,) = [p for p in packages if p["name"] == name and p["version"] == version]
        urls = {item["url"]: item for item in metadata["urls"]}
        for artifact in [package["sdist"], *package["wheels"]]:
            item = urls[artifact["url"]]
            assert item["size"] == artifact["size"]
            assert artifact["hash"] == "sha256:" + item["digests"]["sha256"]
        (wheel,) = package["wheels"]
        data = fetch(wheel["url"])
        assert len(data) == wheel["size"] and digest(data) == wheel["hash"].split(":")[1]
        filename = urls[wheel["url"]]["filename"]
        assert Path(filename).name == filename
        (args.evidence_dir / filename).write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            (license_name,) = [n for n in archive.namelist()
                               if ".dist-info/" in n and n.endswith("/LICENSE")]
            license_data = archive.read(license_name)
            (metadata_name,) = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
            wheel_metadata = BytesParser().parsebytes(archive.read(metadata_name))
        assert digest(license_data) == license_digest
        assert b"Apache License" in license_data and b"Version 2.0, January 2004" in license_data
        assert wheel_metadata["License"] == declared_license
        installed = args.replay_site_packages / license_name
        assert installed.read_bytes() == license_data
        print(json.dumps({"name": name, "version": version, "source": url,
                          "pypi_json_sha256": digest(raw), "wheel_sha256": digest(data),
                          "wheel_bytes": len(data), "metadata_license": declared_license,
                          "license_file": license_name, "license_sha256": license_digest,
                          "bundled_license_header": "Apache License 2.0",
                          "matches_installed_license": True}, sort_keys=True), flush=True)
    print("PASS: pinned PyPI URLs/size/hashes and independent wheel/installed LICENSE bytes match")
    print("RETAINED: mlx-lm-lora metadata MIT differs from bundled Apache License 2.0")


if __name__ == "__main__":
    main()
