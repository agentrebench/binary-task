"""Independent PE-shaped data parser and inert template splice model."""
import struct
def solve(f):
    p=bytes.fromhex(f['payload_hex']);argument=bytes.fromhex(f['parameter_hex'])
    if p[:2]!=b'MZ':raise ValueError('magic')
    pe=struct.unpack_from('<I',p,0x3c)[0]
    if pe+44>len(p) or p[pe:pe+4]!=b'PE\0\0':raise ValueError('header')
    machine=struct.unpack_from('<H',p,pe+4)[0];magic=struct.unpack_from('<H',p,pe+24)[0];entry=struct.unpack_from('<I',p,pe+40)[0]
    if (machine,magic)==(0x8664,0x20b):bits=64
    elif (machine,magic)==(0x14c,0x10b):bits=32
    else:raise ValueError('architecture')
    loader=bytearray.fromhex(f['loader'+str(bits)+'_hex']);n=len(loader);argoff=n+len(p);entryoff=n+entry
    if entry>=len(p):raise ValueError('entry outside data')
    offsets={tag:loader.index(struct.pack('<I',tag)) for tag in (0xfacecafe,0xdeadc0de,0xfeedf00d,0xaabbccdd)}
    values={0xfacecafe:n,0xdeadc0de:len(p),0xfeedf00d:entryoff-(offsets[0xfeedf00d]+4),0xaabbccdd:argoff-(offsets[0xaabbccdd]+4)}
    for tag,v in values.items():struct.pack_into('<I',loader,offsets[tag],v)
    output=bytes(loader)+p+argument
    return {'schema_version':1,'answers':{
      'selection':{'pe_machine':machine,'optional_header_magic':magic,'loader_bits':bits},
      'layout':{'loader_size':n,'payload_size':len(p),'parameter_offset':argoff,'total_size':len(output),'entry_offset':entryoff},
      'patches':{'payload_offset':struct.unpack_from('<I',output,offsets[0xfacecafe])[0],'payload_size':struct.unpack_from('<I',output,offsets[0xdeadc0de])[0],'entry_relative_displacement':struct.unpack_from('<I',output,offsets[0xfeedf00d])[0],'parameter_relative_displacement':struct.unpack_from('<I',output,offsets[0xaabbccdd])[0]},
      'parameter':{'ascii':output[argoff:].split(b'\0')[0].decode()}}}
