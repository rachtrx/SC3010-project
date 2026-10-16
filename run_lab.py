#!/usr/bin/env python3
"""Controlled educational analogue. Never downloads or executes historical malware."""
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "generated"
MARKER = "[lab marker] release-only object executed inside demo_service"


def run(args, cwd=ROOT):
    result = subprocess.run([str(a) for a in args], cwd=cwd,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}{result.stderr}")
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for tool in ("gcc", "make", "readelf", "strings"):
        if not shutil.which(tool):
            raise SystemExit(f"Missing {tool}; run this inside Ubuntu after installing build-essential binutils")
    WORK.mkdir(exist_ok=True)
    marker_object = WORK / "teaching-marker.o"
    run(["gcc", "-O2", "-fPIC", "-c", ROOT / "teaching/marker.c", "-o", marker_object])
    # Ordinary compression, deliberately transparent rather than real obfuscation.
    fixture = lzma.compress(marker_object.read_bytes())
    results = []
    for name in ("source", "clean-release", "tampered-release"):
        tree = WORK / name
        tree.mkdir(exist_ok=True)
        shutil.copytree(ROOT / "src", tree / "src", dirs_exist_ok=True)
        shutil.copyfile(ROOT / "Makefile", tree / "Makefile")
        # Remove only the known build directory inside this generated variant.
        build = tree / "build"
        if build.exists():
            shutil.rmtree(build)
        args = ["make", "all"]
        if name != "source":
            (tree / "release-metadata.txt").write_text("educational release packaging\n")
        if name == "tampered-release":
            fixtures = tree / "tests/files"
            fixtures.mkdir(parents=True, exist_ok=True)
            (fixtures / "marker-fixture.xz").write_bytes(fixture)
            # Models a release-only build step; does not run any extracted script.
            build.mkdir()
            recovered = build / "fixture-marker.o"
            recovered.write_bytes(lzma.decompress((fixtures / "marker-fixture.xz").read_bytes()))
            assert recovered.read_bytes() == marker_object.read_bytes()
            args.append("EXTRA_OBJECTS=build/fixture-marker.o")
        build_log = run(args, cwd=tree)
        (tree / "build.log").write_text(build_log)
        output = run([build / "demo_service"])
        (tree / "runtime.txt").write_text(output)
        deps = {}
        for file in ("demo_service", "libsupport.so", "libcodec_demo.so"):
            deps[file] = run(["readelf", "-d", build / file])
        (tree / "dependencies.txt").write_text(json.dumps(deps, indent=2))
        strings = run(["strings", build / "libcodec_demo.so"])
        row = {
            "variant": name,
            "source_sha256": {p.name: digest(p) for p in sorted((tree / "src").glob("*.c"))},
            "library_sha256": digest(build / "libcodec_demo.so"),
            "marker_in_library": MARKER in strings,
            "marker_executed": MARKER in output,
            "checksum_passed": "checksum=1236" in output,
            "extra_object_in_map": "fixture-marker.o" in (build / "codec.map").read_text(),
        }
        expected_marker = name == "tampered-release"
        assert row["checksum_passed"]
        assert row["marker_in_library"] == expected_marker
        assert row["marker_executed"] == expected_marker
        assert row["extra_object_in_map"] == expected_marker
        assert "libsupport.so" in deps["demo_service"]
        assert "libcodec_demo.so" not in deps["demo_service"]
        assert "libcodec_demo.so" in deps["libsupport.so"]
        results.append(row)
        print(f"{name}: checksum PASS; marker={row['marker_executed']}; extra object={row['extra_object_in_map']}")
    assert all(r["source_sha256"] == results[0]["source_sha256"] for r in results)
    assert results[0]["library_sha256"] == results[1]["library_sha256"]
    assert results[1]["library_sha256"] != results[2]["library_sha256"]
    (WORK / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print("All checks passed. Evidence saved under generated/.")


if __name__ == "__main__":
    main()
