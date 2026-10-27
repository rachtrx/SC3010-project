#!/usr/bin/env python3
"""Prepare signed tokens, compressed hook fixtures, and a build tree. Run Make next."""
import json
import lzma
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
TAMPERED = ROOT / "tampered"
PAYLOAD = b"XZ-LAB:fixed-auth-control-flow-demo:v1"


def run(args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    # Refresh each example's generated files, preserving its own Makefile.
    for variant in ("clean", "tampered"):
        tree = ROOT / variant
        for name in ("src", "tests", "build"):
            if (tree / name).exists():
                shutil.rmtree(tree / name)
        for name in ("auth_demo", "libsupport.so", "libauth_demo.so", "libauth_core.so"):
            (tree / name).unlink(missing_ok=True)
        (tree / "src").mkdir()
        for name in ("auth_core.c", "auth_demo.c", "auth_demo.h", "support.c"):
            shutil.copyfile(ROOT / "src" / name, tree / "src" / name)
    # The extra hook source and all trigger/key files belong only to tampered/.
    shutil.copyfile(ROOT / "src/auth_hook.c", TAMPERED / "src/auth_hook.c")
    # Generate the signing key and embed its public key in the hook at build time.
    private_key, public_key = TAMPERED / "demo-private.pem", TAMPERED / "demo-public.pem"
    payload, signature = TAMPERED / "trigger.bin", TAMPERED / "trigger.sig"
    payload.write_bytes(PAYLOAD)
    run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", private_key])
    run(["openssl", "pkey", "-in", private_key, "-pubout", "-out", public_key])
    (TAMPERED / "trusted_key.h").write_text(
        "static const char TRUSTED_PUBLIC_KEY[] = " + json.dumps(public_key.read_text()) + ";\n")
    run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", private_key,
         "-in", payload, "-out", signature])
    private_key.unlink()

    # Compile the hook ONCE during fixture preparation, then package its bytes.
    # The temporary object disappears; Make must recover it from the LZMA file.
    fixtures = TAMPERED / "tests/files"
    fixtures.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as temp:
        hook_object = Path(temp) / "auth_hook.o"
        run(["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-c",
             TAMPERED / "src/auth_hook.c", "-I", TAMPERED / "src", "-I", TAMPERED,
             "-o", hook_object])
        (fixtures / "stage2-object.lzma").write_bytes(
            lzma.compress(hook_object.read_bytes(), format=lzma.FORMAT_ALONE))
    script = b"#!/bin/sh\nset -eu\nxz --format=lzma --decompress --stdout tests/files/stage2-object.lzma\n"
    (fixtures / "stage1-payload.xz").write_bytes(lzma.compress(script))

    # Prepare an invalid token for the manual rejection example too.
    (TAMPERED / "tampered-trigger.bin").write_bytes(PAYLOAD + b"-changed")
    print("Prepared clean/ and tampered/. Next: make -C clean all; make -C tampered all")


if __name__ == "__main__":
    main()
