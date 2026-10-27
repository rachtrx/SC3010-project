#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include "trusted_key.h"
#include "auth_demo.h"

/* This file is compiled and compressed during preparation. The tampered Makefile
   recovers that object from a fixture rather than compiling this source.
   Trust the public key compiled into this library, never a caller-selected key.
   Command-line arguments supply only the untrusted token and signature paths. */
static int verified_trigger(const char *token_path, const char *signature_path) {
    const unsigned char expected[] = "XZ-LAB:fixed-auth-control-flow-demo:v1";
    unsigned char token[256], signature[64];
    if (!token_path || !signature_path) return 0;

    FILE *file = fopen(token_path, "rb");
    if (!file) return 0;
    size_t token_size = fread(token, 1, sizeof(token), file);
    int token_ok = !ferror(file) && feof(file);
    fclose(file);
    if (!token_ok || token_size != sizeof(expected) - 1 ||
        memcmp(token, expected, token_size) != 0) return 0;

    file = fopen(signature_path, "rb");
    if (!file) return 0;
    size_t signature_size = fread(signature, 1, sizeof(signature), file);
    int signature_ok = signature_size == sizeof(signature) &&
                       fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!signature_ok) return 0;

    BIO *bio = BIO_new_mem_buf(TRUSTED_PUBLIC_KEY, -1);
    if (!bio) return 0;
    EVP_PKEY *key = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
    BIO_free(bio);
    EVP_MD_CTX *context = EVP_MD_CTX_new();
    int valid = key && context &&
        EVP_DigestVerifyInit(context, NULL, NULL, NULL, key) == 1 &&
        EVP_DigestVerify(context, signature, signature_size, token, token_size) == 1;
    EVP_MD_CTX_free(context);
    EVP_PKEY_free(key);
    return valid;
}

/* Store the original address independently of the intercepted symbol name. */
typedef int (*authentication_fn)(const char *, const char *);
static authentication_fn original_authentication;

/* Constructors run after relocation but before main(). dlsym is safe here,
   unlike inside an early IFUNC resolver. RTLD_NEXT skips this library's IFUNC
   and finds the real function in the required libauth_core.so. */
__attribute__((constructor))
static void save_original_authentication(void) {
    original_authentication = (authentication_fn)dlsym(RTLD_NEXT, "authenticate_password");
}

static int hooked_authentication(const char *username, const char *password) {
    if (!original_authentication) return 0;
    const struct signed_trigger *trigger = support_get_trigger();
    if (verified_trigger(trigger->token_path, trigger->signature_path)) {
        return 1;
    }
    /* Call the saved address, NOT authenticate_password by name (recursion). */
    return original_authentication(username, password);
}

/* GNU IFUNC: the loader calls this resolver to obtain the address to use for
   authenticate_password. The executable is linked with -z now, so this happens
   before main(). Do not read files or run OpenSSL here: startup is still early.
   Signature verification occurs later, when the selected function is called.
   This demonstrates real IFUNC selection, not the historical loader tampering. */
static authentication_fn resolve_authentication(void) {
    return hooked_authentication;
}

int authenticate_password(const char *, const char *)
    __attribute__((ifunc("resolve_authentication")));
