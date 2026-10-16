#include <stdio.h>
/* A fixed message only: no commands, credentials, sockets, or hooks. */
__attribute__((constructor))
static void release_marker(void) {
    puts("[lab marker] release-only object executed inside demo_service");
}
