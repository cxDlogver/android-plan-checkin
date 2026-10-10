"""Inspect the pinned official package in memory; install no application dependencies."""
import base64
import hashlib
import io
import json
import re
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

url = "https://registry.npmjs.org/expo-sqlite/57.0.4"
with urllib.request.urlopen(url, timeout=30) as response:
    metadata = json.load(response)
dist = metadata["dist"]
with urllib.request.urlopen(dist["tarball"], timeout=30) as response:
    package = response.read()
algorithm, expected = dist["integrity"].split("-", 1)
assert algorithm == "sha512"
actual = base64.b64encode(hashlib.sha512(package).digest()).decode("ascii")
assert actual == expected, "Package integrity mismatch"
with tarfile.open(fileobj=io.BytesIO(package), mode="r:gz") as archive:
    header = archive.extractfile("package/vendor/sqlite3/sqlite3.h").read().decode("utf-8")
version = re.search(r'^#define SQLITE_VERSION\s+"([^"]+)"', header, re.MULTILINE).group(1)
source_id = re.search(r'^#define SQLITE_SOURCE_ID\s+"([^"]+)"', header, re.MULTILINE).group(1)
report = {
    "date": datetime.now(timezone.utc).isoformat(),
    "scope": "official_pinned_package_source_only",
    "package": "expo-sqlite", "packageVersion": metadata["version"],
    "metadataUrl": url, "tarballUrl": dist["tarball"],
    "integrity": dist["integrity"], "integrityCheck": "PASS",
    "packageSha256": hashlib.sha256(package).hexdigest(),
    "sqliteVersion": version, "sqliteSourceId": source_id,
    "packageFilesWritten": False, "applicationInstalled": False,
    "androidRuntime": "NOT_RUN",
    "walResetReference": "https://sqlite.org/wal.html#the_wal_reset_bug",
    "requiredArchitecture": "one native connection per business database; all SQL serialized",
}
Path(__file__).with_name("SQLite发布包核查结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"packageVersion": metadata["version"], "integrityCheck": "PASS", "sqliteVersion": version, "androidRuntime": "NOT_RUN"}))
