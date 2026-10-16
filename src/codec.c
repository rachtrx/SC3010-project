unsigned codec_checksum(const char *text) {
    unsigned result = 0;
    while (*text) result += (unsigned char)*text++;
    return result;
}
