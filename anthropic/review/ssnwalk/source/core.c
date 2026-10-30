#include <stdint.h>
#include <stddef.h>
#include "fixture_data.inc"

static uint32_t little32(const volatile unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static __attribute__((noinline)) uint32_t hash_name(const volatile unsigned char *s) {
    uint32_t c=0xffffffffu;
    for (unsigned i=0;i<32 && s[i];i++) {
        c^=s[i];
        for(unsigned b=0;b<8;b++) c=(c>>1)^(0xedb88320u & (0u-(c&1u)));
    }
    return ~c;
}
static __attribute__((noinline)) int read_token(unsigned slot, unsigned *token) {
    if(slot>=sizeof(stub_pages)/32) return 0;
    const volatile unsigned char *s=stub_pages+slot*32;
    if(s[0]!=0x4c || s[1]!=0x8b || s[2]!=0xd1 || s[3]!=0xb8) return 0;
    if(s[8]!=0x0f || s[9]!=0x05 || s[10]!=0xc3) return 0;
    *token=(unsigned)s[4] | ((unsigned)s[5]<<8);
    return 1;
}
static void name_words(uint64_t *out, const volatile unsigned char *s) {
    unsigned n=0;
    while(n<32 && s[n]) {out[n+1]=s[n];n++;}
    out[0]=n;
}
int sample_entry(uint64_t *out) {
    for(unsigned i=0;i<352;i++) out[i]=0;
    name_words(out,module_bytes);
    for(unsigned q=0;q<sizeof(query_hashes)/4;q++) {
        uint32_t wanted=little32(query_hashes+q*4);
        unsigned row=0;
        for(;row<sizeof(export_directory)/36;row++) if(hash_name(export_directory+row*36)==wanted) break;
        if(row==sizeof(export_directory)/36) return 1;
        unsigned slot=little32(export_directory+row*36+32),witness=slot,token=0,distance=0,up=0;
        int found=read_token(slot,&token);
        for(unsigned d=1;d<=2 && !found;d++) {
            unsigned value;
            if(read_token(slot+d,&value) && value>=d) {token=value-d;witness=slot+d;distance=d;up=1;found=1;}
        }
        for(unsigned d=1;d<=2 && !found;d++) {
            unsigned value;
            if(slot>=d && read_token(slot-d,&value)) {token=value+d;witness=slot-d;distance=d;up=0;found=1;}
        }
        if(!found) return 2;
        unsigned witness_row=0;
        for(;witness_row<sizeof(export_directory)/36;witness_row++) if(little32(export_directory+witness_row*36+32)==witness) break;
        if(witness_row==sizeof(export_directory)/36) return 3;
        uint64_t *r=out+64+q*96;
        name_words(r,export_directory+row*36);
        r[33]=token;r[34]=distance!=0;r[35]=up;r[36]=distance*32;
        name_words(r+37,export_directory+witness_row*36);
    }
    return 0;
}
