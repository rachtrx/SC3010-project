# XZ Utils supply-chain teaching lab

Two builds show normal authentication and a tampered library containing an
injected object, a GNU IFUNC resolver, and a signature-checking replacement.
This is a local toy simulation, not the historical backdoor or an SSH server.

## Prepare and build

```bash
sudo apt install -y build-essential binutils python3 openssl libssl-dev xz-utils curl
python3 run_lab.py
make -C clean all
make -C tampered all
python3 inspect_lab.py   # optional hashes, linker inputs, dependencies
```

There are two independent Makefiles: `clean/Makefile` and `tampered/Makefile`.
Both build the same filenames and dependency chain inside their own directory:

```text
auth_demo -> libsupport.so -> libauth_demo.so -> libauth_core.so
```

No copying libraries or loader environment variables is necessary. Each executable
uses `$ORIGIN` to find the libraries beside itself. Both executables are built
from the same application and normal password-checking code.

`run_lab.py` only prepares inputs; it does not invoke Make or run scenarios.
Running it again refreshes the copied sources, fixtures, and build outputs while
preserving both Makefiles. The editable source of truth is the top-level `src/`.
The copied `clean/src/` and `tampered/src/` files can be inspected separately.

## Run manually

From the project root:

```bash
# Clean: normal credentials work; wrong credentials fail.
./clean/auth_demo student sc3010
# Authenticated!
./clean/auth_demo student wrong
# Authentication denied.

# Tampered: no trigger still means normal password checking.
./tampered/auth_demo student wrong
# Authentication denied.

# Tampered: valid signed trigger overrides the wrong password.
./tampered/auth_demo student wrong --token tampered/trigger.bin --signature tampered/trigger.sig
# Authenticated!

# Tampered: modified token with the original signature is rejected.
./tampered/auth_demo student wrong --token tampered/tampered-trigger.bin --signature tampered/trigger.sig
# Authentication denied.

# The clean library does not accept even the valid trigger.
./clean/auth_demo student wrong --token tampered/trigger.bin --signature tampered/trigger.sig
# Authentication denied.
```

Token paths are relative to your current directory. Results come from the actual
C authentication call, not a scripted test summary. Exit status is 0 for acceptance,
1 for denial, and 2 for invalid arguments.

## Files and their roles

All editable C files live together in `src/`:

| File | Role |
|---|---|
| `auth_demo.c` | Host program: parse arguments and call the support library |
| `auth_core.c` | Original strong authentication function in `libauth_core.so`; toy stand-in for the RSA-related path |
| `support.c` | Intermediate library; stores optional hook inputs separately and forwards username/password |
| `auth_hook.c` | Replacement handler plus IFUNC resolver, packaged into the injected object |
| `auth_demo.h` | Shared function declarations |

The clean source tree contains three C files (`auth_demo.c`, `auth_core.c`,
`support.c`) and the header. The tampered
source tree contains those same files plus `auth_hook.c`. Only `tampered/` has the
signed tokens, public-key files, and `tests/files/` compressed fixtures. Its copy
of `auth_hook.c` is available for review, but its Makefile never compiles that
source: it must recover the precompiled object from the fixtures instead.
Both Makefiles compile `auth_core.c` once into `libauth_core.so`. It exports the
original strong `authenticate_password()` function. The clean `libauth_demo.so`
is a bridge that depends on this original library, without defining a replacement.
The tampered `libauth_demo.so` contains the recovered hook and depends on the same
original library. Two strong definitions can coexist in different shared libraries;
they are not linked together into a single library. There are no weak symbols,
conditional compilation, double compilation, or `auth_library.c`.

| Other file | Role |
|---|---|
| `run_lab.py` | Prepare both source trees, signed tokens, and the two compressed fixtures |
| `clean/Makefile` | Build normal executable, support/bridge libraries, and original `libauth_core.so` |
| `tampered/Makefile` | Build the same outputs, recovering the hook object from fixtures |
| `inspect_lab.py` | Read-only hashes, hook linker-map entry, and dependency chain for both builds |
| `audit_release.py` | Optional static inspection of a supplied historical archive |

## Object injection during Make

Preparation generates a throwaway Ed25519 keypair and signs a fixed token.
It embeds the public key into a temporary compiled `auth_hook.o`, compresses that
object into the LZMA fixture, and deletes the temporary object and private key.
It independently compresses an extraction script into the XZ fixture. Both
fixtures already exist before Make starts.

```text
Preparation (Python):
  src/auth_hook.c -> temporary auth_hook.o -> tampered/tests/files/stage2-object.lzma
  extraction script                       -> tampered/tests/files/stage1-payload.xz

Tampered build (Make):
  stage1-payload.xz -> build/extract-hook.sh
                                | reads separate stage2-object.lzma
                                v
                         build/auth_hook.o
                                | contains resolver + replacement handler
                                v
                         libauth_demo.so
```

The script inside the XZ file is:

```sh
#!/bin/sh
set -eu
xz --format=lzma --decompress --stdout tests/files/stage2-object.lzma
```

Make uses no Python. Its two extraction commands are `xz -dc ... > ...` and
`sh build/extract-hook.sh > build/auth_hook.o`. The clean Makefile has no extraction
rules. Each linker writes `build/auth.map`; only the tampered map includes
`LOAD build/auth_hook.o`. Hash differences show different library bytes, not
maliciousness on their own.

To repeat building and extraction without preparing tokens again:

```bash
make -C clean clean
make -C tampered clean
make -C clean all
make -C tampered all
```

## Exact runtime call order

### Tampered build

