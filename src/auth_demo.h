#ifndef AUTH_DEMO_H
#define AUTH_DEMO_H

/* Optional hook inputs are configured separately from the password-check API. */
struct signed_trigger {
    const char *token_path;
    const char *signature_path;
};
void support_set_trigger(const char *token_path, const char *signature_path);
const struct signed_trigger *support_get_trigger(void);

int authenticate_password(const char *username, const char *password);
int support_authenticate(const char *username, const char *password);

#endif
