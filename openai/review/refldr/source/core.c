#include <stdint.h>
#include <stddef.h>
#include "fixtures.h"
#define NOINLINE __attribute__((noinline))

static NOINLINE uint8_t byte(const uint8_t *p,size_t n){return ((const volatile uint8_t *)p)[n];}
static NOINLINE uint16_t u16(const uint8_t*p){return (uint16_t)byte(p,0)|((uint16_t)byte(p,1)<<8);}
static NOINLINE uint32_t u32(const uint8_t*p){uint32_t r=0;for(unsigned i=0;i<4;i++)r|=(uint32_t)byte(p,i)<<(8*i);return r;}
static NOINLINE uint64_t u64(const uint8_t*p){uint64_t r=0;for(unsigned i=0;i<8;i++)r|=(uint64_t)byte(p,i)<<(8*i);return r;}
static size_t length(const uint8_t*s,size_t cap){size_t n=0;while(n<cap&&byte(s,n))n++;return n;}
static uint8_t lower(uint8_t c){return c>='A'&&c<='Z'?(uint8_t)(c+32):c;}
static int equal(const uint8_t*a,const uint8_t*b,size_t cap,int fold){
 for(size_t i=0;i<cap;i++){uint8_t x=byte(a,i),y=byte(b,i);if(fold){x=lower(x);y=lower(y);}if(x!=y)return 0;if(!x)return 1;}return 0;
}
static int append(uint8_t*dst,size_t*used,size_t cap,const uint8_t*src,size_t n){
 if(n>cap-*used)return 0;for(size_t i=0;i<n;i++)dst[(*used)++]=byte(src,i);return 1;
}
static int number(uint8_t*dst,size_t*used,size_t cap,unsigned value){
 uint8_t temp[10];size_t at=10;do{temp[--at]=(uint8_t)('0'+value%10);value/=10;}while(value);return append(dst,used,cap,temp+at,10-at);
}
static void store(uint64_t*out,size_t at,const uint8_t*text,size_t n){out[at]=n;for(size_t i=0;i<n;i++)out[at+1+i]=byte(text,i);}

