# XZ Utils supply-chain teaching lab

This is the simple constructor + IFUNC version of the local authentication demo.
Python prepares two compressed fixtures; Make recovers a compiled hook and links
it into the tampered library. At startup, IFUNC selects the replacement and a
constructor saves the original function address for fallback. There is no ELF
scanning, GOT patching, codec probe, or memory-permission manipulation.

The names follow the real components with `_demo` suffixes, so they cannot be
mistaken for system libraries or collide with OpenSSL's real RSA function. The
symbol `RSA_public_decrypt_demo` still takes a username/password and checks strings;
it does not have OpenSSL's RSA API or perform RSA decryption.

This is a toy Linux/glibc demonstration, not SSH or the historical backdoor.
All commands start from the project root unless otherwise stated.

## Prepare and build

```bash
sudo apt update
sudo apt install -y build-essential binutils python3 openssl libssl-dev xz-utils curl
python3 run_lab.py
make -C clean all
make -C tampered all
python3 inspect_lab.py
```

`libssl-dev` supplies the OpenSSL C headers and linker files. `curl` is only for
the optional archive audit below. IFUNC and `RTLD_NEXT` require a compatible GNU
ELF/glibc environment; this is not a portable Windows/macOS program.

`run_lab.py` only prepares the inputs. It compiles a temporary object to package
its bytes, but does not run Make or authentication scenarios. The independent
`clean/Makefile` and `tampered/Makefile` each build:

```text
sshd_demo -> libsystemd_demo.so -> liblzma_demo.so -> libcrypto_demo.so
```

Both trees use the same output names and application source. `$ORIGIN` finds the
libraries beside each executable. No copying libraries, `LD_PRELOAD`, or
`LD_LIBRARY_PATH` is needed. Rerunning preparation refreshes copied sources,
fixtures, tokens, and outputs while preserving the two Makefiles. Edit top-level
`src/` files, then prepare again to copy your changes into each tree.

## Run manually

The application only accepts `USER PASSWORD`. It has no trigger flags, trigger
setters, or signature-checking code.

```bash
# Normal login works in both builds.
./clean/sshd_demo student sc3010
# Authenticated!
./tampered/sshd_demo student sc3010
# Authenticated!

# Ordinary wrong passwords fail in both builds.
./clean/sshd_demo student wrong
# Authentication denied.
./tampered/sshd_demo student wrong
# Authentication denied.

# Only the tampered hook recognizes the signed input.
./tampered/sshd_demo student "$(cat tampered/trigger-password.txt)"
# Authenticated!
./clean/sshd_demo student "$(cat tampered/trigger-password.txt)"
# Authentication denied.

# Altered signed data does not activate the override.
./tampered/sshd_demo student "$(cat tampered/tampered-trigger-password.txt)"
# Authentication denied.
```

`$(cat FILE)` supplies the text as a single quoted password argument. Only the
injected hook recognizes its `XZLAB1:TOKEN_HEX:SIGNATURE_HEX` format. The normal
host passes the input unchanged. This envelope is a teaching substitute for
trigger data in existing authentication inputs, not the real SSH trigger format.
An ordinary or invalid special input falls back to normal password checking;
ordinary correct passwords still work. Exit status is 0 for acceptance, 1 for
denial, and 2 for invalid argument count.

## Files and build inputs

All editable C code lives in `src/`:

| File | Role |
|---|---|
| `sshd_demo.c` | `main()`: accepts credentials, calls support, prints the actual result |
| `libsystemd_demo.c` | Forwards credentials to `RSA_public_decrypt_demo()` |
| `libcrypto_demo.c` | Original strong `RSA_public_decrypt_demo()` in `libcrypto_demo.so` |
| `liblzma_hook_demo.c` | IFUNC resolver, constructor saving the original, signature checker, replacement |
| `xz_demo.h` | Ordinary authentication/support declarations only |

The clean tree receives the three common C files and header. The tampered tree
receives those plus the hook source for inspection. Only tampered has tokens,
encoded credential examples, key files, and `tests/files/` fixtures. The tampered
Makefile never compiles the hook source: its object must be recovered from those
fixtures. Both Makefiles compile `libcrypto_demo.c` once. No weak symbols, conditional
compilation, double compilation, or extra wrapper C file is used.

