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
all: auth_demo
# Remove incomplete outputs after a failed recipe.
.DELETE_ON_ERROR:

build:
	mkdir -p build

# Compile the original strong authenticate_password function ONCE.
build/auth_core.o: src/auth_core.c src/auth_demo.h | build
	$(CC) $(CFLAGS) -c $< -o $@

# Keep the original implementation in a separate, unchanged library.
# The hook can save its actual address without conflicting definitions at link time.
libauth_core.so: build/auth_core.o
	$(CC) -shared -Wl,-soname,libauth_core.so -o $@ $^

# The intermediate library forwards the host's call to the replaceable library.
build/support.o: src/support.c src/auth_demo.h | build
	$(CC) $(CFLAGS) -c $< -o $@

# This clean bridge carries no replacement code: its dependency supplies the
# ordinary authenticate_password. --no-as-needed keeps this dependency even
# though this bridge defines no user functions itself. $ORIGIN finds it beside us.
# -Map writes the library's linker inputs; -soname records its runtime name.
libauth_demo.so: libauth_core.so
	$(CC) -shared -Wl,-soname,libauth_demo.so -Wl,-Map,build/auth.map -o $@ -L. -Wl,--no-as-needed -lauth_core -Wl,-rpath,'$$ORIGIN'

# Record the indirect dependency: libsupport needs libauth_demo.so.
# -z now resolves its authenticate_password call before main(), including the IFUNC.
libsupport.so: build/support.o libauth_demo.so
	$(CC) -shared -Wl,-soname,libsupport.so -o $@ build/support.o -L. -Wl,--no-as-needed -lauth_demo -Wl,-rpath,'$$ORIGIN' -Wl,-z,now

# Build ONE executable. $ORIGIN finds the active library beside it at runtime.
# -z now resolves the IFUNC before main(), rather than delaying until first call.
# -L. searches here at link time; -lsupport selects libsupport.so.
# -rpath-link helps the linker find support's indirect library dependency.
# $$ passes a literal $ through Make; single quotes protect it from the shell.
# The loader later interprets $ORIGIN as the executable's own directory.
auth_demo: src/auth_demo.c src/auth_demo.h libsupport.so
	$(CC) -O2 -Wall -Wextra -Werror -o $@ $< -L. -lsupport -Wl,-rpath,'$$ORIGIN' -Wl,-rpath-link,. -Wl,-z,now

# Preserve both compressed fixtures so Make can repeat extraction from scratch.
clean:
	rm -rf build auth_demo libsupport.so libauth_demo.so libauth_core.so
