#!/usr/bin/env python3
"""Show three pieces of build evidence. Does not build or run the demo."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    # Read-only inspection: no build commands or executable runs.
    for variant in ("clean", "tampered"):
        for name in ("auth_demo", "libsupport.so", "libauth_demo.so", "libauth_core.so", "build/auth.map"):
            if not (ROOT / variant / name).is_file():
                raise SystemExit(f"Build first: make -C {variant} all")

    for variant in ("clean", "tampered"):
        tree = ROOT / variant
        library = tree / "libauth_demo.so"
        print(f"\n{variant}:")

        # A hash identifies the library's exact bytes; it does not prove safety.
        digest = hashlib.sha256(library.read_bytes()).hexdigest()
        print(f"  Library SHA256: {digest}")

        # Show the linker's actual input record for the injected object.
        linker_map = tree / "build/auth.map"
        entries = [line.strip() for line in linker_map.read_text().splitlines()
                   if line.startswith("LOAD ") and "auth_hook.o" in line]
        print("  Linker map: " + ("; ".join(entries) if entries else "no injected hook object"))

        # Read recorded dependencies without executing the program or libraries.
        print("  Dependencies (from readelf):")
        for name in ("auth_demo", "libsupport.so", library.name, "libauth_core.so"):
            output = subprocess.check_output(["readelf", "-d", str(tree / name)], text=True)
            needed = [line.split("[", 1)[1].split("]", 1)[0]
                      for line in output.splitlines() if "(NEEDED)" in line]
            print(f"    {name} -> {', '.join(needed) or '(none)'}")
        print(f"  Full linker map: {linker_map}")



if __name__ == "__main__":
    main()