The original function stays unchanged in `libcrypto_demo.so`. The clean
`liblzma_demo.so` is a dependency-only bridge: lookup continues to the original.
The tampered `liblzma_demo.so` contains the IFUNC of the same name, found first,
and depends on the original library. Separate shared libraries can define the
same strong name; the original is not overwritten or deleted.

## Fixture extraction during Make

Preparation generates a throwaway Ed25519 keypair and signs a fixed token. The
public key is compiled into a temporary hook object. Python compresses its bytes
into the LZMA fixture, then deletes the temporary object and private key. The XZ
fixture independently contains the extraction script. Both exist before Make.

```text
Python:
  src/liblzma_hook_demo.c -> temporary lzma_hook_demo.o -> tampered/tests/files/stage2-object.lzma
  extraction script                       -> tampered/tests/files/stage1-payload.xz

Tampered Make:
  stage1-payload.xz -> build/extract-hook.sh
                                | reads separate stage2-object.lzma
                                v
                         build/lzma_hook_demo.o -> liblzma_demo.so
```

The XZ contains this script, not the LZMA file:

```sh
#!/bin/sh
set -eu
xz --format=lzma --decompress --stdout tests/files/stage2-object.lzma
```

Make runs `xz -dc` to extract the script, then `sh` to run it and recover the
object. No Python runs during Make. Signature verification happens inside the
hook, not in a host-approved flag. Changing the public-key PEM after preparation
does not change the key embedded in the object.

To rebuild from existing fixtures without generating new keys:

```bash
make -C clean clean
make -C tampered clean
make -C clean all
make -C tampered all
```

## Exact runtime order

### Tampered

1. You start `tampered/sshd_demo`. Its libraries load through the dependency chain.
2. Support's `RSA_public_decrypt_demo` reference finds the IFUNC in `liblzma_demo.so`.
   Because support uses `-z now`, the loader calls `resolve_RSA_public_decrypt_demo()`
   before `main()`. It returns the address of `hooked_RSA_public_decrypt_demo`. This only
   selects a function; it does not check passwords or signatures yet.
3. After relocation, the constructor `save_original_RSA_public_decrypt_demo()` runs.
   `dlsym(RTLD_NEXT, "RSA_public_decrypt_demo")` searches after this library and
   finds the original in `libcrypto_demo.so`. Its address is saved in
   `original_RSA_public_decrypt`. No memory tables are patched.
4. Initialization finishes and normal startup enters `main()`.
5. `main()` passes username/password to `systemd_bridge_demo()`.
6. Support calls `RSA_public_decrypt_demo()`. The address selected by IFUNC sends
   this call to `hooked_RSA_public_decrypt_demo`.
7. Only the hook parses a signed credential envelope and verifies its signature.
   Valid signed data returns success. Ordinary or invalid inputs call the saved
   `original_RSA_public_decrypt(username, password)` pointer, forwarding both arguments
   unchanged. If the original lookup failed, the hook denies access.
8. The result returns through support to `main()`, which prints it.

```text
Startup: IFUNC selects replacement -> constructor saves original -> main

main -> support -> IFUNC-selected replacement
                     valid signed input: accept
                     otherwise: saved pointer -> original password checker
     <- result through support
main prints result
```

The saved pointer avoids recursively looking up the intercepted name. The
original function still exists in its own library. The resolver and constructor
do not call `main()` themselves.

### Clean

There is no hook IFUNC or hook constructor. Lookup reaches the ordinary function
in `libcrypto_demo.so`: `main -> support -> original password checker -> result`.
No normal application code knows that signed credentials or a hook exist.

## Inspect evidence

`inspect_lab.py` reads library hashes, the hook object's `LOAD` entry in
`build/lzma.map`, and dependencies using `readelf`. It does not build or run the
programs. Different hashes show different bytes; the extracted linker input and
observed behavior explain the difference.

