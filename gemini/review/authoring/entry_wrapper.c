#include <stddef.h>
#include <stdint.h>

#ifndef OUTPUT_WORDS
#error OUTPUT_WORDS must be supplied by the private build configuration
#endif

extern int sample_entry(uint64_t *out);
volatile uint64_t observation_sink;

void rust_eh_personality(void) {}

int main(void) {
    uint64_t words[OUTPUT_WORDS] = {0};
    int status = sample_entry(words);
    uint64_t value = (uint32_t)status;
    for (size_t i = 0; i < OUTPUT_WORDS; ++i) {
        value += words[i];
    }
    observation_sink = value;
    return 0;
}
