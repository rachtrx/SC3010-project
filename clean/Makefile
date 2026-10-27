# Clean build: run `python3 run_lab.py`, then `make -C clean`.
# This Makefile builds libraries in this directory; no Python runs during Make.
# Quick syntax guide:
#   target: prerequisites    = what to produce, and which files it needs first.
#   A TAB-indented line      = the shell command that produces it.
#   $(NAME)                 = insert the value of a Make variable.
#   $@                      = this rule's output filename (target).
#   $<                      = its first prerequisite.
#   $^                      = all its prerequisites.
#   | build                 = create build/ first; ignore its timestamp changes.
# Make skips targets that already exist and are newer than their prerequisites.
# .c is source text; .o is compiled code; .so is a runtime shared library.
#
# := assigns a variable. gcc compiles C and invokes the linker when needed.
CC := gcc
# -O2 optimizes; -fPIC supports shared libraries; -Wall/-Wextra enable warnings;
# -Werror makes warnings stop the build. -c below compiles without linking.
CFLAGS := -O2 -fPIC -Wall -Wextra -Werror

# all and clean name actions, rather than real files. Plain make selects all.
.PHONY: all clean
all: sshd_demo
# Remove incomplete outputs after a failed recipe.
.DELETE_ON_ERROR:

build:
	mkdir -p build

# Compile the original strong RSA_public_decrypt_demo function ONCE.
build/crypto_demo.o: src/libcrypto_demo.c src/xz_demo.h | build
	$(CC) $(CFLAGS) -c $< -o $@

# Keep the original implementation in a separate, unchanged library.
# The hook can save its actual address without conflicting definitions at link time.
libcrypto_demo.so: build/crypto_demo.o
	$(CC) -shared -Wl,-soname,libcrypto_demo.so -o $@ $^

# The intermediate library forwards the host's call to the replaceable library.
build/systemd_demo.o: src/libsystemd_demo.c src/xz_demo.h | build
	$(CC) $(CFLAGS) -c $< -o $@

# Clean bridge: no replacement code. Its dependency supplies the original.
# --no-as-needed retains the dependency even though the bridge has no functions.
liblzma_demo.so: libcrypto_demo.so
	$(CC) -shared -Wl,-soname,liblzma_demo.so -Wl,-Map,build/lzma.map -o $@ -L. -Wl,--no-as-needed -lcrypto_demo -Wl,-rpath,'$$ORIGIN'

# Record the indirect dependency: libsupport needs liblzma_demo.so.
# -z now resolves the authentication entry before main(), including its IFUNC.
libsystemd_demo.so: build/systemd_demo.o liblzma_demo.so
	$(CC) -shared -Wl,-soname,libsystemd_demo.so -o $@ build/systemd_demo.o -L. -Wl,--no-as-needed -llzma_demo -Wl,-rpath,'$$ORIGIN' -Wl,-z,now

# Build the same application in each tree. $ORIGIN finds libraries beside it.
# -L. searches here at link time; -lsystemd_demo selects libsystemd_demo.so.
# -rpath-link helps the linker find support's indirect dependencies.
# $$ passes a literal $ through Make; quotes protect it from shell expansion.
sshd_demo: src/sshd_demo.c src/xz_demo.h libsystemd_demo.so
	$(CC) -O2 -Wall -Wextra -Werror -o $@ $< -L. -lsystemd_demo -Wl,-rpath,'$$ORIGIN' -Wl,-rpath-link,. -Wl,-z,now

# Preserve both compressed fixtures so Make can repeat extraction from scratch.
clean:
	rm -rf build sshd_demo libsystemd_demo.so liblzma_demo.so libcrypto_demo.so
