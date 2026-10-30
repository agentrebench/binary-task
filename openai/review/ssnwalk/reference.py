"""Independent byte-fixture model; zlib CRC is independent of C bit iteration."""
import struct,zlib
def solve(f):
    module=bytes.fromhex(f['module_hex']).split(b'\0')[0].decode()
    raw=bytes.fromhex(f['exports_hex']);stubs=bytes.fromhex(f['stubs_hex']);q=bytes.fromhex(f['queries_hex'])
    exports=[(raw[p:p+32].split(b'\0')[0].decode(),struct.unpack_from('<I',raw,p+32)[0]) for p in range(0,len(raw),36)]
    byslot={slot:name for name,slot in exports}
    def token(slot):
        if not 0<=slot<len(stubs)//32:return None
        b=stubs[slot*32:(slot+1)*32]
        if b[:4]!=bytes.fromhex('4c8bd1b8') or b[8:11]!=bytes.fromhex('0f05c3'):return None
        return int.from_bytes(b[4:6],'little')
    selected=[];values=[];used=[];higher=[];witness=[];dist=[]
    for want, in struct.iter_unpack('<I',q):
        name,slot=next((n,s) for n,s in exports if zlib.crc32(n.encode())==want)
        candidates=[(slot,0,False)]+[(slot+d,d,True) for d in (1,2)]+[(slot-d,d,False) for d in (1,2)]
        for w,d,up in candidates:
            t=token(w)
            if t is None or (up and t<d):continue
            v=t-d if up else t+d
            break
        else:raise ValueError('unresolved fixture')
        selected.append(name);values.append(v);used.append(d!=0);higher.append(up if d else False);witness.append(byslot[w]);dist.append(d*32)
    return {'schema_version':1,'answers':{
      'resolver':{'module':module,'selected_exports':selected},
      'service_tokens':{'values':values},
      'recovery':{'used_neighbor':used,'higher_address':higher,'witness_exports':witness,'distance_bytes':dist}}}
