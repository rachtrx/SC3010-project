CC := gcc
OUT ?= build
EXTRA_OBJECTS ?=
CFLAGS := -O2 -fPIC -Wall -Wextra -Werror

.PHONY: all clean
all: $(OUT)/demo_service

$(OUT):
	mkdir -p $(OUT)

$(OUT)/codec.o: src/codec.c | $(OUT)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT)/support.o: src/support.c | $(OUT)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT)/libcodec_demo.so: $(OUT)/codec.o $(EXTRA_OBJECTS)
	$(CC) -shared -Wl,-soname,libcodec_demo.so -Wl,-Map,$(OUT)/codec.map -o $@ $^

$(OUT)/libsupport.so: $(OUT)/support.o $(OUT)/libcodec_demo.so
	$(CC) -shared -Wl,-soname,libsupport.so -Wl,-rpath,'$$ORIGIN' -o $@ $(OUT)/support.o -L$(OUT) -lcodec_demo

$(OUT)/demo_service: src/service.c $(OUT)/libsupport.so
	$(CC) -O2 -Wall -Wextra -Werror -Wl,-rpath,'$$ORIGIN' -Wl,-rpath-link,$(OUT) -o $@ $< -L$(OUT) -lsupport

clean:
	rm -rf build
