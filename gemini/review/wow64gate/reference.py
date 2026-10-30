"""Independent descriptor and request decoder, with no platform API use."""
import struct,zlib
def solve(f):
    b=bytes.fromhex(f['descriptors_hex']);want=int.from_bytes(bytes.fromhex(f['request_hash_hex']),'little')
    d=next(b[p:p+44] for p in range(0,len(b),44) if zlib.crc32(b[p:p+32].split(b'\0')[0])==want)
    name=d[:32].split(b'\0')[0].decode();process,native,enter,leave=struct.unpack_from('<HHHH',d,32)
    alignment,width=d[42:44]
    accepted=[];effective=[]
    for proc,nat,context,flags in struct.iter_unpack('<HHQI',bytes.fromhex(f['requests_hex'])):
        valid=proc==process and nat==native and proc!=nat and width==8 and context!=0 and context%alignment==0 and bool(flags&1)
        accepted.append(valid);effective.append(context if valid else 0)
    return {'schema_version':1,'answers':{
      'platform':{'api_name':name,'required_process_machine':process,'required_native_machine':native},
      'transition_data':{'entry_selector':enter,'return_selector':leave,'marker_hex':d[40:42].hex(),'context_width_bytes':width},
      'requests':{'accepted':accepted,'effective_targets':effective}}}
