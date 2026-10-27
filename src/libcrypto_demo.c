#include <string.h>
#include "xz_demo.h"

/* Toy stand-in for the OpenSSL function name: this checks credentials, not RSA.
   The original remains in its own library, libcrypto_demo.so. */
int RSA_public_decrypt_demo(const char *username, const char *password) {
    return strcmp(username, "student") == 0 &&
           strcmp(password, "sc3010") == 0;
}
