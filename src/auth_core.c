#include <string.h>
#include "auth_demo.h"

/* The original implementation stays in its own library, libauth_core.so.
   It remains intact when calls are intercepted. No weak symbol is needed. */
int authenticate_password(const char *username, const char *password) {
    return strcmp(username, "student") == 0 &&
           strcmp(password, "sc3010") == 0;
}
