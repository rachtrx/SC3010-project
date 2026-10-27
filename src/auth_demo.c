#include <stdio.h>
#include <string.h>
#include "auth_demo.h"

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s USER PASSWORD [--token FILE --signature FILE]\n", argv[0]);
        return 2;
    }
    const char *token_path = NULL;
    const char *signature_path = NULL;
    for (int i = 3; i < argc; i += 2) {
        if (i + 1 >= argc) {
            fputs("Missing option value.\n", stderr);
            return 2;
        }
        if (strcmp(argv[i], "--token") == 0 && !token_path)
            token_path = argv[i + 1];
        else if (strcmp(argv[i], "--signature") == 0 && !signature_path)
            signature_path = argv[i + 1];
        else {
            fprintf(stderr, "Unknown or repeated option: %s\n", argv[i]);
            return 2;
        }
    }
    if ((token_path == NULL) != (signature_path == NULL)) {
        fputs("Provide both --token and --signature.\n", stderr);
        return 2;
    }
    support_set_trigger(token_path, signature_path);
    int accepted = support_authenticate(argv[1], argv[2]);
    puts(accepted ? "Authenticated!" : "Authentication denied.");
    return accepted ? 0 : 1;
}
