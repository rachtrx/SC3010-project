#!/usr/bin/env python3
"""Inspect an XZ source tarball as data; never extracts or executes its contents."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

KNOWN = {
    "m4/build-to-host.m4": None,  # release-only file; not in the Git tag archive
    "tests/files/bad-3-corrupt_lzma2.xz": "ecda10d8877d555dbda4a4eba329e146b2be8ac4b7915fb723eaacc9f89d16bd",
    "tests/files/good-large_compressed.lzma": "9aef898229de60f94cdea42f19268e6e3047f7136f2ff97510390a2deeda7032",
}
EXPECTED_SHA256 = "f334777310ca3ae9ba07206d78ed286a655aa3f44eec27854f740c26b2cd2ed0"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path, help="XZ 5.6.1 Debian orig tarball")
    ap.add_argument("--git-archive", type=Path, help="optional GitHub-generated v5.6.1 source archive")
    ap.add_argument("--output", type=Path, default=Path("generated/forensic-5.6.1.json"))
    args = ap.parse_args()

    archive_hash = sha256(args.archive.read_bytes())
    report = {"archive": str(args.archive), "archive_sha256": archive_hash,
              "expected_debian_sha256": EXPECTED_SHA256, "entries": {},
              "archive_hash_matches_debian_snapshot": archive_hash == EXPECTED_SHA256,
              "suspicious_build_script_lines": [],
              "execution_policy": "archive members are read in memory only; no configure or embedded script is run"}
    with tarfile.open(args.archive, "r:xz") as tar:
        # Only read exact expected regular files. Never call extract/extractall.
        for suffix, expected in KNOWN.items():
            matches = [m for m in tar.getmembers() if m.isfile() and m.name.endswith("/" + suffix)]
            if len(matches) != 1:
                report["entries"][suffix] = {"matches": len(matches), "present": bool(matches)}
                continue
            data = tar.extractfile(matches[0]).read()
            report["entries"][suffix] = {"size": len(data), "sha256": sha256(data),
                                          "expected_sha256": expected,
                                          "hash_matches_known_fixture": None if expected is None else sha256(data) == expected}
            if suffix.endswith("build-to-host.m4"):
                text = data.decode("utf-8", "replace")
                report["suspicious_build_script_lines"] = [
                    {"line": i, "text": line[:300]}
                    for i, line in enumerate(text.splitlines(), 1)
                    if any(term in line for term in ("gl_am_configmake=", "gl_[$1]_config=", "#{4}"))
                ]

    if args.git_archive:
        with tarfile.open(args.git_archive, "r:*") as tar:
            git_members = [m for m in tar.getmembers() if m.isfile()]
            git_m4 = [m.name for m in git_members if m.name.endswith("/m4/build-to-host.m4")]
            git_fixtures = {}
            for suffix in ("tests/files/bad-3-corrupt_lzma2.xz", "tests/files/good-large_compressed.lzma"):
                matches = [m for m in git_members if m.name.endswith("/" + suffix)]
                if len(matches) == 1:
                    git_fixtures[suffix] = sha256(tar.extractfile(matches[0]).read())
        report["git_archive"] = str(args.git_archive)
        report["build_to_host_m4_present_in_git_archive"] = bool(git_m4)
        report["git_archive_m4_paths"] = git_m4
        report["git_fixture_sha256"] = git_fixtures
        report["release_and_git_fixture_hashes_match"] = all(
            report["entries"].get(name, {}).get("sha256") == digest
            for name, digest in git_fixtures.items())

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
