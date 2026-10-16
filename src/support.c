unsigned codec_checksum(const char *text);
unsigned support_checksum(const char *text) {
    return codec_checksum(text);
}
