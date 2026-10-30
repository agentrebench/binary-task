#include <stdint.h>
#include <stddef.h>
#include "data.h"

struct Text { uint8_t b[96]; unsigned n; };
struct Config {
    uint8_t flags,ip[4],path[32],body[64];
    unsigned port,interval,path_n,body_n;
    uint32_t module_hash,api_hash;
    bool integrity;
};
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint32_t checksum(const uint8_t *p,unsigned n,bool lower=false) {
    uint32_t value=0xffffffffu;
    for(unsigned i=0;i<n;++i) {
        uint8_t c=p[i];if(lower && c>='A'&&c<='Z')c=(uint8_t)(c+32);
        value^=c;
        for(unsigned bit=0;bit<8;++bit)value=(value>>1)^((0u-(value&1u))&0xedb88320u);
    }
    return ~value;
}
static bool decompress(const uint8_t *src,unsigned size,uint8_t *dst,unsigned &written) {
    uint16_t prefix[4096];uint8_t suffix[4096],stack[4096];
    unsigned next=258,width=9,pos=0,bits=0,old=0;
    uint32_t reservoir=0;uint8_t first=0;bool prior=false,cleared=false;
    written=0;
    for(;;) {
        while(bits<width) {
            if(pos==size)return false;
            reservoir|=(uint32_t)src[pos++]<<bits;bits+=8;
        }
        unsigned code=reservoir&((1u<<width)-1);reservoir>>=width;bits-=width;
        if(code==256){next=258;width=9;prior=false;cleared=true;continue;}
        if(!cleared)return false;
        if(code==257)return true;
        unsigned incoming=code,count=0;
        if(code==next) {
            if(!prior)return false;
            stack[count++]=first;code=old;
        } else if(code>next)return false;
        while(code>=258) {
            if(code>=next||count>=sizeof(stack))return false;
            stack[count++]=suffix[code];code=prefix[code];
        }
        if(code>255||count>=sizeof(stack))return false;
        first=(uint8_t)code;stack[count++]=first;
        if(written+count>256)return false;
        while(count)dst[written++]=stack[--count];
        if(prior&&next<4096) {
            prefix[next]=(uint16_t)old;suffix[next]=first;++next;
            if(next==(1u<<width)&&width<12)++width;
        }
        old=incoming;prior=true;
    }
}
static bool parse(const uint8_t *p,unsigned n,Config &c) {
    if(n<26||p[0]!='L'||p[1]!='C'||p[2]!=1)return false;
    c.flags=p[3];c.port=(unsigned)p[4]|((unsigned)p[5]<<8);c.interval=(unsigned)p[6]|((unsigned)p[7]<<8);
    for(unsigned i=0;i<4;++i)c.ip[i]=p[8+i];
    unsigned at=12;c.path_n=p[at++];
    if(c.path_n>sizeof(c.path)||at+c.path_n+1>n)return false;
    for(unsigned i=0;i<c.path_n;++i)c.path[i]=p[at++];
    c.body_n=p[at++];
    if(c.body_n>sizeof(c.body)||at+c.body_n+12!=n)return false;
    for(unsigned i=0;i<c.body_n;++i)c.body[i]=p[at++];
    c.module_hash=le32(p+at);c.api_hash=le32(p+at+4);at+=8;
    c.integrity=(checksum(p,at)==le32(p+at));
    return true;
}
static bool push(Text &s,uint8_t c){if(s.n==sizeof(s.b))return false;s.b[s.n++]=c;return true;}
static bool literal(Text &s,const char *p){while(*p)if(!push(s,(uint8_t)*p++))return false;return true;}
static bool decimal(Text &s,unsigned v){uint8_t a[10];unsigned n=0;do{a[n++]=(uint8_t)('0'+v%10);v/=10;}while(v);while(n)if(!push(s,a[--n]))return false;return true;}
static bool url(Text &s,const Config &c) {
    if(!literal(s,(c.flags&2)?"https://":"http://"))return false;
    for(unsigned i=0;i<4;++i){if(i&&!push(s,'.'))return false;if(!decimal(s,c.ip[i]))return false;}
    if(!push(s,':')||!decimal(s,c.port))return false;
    for(unsigned i=0;i<c.path_n;++i)if(!push(s,c.path[i]))return false;
    return true;
}
static bool resolve(const Config &c,Text &module,Text &name) {
    unsigned pos=0;
    while(pos<sizeof(fixture_exports)) {
        uint8_t mod[32],api[64];unsigned mn=fixture_exports[pos++];
        if(mn>sizeof(mod)||pos+mn+1>sizeof(fixture_exports))return false;
        for(unsigned i=0;i<mn;++i)mod[i]=fixture_exports[pos++];
        unsigned an=fixture_exports[pos++];
        if(an>sizeof(api)||pos+an>sizeof(fixture_exports))return false;
        for(unsigned i=0;i<an;++i)api[i]=fixture_exports[pos++];
        if(checksum(mod,mn,true)==c.module_hash&&checksum(api,an)==c.api_hash) {
            module.n=name.n=0;
            for(unsigned i=0;i<mn;++i)if(!push(module,(mod[i]>='A'&&mod[i]<='Z')?(uint8_t)(mod[i]+32):mod[i]))return false;
            for(unsigned i=0;i<an;++i)if(!push(name,api[i]))return false;
            return true;
        }
    }
    return false;
}

extern "C" int sample_entry(uint64_t *out) {
    for(unsigned i=0;i<384;++i)out[i]=0;
    unsigned pos=0;Config active{},candidate{};Text module{},name{};
    bool have_active=false,accepted=false;
    while(pos<sizeof(fixture_container)) {
        if(pos+6>sizeof(fixture_container))return 1;
        uint8_t head[6];for(unsigned i=0;i<6;++i)head[i]=fixture_container[pos++];
        uint32_t state=le32(head);unsigned n=(unsigned)head[4]|((unsigned)head[5]<<8);
        if(n>512||pos+n>sizeof(fixture_container))return 2;
        uint8_t packed[512],plain[256];
        for(unsigned i=0;i<n;++i) {
            state^=state<<13;state^=state>>17;state^=state<<5;
            packed[i]=fixture_container[pos++]^(uint8_t)state;
        }
        unsigned decoded=0;
        if(!decompress(packed,n,plain,decoded)||!parse(plain,decoded,candidate))return 3;
        Text proposed_module{},proposed_name{};
        bool found=resolve(candidate,proposed_module,proposed_name);
        accepted=candidate.integrity&&(candidate.flags&1)&&found;
        if(accepted) {active=candidate;module=proposed_module;name=proposed_name;have_active=true;}
    }
    if(!have_active)return 4;
    Text destination{},alternate{};
    if(!url(destination,active)||!url(alternate,candidate))return 5;
    if(module.n>32||name.n>64)return 6;
    out[0]=destination.n;out[1]=active.interval;out[2]=active.body_n;
    out[3]=module.n;out[4]=name.n;out[5]=alternate.n;out[6]=accepted;
    for(unsigned i=0;i<destination.n;++i)out[32+i]=destination.b[i];
    for(unsigned i=0;i<active.body_n;++i)out[128+i]=active.body[i];
    for(unsigned i=0;i<module.n;++i)out[192+i]=module.b[i];
    for(unsigned i=0;i<name.n;++i)out[224+i]=name.b[i];
    for(unsigned i=0;i<alternate.n;++i)out[288+i]=alternate.b[i];
    return 0;
}
