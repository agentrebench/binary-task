#include <stdint.h>
#include <stddef.h>
#include "fixture_data.inc"

static uint16_t u16(const volatile unsigned char *p) {return uint16_t(p[0]) | (uint16_t(p[1])<<8);}
static uint32_t u32(const volatile unsigned char *p) {return uint32_t(u16(p)) | (uint32_t(u16(p+2))<<16);}
static uint64_t u64(const volatile unsigned char *p) {return uint64_t(u32(p)) | (uint64_t(u32(p+4))<<32);}
static __attribute__((noinline)) uint32_t hash_name(const volatile unsigned char *p) {
    uint32_t c=0xffffffffu;
    for(unsigned i=0;i<32 && p[i];i++) {
        c^=p[i];for(unsigned k=0;k<8;k++) c=(c>>1)^(0xedb88320u & (0u-(c&1u)));
    }
    return ~c;
}
static __attribute__((noinline)) bool accepts(const volatile unsigned char *descriptor,const volatile unsigned char *request) {
    const uint16_t process=u16(request),native=u16(request+2);
    const uint64_t context=u64(request+4);
    const unsigned alignment=descriptor[42],width=descriptor[43];
    if(process!=u16(descriptor+32) || native!=u16(descriptor+34) || process==native) return false;
    if(width!=8 || !alignment || (alignment&(alignment-1)) || !context || (context&(alignment-1))) return false;
    return (u32(request+12)&1u)!=0;
}
extern "C" int sample_entry(uint64_t *out) {
    for(unsigned i=0;i<64;i++) out[i]=0;
    const uint32_t wanted=u32(selected_api_hash);
    unsigned row=0;
    for(;row<sizeof(platform_descriptors)/44;row++) if(hash_name(platform_descriptors+row*44)==wanted) break;
    if(row==sizeof(platform_descriptors)/44) return 1;
    const volatile unsigned char *d=platform_descriptors+row*44;
    unsigned n=0;while(n<32 && d[n]) {out[n+1]=d[n];n++;}out[0]=n;
    out[40]=u16(d+32);out[41]=u16(d+34);out[42]=u16(d+36);out[43]=u16(d+38);
    out[44]=d[40];out[45]=d[41];out[46]=d[43];
    for(unsigned i=0;i<sizeof(context_requests)/16;i++) {
        const volatile unsigned char *r=context_requests+i*16;
        const bool accepted=accepts(d,r);out[50+i]=accepted;out[56+i]=accepted?u64(r+4):0;
    }
    return 0;
}