```bash
readelf -Ws clean/libcrypto_demo.so | grep RSA_public_decrypt_demo     # original FUNC
readelf -Ws tampered/liblzma_demo.so | grep RSA_public_decrypt_demo  # replacement IFUNC
```

## Historical attack: end-to-end technical flow

The sequence below is a technical overview, not a claim that this project
reproduces every stage of CVE-2024-3094.

1. **Compromised releases were distributed.** XZ Utils 5.6.0 and 5.6.1 release
   tarballs contained the backdoor. Release archives and repository-generated
   source archives were not equivalent inputs. [XZ maintainer's incident notes](https://tukaani.org/xz-backdoor/)
2. **Build machinery activated hidden material.** A modified release-only
   `m4/build-to-host.m4` activated processing of compressed test fixtures already
   present in the repository. [Maintainer's review](https://tukaani.org/xz-backdoor/review.html)
3. **Staged extraction recovered injected code.** Build scripts processed
   `bad-3-corrupt_lzma2.xz`, then separate `good-large_compressed.lzma`, and
   incorporated recovered object code into liblzma. Activation checked selected
   platform, toolchain, and packaging conditions. [Original disclosure](https://www.openwall.com/lists/oss-security/2024/03/29/4)
4. **The affected library reached another program.** In some distribution builds,
   sshd's systemd integration indirectly loaded liblzma. This was library loading,
   not an RSA authentication call forwarded by libsystemd. [Original disclosure](https://www.openwall.com/lists/oss-security/2024/03/29/4)
5. **Startup code established interception.** Modified checksum IFUNC resolvers
   ran during startup. Injected code interfered with symbol resolution so calls
   intended for OpenSSL's `RSA_public_decrypt` reached a replacement carried in
   liblzma. The RSA function was not itself the checksum IFUNC. [Original disclosure](https://www.openwall.com/lists/oss-security/2024/03/29/4)
6. **Attacker input reached the replacement.** Specially constructed RSA-key data
   in the authentication path carried an encrypted, signed trigger. The hook
   checked an Ed448 signature against its embedded trust material, including
   host-related binding. [Binarly's reverse engineering](https://github.com/binarly-io/binary-risk-intelligence/blob/master/xz-backdoor/readme.md)
7. **Verified requests enabled malicious behavior.** Supported operations included
   command execution. This was more than accepting an arbitrary wrong password.
   The private signing key controlled access to the authenticated trigger path.
   [Binarly's reverse engineering](https://github.com/binarly-io/binary-risk-intelligence/blob/master/xz-backdoor/readme.md)
8. **Normal processing could continue.** The hook preserved the original function
   address and used it for fallback. It could call that address without looking up
   the intercepted name again. [Binarly's reverse engineering](https://github.com/binarly-io/binary-risk-intelligence/blob/master/xz-backdoor/readme.md)

The compromise was not perfectly invisible: slow SSH logins and diagnostic errors
helped expose it. [Andres Freund's disclosure](https://www.openwall.com/lists/oss-security/2024/03/29/4)

### The crucial distinction: loading versus calling

```text
Historical loading relationships (simplified):
sshd
├── OpenSSL/libcrypto                  original RSA function
└── libsystemd
    └── liblzma                        injected startup code + replacement

Normal RSA call:
sshd -> original OpenSSL RSA function

After interception:
sshd -> replacement inside liblzma
           ordinary/unrecognized input -> saved original OpenSSL function
           verified trigger            -> authenticated malicious operation
```

**Neither the original RSA call nor the redirected replacement call needed to
pass through libsystemd.** Libsystemd was relevant because its dependency caused
liblzma to be loaded into the process. Once loaded, the injected code established
interception separately.

## How this project models those stages

The project demonstrates an actual working chain for the selected mechanisms:
fixture extraction produces a real object, that object becomes library code,
the GNU loader selects its replacement, and that replacement verifies signed
input before deciding whether to override or call the original. These are
executed behaviors, not just messages describing an attack.

| Stage / purpose | What this project actually does | Where to see it |
|---|---|---|
| Package executable code as apparent test data | Compile a hook object and compress it into a separate LZMA fixture | `run_lab.py` |
| Use one fixture to process another | XZ contains a script naming the separate LZMA file; both exist before Make | `tampered/tests/files/` |
| Inject during the build | Make extracts the script, runs it, recovers `lzma_hook_demo.o`, and links it into the child library | `tampered/Makefile`, `build/lzma.map` |
| Carry replacement code in a dependency | The tampered `liblzma_demo.so` contains the recovered replacement and resolver | `src/liblzma_hook_demo.c` |
| Select behavior before the host starts | Real GNU IFUNC resolution occurs before `main()` because support uses `-z now` | `resolve_RSA_public_decrypt_demo()` |
| Retain access to the normal implementation | A constructor obtains the separate original with `dlsym(RTLD_NEXT, ...)` and saves its address | `save_original_RSA_public_decrypt_demo()` |
| Let existing authentication input reach the hook | The host accepts only username/password; only the injected object understands the signed envelope | `src/sshd_demo.c`, `verified_trigger()` |
| Gate the override cryptographically | Verify a signature using the embedded public key inside the hook, not in the host | `verified_trigger()` |
| Preserve ordinary logins | Call the saved original address for ordinary or invalid special input | `hooked_RSA_public_decrypt_demo()` |
| Make the result reviewable | Compare library hashes, linker inputs, dependencies, and actual login outcomes | `inspect_lab.py` and the manual examples |

The original checker remains unchanged in `libcrypto_demo.so`. Clean and tampered
builds use the same application source and library filenames. This isolates the
extra behavior to the dependency being compared. That is a deliberate experimental
control, not a claim that all historical C sources or build inputs were identical.

## Limitations: what the current simple model does not reproduce

### 1. Authentication still passes through the teaching bridge

The current code deliberately uses this forwarding chain:

```text
sshd_demo -> systemd_bridge_demo -> RSA_public_decrypt_demo
                                       clean: original implementation
                                    tampered: IFUNC-selected replacement
                                                  -> saved original for fallback
```

`systemd_bridge_demo()` is an invented teaching function, **not a real systemd
API**. Unlike the historical attack, both normal and replacement authentication
calls in this project pass through that bridge. Merely loading a dependency does
not intercept an unrelated function call. The bridge and symbol lookup order
make the simplified replacement work.

The former, longer version used local call-address redirection and could reach
both original and replacement without this bridge. That code was removed in
favor of the requested simple constructor + IFUNC version. **The current project
does not patch GOT/PLT slots or independently hijack the host's direct RSA call.**

### 2. The IFUNC and initialization sequence are simplified

Our toy RSA-named entry is itself the IFUNC. Its resolver directly selects the
replacement; a later constructor saves the original with `RTLD_NEXT`. We do not
reproduce an unrelated checksum resolver setting up interception of an OpenSSL
function, manipulate loader lookup structures, or implement the real hook-install
sequence. Names and genuine IFUNC usage do not make those mechanisms equivalent.

### 3. The function names are analogies, not real implementations

`RSA_public_decrypt_demo(username, password)` compares strings; it does not have
OpenSSL's RSA function signature or perform RSA cryptography. `sshd_demo` is a
short-lived local executable, not OpenSSH, and `liblzma_demo.so` does not implement
a compression library. The `_demo` suffix avoids collisions with real components.
The hook uses the real OpenSSL library only to check its demonstration signature.

### 4. Trigger encoding, trust setup, and effect are reduced

We use a fixed token with Ed25519 and a readable hex envelope in the password
argument. There is no real SSH exchange, RSA-key carrier, encrypted trigger
protocol, host-key binding, or Ed448 implementation. A fresh throwaway key is
created for each preparation. The test input's private key is deleted afterward;
the public key stays embedded in the object. These are reproducible lab artifacts,
not the historical attacker's keys or payloads.

A valid trigger simply makes the toy check return success. It does not execute
commands, establish a remote session, reproduce privilege behavior, or demonstrate
the full impact of the actual authenticated command-execution path.

### 5. Packaging and targeting are transparent teaching substitutes

Python openly prepares the fixtures and token examples; there is no compromised
release producer, modified Autotools `configure`/M4 chain, social engineering,
release archive generation, obfuscation, or reproduction of the historical
platform/toolchain/distribution/debugger gates. Both fixtures are supplied only to
the tampered tree to make the comparison easy. The historical fixture files were
also present in the repository; the separate audit below examines that difference.

The source of the injected object is available for reading. The generated Make
build does recover its compiled bytes from fixtures rather than silently compiling
the visible hook source. This demonstrates the build mechanism, not stealth.

### 6. Scope of the evidence and platform

Hashes establish byte differences, linker maps show included inputs, and dependency
records show library requirements. They do not prove successful historical
exploitation or identify maliciousness on their own. Manual runtime comparisons
establish only the behavior exercised by this toy program; they are not a complete
analysis of OpenSSH or XZ. The local code needs a compatible GNU ELF/glibc IFUNC
and `RTLD_NEXT` environment and OpenSSL development files. It does not install
compromised libraries, modify system files, or validate a real affected deployment.

The optional archive audit below is separate. Only its report uses `generated/`;
the runnable builds use `clean/` and `tampered/`.

## Static examination of the actual 5.6.1 release archive

The original release assets were removed from the upstream download page. Debian's
snapshot preserves the 5.6.1 upstream source archive; its SHA1 and SHA256 are recorded
in Debian's signed package announcement. Download that exact archive and the
GitHub-generated tag archive:

```bash
mkdir -p /tmp/xz-release-audit
curl -fL https://snapshot.debian.org/file/a77dd4689db35cfaa814d1c3a919720bd41f5623 \
  -o /tmp/xz-release-audit/xz-utils_5.6.1.orig.tar.xz
curl -fL https://codeload.github.com/tukaani-project/xz/tar.gz/refs/tags/v5.6.1 \
  -o /tmp/xz-release-audit/xz-v5.6.1-git-source.tar.gz
python3 audit_release.py /tmp/xz-release-audit/xz-utils_5.6.1.orig.tar.xz \
  --git-archive /tmp/xz-release-audit/xz-v5.6.1-git-source.tar.gz
```

The auditor reads expected regular files directly from the archive in memory. It
does not extract archive paths, run `configure`, evaluate embedded shell, or execute
any object file. Evidence is written to `generated/forensic-5.6.1.json`.

### Findings from our static audit

The saved [forensic report](generated/forensic-5.6.1.json) records:

| Check | Finding |
|---|---|
| Release archive identity | SHA256 matches the value published in Debian's package announcement |
| `m4/build-to-host.m4` | Present in the release archive (4,399 bytes); absent from the Git-tag archive |
| `tests/files/bad-3-corrupt_lzma2.xz` | Present in both archives, with identical SHA256 hashes |
| `tests/files/good-large_compressed.lzma` | Present in both archives, with identical SHA256 hashes |
| Selected build-script lines | Flags lines 63, 65, and 86; these include an extraction/evaluation expression and a marker search |

**Presentation summary:** We reproduced a known release-versus-repository
discrepancy: the release archive contains additional build machinery, while the
suspicious compressed fixture bytes were already present in both sources. This
supports the distinction between release packaging and repository contents.

The release archive's SHA256 is
`f334777310ca3ae9ba07206d78ed286a655aa3f44eec27854f740c26b2cd2ed0`.
This is a targeted static comparison, not a complete archive diff or an independent
discovery of the backdoor. A release-only file or hash match alone does not prove
maliciousness. The auditor does not verify PGP signatures, execute the extracted
build logic, or demonstrate historical exploitation. Its default output path is
relative to the working directory; running from this project root writes
`/home/rachm/xz-lab/generated/forensic-5.6.1.json`.

Primary sources: [Andres Freund's disclosure](https://www.openwall.com/lists/oss-security/2024/03/29/4),
[Debian's 5.6.1 source-package announcement](https://tracker.debian.org/news/1515323/accepted-xz-utils-561-1-source-into-unstable/),
and [XZ Utils incident notes](https://tukaani.org/xz-backdoor/).
