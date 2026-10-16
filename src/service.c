#include <stdio.h>
unsigned support_checksum(const char *text);
int main(void) {
    unsigned value = support_checksum("security-lab");
    printf("checksum=%u\n", value);
    return value == 1236 ? 0 : 1;
}