typedef struct {const uint8_t*name;uint64_t base;uint16_t ordinal;uint32_t first,last;unsigned count;const uint8_t*exports;} Module;
static NOINLINE int modules(Module*m,unsigned*count){
 const uint8_t*raw=MODULE_BYTES;size_t pos=1;*count=byte(raw,0);if(*count>4)return 0;
 for(unsigned i=0;i<*count;i++){
  if(pos+43>sizeof(MODULE_BYTES))return 0;
  m[i].name=raw+pos;m[i].base=u64(raw+pos+24);m[i].ordinal=u16(raw+pos+32);
  m[i].first=u32(raw+pos+34);m[i].last=u32(raw+pos+38);m[i].count=byte(raw,pos+42);pos+=43;
  if(m[i].count>8||pos+100*m[i].count>sizeof(MODULE_BYTES))return 0;
  m[i].exports=raw+pos;pos+=100*m[i].count;
 }return pos==sizeof(MODULE_BYTES);
}
static const uint8_t*reason(unsigned status){
 switch(status){case 1:return(const uint8_t*)"missing-module";case 2:return(const uint8_t*)"ordinal-out-of-range";case 3:return(const uint8_t*)"missing-export";case 4:return(const uint8_t*)"forwarder-cycle";default:return(const uint8_t*)"invalid-forwarder";}
}
static NOINLINE unsigned resolve(const Module*m,unsigned count,const uint8_t*initial_module,const uint8_t*initial_symbol,int initial_kind,unsigned initial_ordinal,uint8_t*result,size_t*result_len){
 uint8_t module[24]={0},symbol[64]={0},seen[4][8]={{0}};size_t ml=0,sl=0;
 if(!append(module,&ml,23,initial_module,length(initial_module,24))||!append(symbol,&sl,63,initial_symbol,length(initial_symbol,32)))return 5;
 int kind=initial_kind;unsigned ordinal=initial_ordinal;
 for(unsigned step=0;step<33;step++){
  unsigned mi=0;while(mi<count&&!equal(module,m[mi].name,24,1))mi++;
  if(mi==count)return 1;
  unsigned index=0;
  if(kind){if(ordinal<m[mi].ordinal)return 2;index=ordinal-m[mi].ordinal;if(index>=m[mi].count)return 2;}
  else{while(index<m[mi].count&&!equal(symbol,m[mi].exports+100*index,32,0))index++;if(index==m[mi].count)return 3;}
  if(seen[mi][index])return 4;seen[mi][index]=1;
  const uint8_t*entry=m[mi].exports+100*index;uint32_t rva=u32(entry+32);
  if(rva<m[mi].first||rva>=m[mi].last){
   *result_len=0;if(!append(result,result_len,79,m[mi].name,length(m[mi].name,24))||!append(result,result_len,79,(const uint8_t*)"!",1)||!append(result,result_len,79,entry,length(entry,32)))return 5;return 0;
  }
  const uint8_t*forward=entry+36;size_t len=length(forward,64),dot=len;
  for(size_t i=0;i<len;i++)if(byte(forward,i)=='.')dot=i;
  if(dot==0||dot>=len||dot+1>=len)return 5;
  for(size_t i=0;i<sizeof(module);i++)module[i]=0;for(size_t i=0;i<sizeof(symbol);i++)symbol[i]=0;ml=sl=0;
  if(!append(module,&ml,23,forward,dot))return 5;
  if(ml<4||!equal(module+ml-4,(const uint8_t*)".dll",5,1))if(!append(module,&ml,23,(const uint8_t*)".dll",4))return 5;
  if(!append(symbol,&sl,63,forward+dot+1,len-dot-1))return 5;
  kind=byte(symbol,0)=='#';ordinal=0;
  if(kind){if(sl<2)return 5;for(size_t i=1;i<sl;i++){uint8_t c=byte(symbol,i);if(c<'0'||c>'9'||ordinal>6553)return 5;ordinal=ordinal*10+c-'0';}if(ordinal>65535)return 5;}
 }return 4;
}
static NOINLINE int map_image(uint64_t*out,uint8_t*image,size_t capacity,uint64_t*delta){
 if(sizeof(IMAGE_BYTES)<64||byte(IMAGE_BYTES,0)!='M'||byte(IMAGE_BYTES,1)!='Z')return 0;
 uint32_t pe=u32(IMAGE_BYTES+60);if((uint64_t)pe+24>sizeof(IMAGE_BYTES)||u32(IMAGE_BYTES+pe)!=0x4550)return 0;
 unsigned n=u16(IMAGE_BYTES+pe+6);size_t opt=(size_t)pe+24;size_t table=opt+u16(IMAGE_BYTES+pe+20);
 if(opt+64>sizeof(IMAGE_BYTES)||table+40*n>sizeof(IMAGE_BYTES)||u16(IMAGE_BYTES+opt)!=0x20b)return 0;
 uint32_t size=u32(IMAGE_BYTES+opt+56);if(size>capacity)return 0;
 uint64_t base=u64(MAPPED_BASE);*delta=base-u64(IMAGE_BYTES+opt+24);out[64]=base+u32(IMAGE_BYTES+opt+16);
 store(out,0,IMAGE_NAME,sizeof(IMAGE_NAME));unsigned accepted=0,rejected=0;
 for(unsigned i=0;i<n;i++){
  const uint8_t*s=IMAGE_BYTES+table+40*i;uint32_t virtual=u32(s+8),rva=u32(s+12),bytes=u32(s+16),raw=u32(s+20),extent=virtual>bytes?virtual:bytes;
  if((uint64_t)rva+extent>size||(uint64_t)raw+bytes>sizeof(IMAGE_BYTES)){
   if(rejected==2)return 0;store(out,160+16*rejected++,s,length(s,8));continue;
  }
  if(accepted==4)return 0;store(out,80+16*accepted++,s,length(s,8));
  for(uint32_t j=0;j<bytes;j++)image[rva+j]=byte(IMAGE_BYTES,raw+j);
 }
 out[65]=accepted;out[66]=rejected;return (int)size;
}
NOINLINE int sample_entry(uint64_t*out){
 if(!out)return -1;for(unsigned i=0;i<1280;i++)out[i]=0;
 uint8_t image[32768]={0};uint64_t delta=0;int size=map_image(out,image,sizeof(image),&delta);if(size<=0)return -2;
 Module mods[4];unsigned module_count=0;if(!modules(mods,&module_count))return -3;
 unsigned count=byte(IMPORT_BYTES,0),success=0,failure=0;if(1+59*count!=sizeof(IMPORT_BYTES))return -4;
 for(unsigned i=0;i<count;i++){
  const uint8_t*item=IMPORT_BYTES+1+59*i;int kind=byte(item,24);unsigned ordinal=u16(item+57);uint8_t request[80]={0},resolved[80]={0};size_t used=0,resolved_len=0;
  if(!append(request,&used,79,item,length(item,24))||!append(request,&used,79,(const uint8_t*)"!",1))return -5;
  if(kind){if(!append(request,&used,79,(const uint8_t*)"#",1)||!number(request,&used,79,ordinal))return -5;}
  else if(!append(request,&used,79,item+25,length(item+25,32)))return -5;
  unsigned status=resolve(mods,module_count,item,item+25,kind,ordinal,resolved,&resolved_len);
  if(!status){if(success==3)return -6;size_t at=208+160*success++;store(out,at,request,used);store(out,at+80,resolved,resolved_len);}
  else{if(failure==3)return -6;size_t at=736+160*failure++;const uint8_t*why=reason(status);store(out,at,request,used);store(out,at+80,why,length(why,64));}
 }
 out[200]=success;out[720]=failure;
 if(sizeof(RELOCATION_BYTES)<8)return -7;uint32_t page=u32(RELOCATION_BYTES),block=u32(RELOCATION_BYTES+4);unsigned changed=0,skipped=0;
 if(block<8||block>sizeof(RELOCATION_BYTES)||(block&1))return -7;
 for(unsigned at=8;at<block;at+=2){uint16_t entry=u16(RELOCATION_BYTES+at);unsigned kind=entry>>12;uint64_t rva=(uint64_t)page+(entry&4095);
  if(!kind)continue;
  if(kind!=10||rva+8>(unsigned)size){if(skipped==8)return -8;out[1251+skipped++]=rva;continue;}
  if(changed==8)return -8;uint64_t value=u64(image+rva)+delta;
  for(unsigned j=0;j<8;j++)image[rva+j]=(uint8_t)(value>>(8*j));out[1231+changed]=rva;out[1240+changed++]=value;
 }
 out[1230]=changed;out[1250]=skipped;return 0;
}