1. You run `./tampered/auth_demo ...`. The loader loads `libsupport.so`,
   `libauth_demo.so`, and the original `libauth_core.so`.
2. While resolving support's `authenticate_password` reference, the loader finds
   the IFUNC in the tampered `libauth_demo.so` and calls `resolve_authentication()`.
   It returns the address of `hooked_authentication`. This selects the replacement;
   it does **not** authenticate anyone, check signatures, or delete the original.
3. After relocation, the constructor `save_original_authentication()` runs.
   `dlsym(RTLD_NEXT, "authenticate_password")` finds the untouched original in
   `libauth_core.so` and saves its address in `original_authentication`.
4. Library initialization finishes, and the executable's `main()` starts.
   The hook and resolver do not call `main()` themselves.
5. `main()` parses the username/password and optional token/signature paths.
6. `main()` calls `support_set_trigger(token_path, signature_path)` to store the
   optional paths separately in support's `signed_trigger` struct. Only the hook
   reads this data; it is not a pre-verified flag or an authentication result.
7. `main()` calls `support_authenticate(username, password)`.
8. Support calls `authenticate_password(username, password)`. The function address
   selected in step 2 sends this call to `hooked_authentication`.
9. The hook calls `support_get_trigger()` and verifies the token and signature.
   A valid trigger returns success. Otherwise it calls
   `original_authentication(username, password)`, using the saved address from
   step 3. The original checker receives **only username and password** and
   performs the ordinary password check; it never sees token/signature paths.
10. The result returns through support to `main()`, which prints `Authenticated!`
    or `Authentication denied.` and exits.

```text
Startup: resolver selects hook -> constructor saves original -> main starts

main: store optional trigger paths in support (separate configuration)
main -> support_authenticate(user, password)
     -> hooked_authentication(user, password)
          | reads paths from support and verifies signature
          | valid: return success
          | absent/invalid: original_authentication(user, password)
          |                       -> original password checker
     <- result through support
main prints result
```

### Clean build

There is no IFUNC or hook constructor. The loader resolves `authenticate_password`
to the ordinary function in `libauth_core.so`. `main()` parses arguments and
stores the optional paths in support, but nothing reads them. The call sequence is
`main -> support_authenticate(username, password) -> authenticate_password(username,
password) -> result -> main prints result`. Only the password check decides access.

## IFUNC and the historical analogy

`auth_core.c` is the toy stand-in for the original RSA-related authentication
function. It compares a username/password, not actual RSA, and lives in the
separate `libauth_core.so`. That library is unchanged between builds.

The clean bridge `libauth_demo.so` has no replacement; calls from support resolve
to the original strong function in its `libauth_core.so` dependency. The tampered
`libauth_demo.so` exports `authenticate_password` as an IFUNC, which is found before
the original in that dependency. Its resolver selects `hooked_authentication`.
Because support is linked with `-z now`, selection happens before `main()`.
The resolver only returns an address and performs no file I/O or crypto.

After relocation and before `main()`, the tampered library's constructor saves the
original function's address:

```c
original_authentication = (authentication_fn)dlsym(RTLD_NEXT, "authenticate_password");
```

`RTLD_NEXT` searches after the current library, skipping its own IFUNC and finding
the original function in `libauth_core.so`. When authentication is called, the
replacement verifies the signature. If the trigger is absent or invalid, it calls
that saved address directly:

```c
return original_authentication(username, password);
```

It does not call `authenticate_password` by name, which would resolve back to the
replacement and recurse. If saving the original fails, the hook denies access.

```text
Clean:     main -> support -> original authenticate_password in libauth_core.so
Tampered:  main -> support -> replacement in libauth_demo.so
                                  valid signature: accept
                                  otherwise: saved pointer -> libauth_core.so
```

The historical backdoor similarly preserved the original OpenSSL function address
and used that pointer for fallback. See the original-pointer assignment and
fallback call in [Binarly's reverse engineering](https://github.com/binarly-io/binary-risk-intelligence/blob/master/xz-backdoor/readme.md).
Our version models this without weak symbols or a separately named fallback.

This remains a simplified local demonstration: the real attack used unrelated
liblzma checksum IFUNC startup code to interfere with lookup of OpenSSL's
`RSA_public_decrypt`. Here the tampered auth library directly supplies the IFUNC
for our toy function, and `dlsym` saves the untouched original from its dependency.
We do not modify the loader's lookup structures. Local Ed25519 token files replace
the historical Ed448 protocol. There is no network listener or command payload.

The indirect dependency analogy is host -> support -> compromised library; the
extra `libauth_core.so` represents the independent library containing the original
cryptographic function. Identical C sources are not a historical requirement.

To inspect the symbols without executing either program:

```bash
readelf -Ws clean/libauth_core.so | grep authenticate_password      # original FUNC
readelf -Ws tampered/libauth_demo.so | grep authenticate_password   # replacement IFUNC
```

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

In our archived copy, `m4/build-to-host.m4` exists in the release archive but not in
the Git tag archive. The two suspicious test fixtures exist in both, with matching
SHA256 hashes. Debian records SHA256
`f334777310ca3ae9ba07206d78ed286a655aa3f44eec27854f740c26b2cd2ed0` for the release
archive. This reproduces the first important forensic finding: the build trigger was
in release packaging, while the opaque fixture data was already in Git.

Primary sources: [Andres Freund's disclosure](https://www.openwall.com/lists/oss-security/2024/03/29/4),
[Debian's 5.6.1 source-package announcement](https://tracker.debian.org/news/1515323/accepted-xz-utils-561-1-source-into-unstable/),
and [XZ Utils incident notes](https://tukaani.org/xz-backdoor/).
