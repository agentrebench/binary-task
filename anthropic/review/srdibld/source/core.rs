#![no_std]
use core::panic::PanicInfo;
#[panic_handler]
fn panic(_info:&PanicInfo)->! {loop {core::hint::spin_loop();}}
include!("fixture_data.rs");

#[inline(never)]
fn bytes<const N:usize>(input:&[u8;N])->[u8;N] {
    let mut result=[0u8;N];
    for i in 0..N {result[i]=unsafe{core::ptr::read_volatile(input.as_ptr().add(i))};}
    result
}
fn read16(b:&[u8],p:usize)->u16 {u16::from_le_bytes([b[p],b[p+1]])}
fn read32(b:&[u8],p:usize)->u32 {u32::from_le_bytes([b[p],b[p+1],b[p+2],b[p+3]])}
fn write32(b:&mut[u8],p:usize,v:u32) {b[p..p+4].copy_from_slice(&v.to_le_bytes());}

#[no_mangle]
pub unsafe extern "C" fn sample_entry(out:*mut u64)->i32 {
    for i in 0..64 {out.add(i).write(0);}
    let payload=bytes(&PAYLOAD_DATA);let argument=bytes(&PARAMETER_DATA);
    if payload.len()<64 || &payload[..2]!=b"MZ" {return 1;}
    let pe=read32(&payload,60) as usize;
    if pe>payload.len().saturating_sub(44) || &payload[pe..pe+4]!=b"PE\0\0" {return 2;}
    let machine=read16(&payload,pe+4);let magic=read16(&payload,pe+24);
    let entry=read32(&payload,pe+40) as usize;
    if entry>=payload.len() {return 3;}
    let mut buffer=[0u8;256];
    let (n,bits)=if machine==0x8664 && magic==0x20b {
        let loader=bytes(&LOADER_DATA64);buffer[..loader.len()].copy_from_slice(&loader);(loader.len(),64u64)
    } else if machine==0x14c && magic==0x10b {
        let loader=bytes(&LOADER_DATA32);buffer[..loader.len()].copy_from_slice(&loader);(loader.len(),32u64)
    } else {return 4;};
    let argument_offset=n+payload.len();let total=argument_offset+argument.len();let entry_offset=n+entry;
    if total>buffer.len() {return 5;}
    let mut locations=[usize::MAX;4];
    for p in 0..n.saturating_sub(3) {
        let which=match read32(&buffer,p) {0xfacecafe=>0,0xdeadc0de=>1,0xfeedf00d=>2,0xaabbccdd=>3,_=>continue};
        if locations[which]!=usize::MAX {return 6;}locations[which]=p;
    }
    if locations.iter().any(|&p|p==usize::MAX) {return 7;}
    if entry_offset<locations[2]+4 || argument_offset<locations[3]+4 {return 8;}
    write32(&mut buffer,locations[0],n as u32);
    write32(&mut buffer,locations[1],payload.len() as u32);
    write32(&mut buffer,locations[2],(entry_offset-locations[2]-4) as u32);
    write32(&mut buffer,locations[3],(argument_offset-locations[3]-4) as u32);
    buffer[n..argument_offset].copy_from_slice(&payload);
    buffer[argument_offset..total].copy_from_slice(&argument);
    let values=[machine as u64,magic as u64,bits,n as u64,payload.len() as u64,argument_offset as u64,total as u64,entry_offset as u64];
    for (i,v) in values.iter().enumerate() {out.add(i).write(*v);}
    for i in 0..4 {out.add(8+i).write(read32(&buffer,locations[i]) as u64);}
    let mut length=0;
    while argument_offset+length<total && buffer[argument_offset+length]!=0 {
        if length>=51 {return 9;}
        out.add(13+length).write(buffer[argument_offset+length] as u64);length+=1;
    }
    out.add(12).write(length as u64);
    0
}
