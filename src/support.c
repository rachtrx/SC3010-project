#include "auth_demo.h"

/* main() stores the optional trigger paths here. Only the hook reads them;
   the original password checker never receives or uses them. */
static struct signed_trigger trigger;

void support_set_trigger(const char *token_path, const char *signature_path) {
    trigger.token_path = token_path;
    trigger.signature_path = signature_path;
}

const struct signed_trigger *support_get_trigger(void) {
    return &trigger;
}

/* This intermediate dependency is the only library called directly by main.
   Its authentication entry is supplied by the replaceable libauth_demo.so. */
int support_authenticate(const char *username, const char *password) {
    return authenticate_password(username, password);
}
