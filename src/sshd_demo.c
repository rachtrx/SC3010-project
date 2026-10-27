#include <stdio.h>
#include "xz_demo.h"

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s USER PASSWORD\n", argv[0]);
        return 2;
    }
    int accepted = systemd_bridge_demo(argv[1], argv[2]);
    puts(accepted ? "Authenticated!" : "Authentication denied.");
    return accepted ? 0 : 1;
}
