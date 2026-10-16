# XZ-style release tampering teaching lab

A harmless, miniature supply-chain experiment for Linux. It uses no historical
backdoor, SSH server, authentication bypass, function interception or network service.
The injected object's only effect is printing a fixed message during library loading.

## Run in Ubuntu / WSL

```bash
sudo apt update
sudo apt install -y build-essential binutils python3
python3 run_lab.py
```

The runner creates three variants under `generated/`: source, clean release and
tampered release. All compile identical application and library C sources. The
tampered release recovers a teaching object from a compressed fixture and explicitly
adds it to the link command. This operation is visible in the lab runner, to make
the mechanism easy to inspect. The marker's source is in `teaching/marker.c`;
it is excluded from the three generated source trees, but available for audit here.
The build uses the same local compiler and options across all variants.

Application dependency chain:

```text
demo_service -> libsupport.so -> libcodec_demo.so -> marker constructor
```

No LD_PRELOAD is required. Each library uses an origin-relative runtime search path.
The marker constructor runs before main when the loader loads the modified library.

## Presentation evidence

```bash
cat generated/results.json
cat generated/tampered-release/build.log
grep fixture-marker generated/tampered-release/build/codec.map
readelf -d generated/tampered-release/build/demo_service | grep NEEDED
readelf -d generated/tampered-release/build/libsupport.so | grep NEEDED
./generated/source/build/demo_service
./generated/clean-release/build/demo_service
./generated/tampered-release/build/demo_service
```

Expected: every variant prints `checksum=1236`. Only the tampered variant prints
the lab marker, includes the marker string, and links the fixture-derived object.
The runner checks these properties and source hashes, direct dependencies, equality
of the two clean library hashes, and inequality of clean versus tampered hashes.
These are controlled local comparisons, not a claim of cross-machine reproducibility.

Generated artifacts are overwritten on reruns; keep your own work outside `generated/`.

## Historical mapping and limitations

The real XZ 5.6.0/5.6.1 incident involved release-only build-script changes and
hidden material in repository test fixtures. On affected distributions, patched
sshd loaded liblzma indirectly through libsystemd. The real runtime interception
used IFUNC-related mechanisms, not this simple constructor. This lab does not
reproduce the cryptographic trigger, RSA interception, remote execution or stealth.
The clean Git versus historical release comparison is a separate investigation;
no actual malicious tarball is bundled or downloaded by this starter.

Primary reference: https://www.openwall.com/lists/oss-security/2024/03/29/4

For your slides: show the three-build results, linker-map evidence, dependency
chain, and actual runtime output. A hash mismatch alone does not prove maliciousness;
repeatable builds can also repeat malicious inputs. Here the object provenance and
observed marker establish exactly what changed.
