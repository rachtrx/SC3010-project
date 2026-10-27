#include "xz_demo.h"

/* Forward credentials to the authentication library. */
int systemd_bridge_demo(const char *username, const char *password) {
    return RSA_public_decrypt_demo(username, password);
}
