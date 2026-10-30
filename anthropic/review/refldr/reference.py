"""Independent private model of inert PE metadata and import resolution."""
from __future__ import annotations
import struct

def text(raw): return raw.split(b'\0',1)[0].decode('ascii')
def unpack_modules(raw):
    modules=[];pos=1
    for _ in range(raw[0]):
        name=text(raw[pos:pos+24]);base,ordinal,start,end,count=struct.unpack_from('<QHIIB',raw,pos+24);pos+=43
        entries=[]
        for i in range(count):
            entries.append({'name':text(raw[pos:pos+32]),'rva':int.from_bytes(raw[pos+32:pos+36],'little'),'forwarder':text(raw[pos+36:pos+100])});pos+=100
        modules.append({'name':name,'base':base,'ordinal':ordinal,'start':start,'end':end,'entries':entries})
    assert pos==len(raw)
    return modules

def solve(f):
    raw=bytes.fromhex(f['image_hex']);pe=int.from_bytes(raw[60:64],'little')
    assert raw[:2]==b'MZ' and raw[pe:pe+4]==b'PE\0\0'
    sections=int.from_bytes(raw[pe+6:pe+8],'little');optional=pe+24
    table=optional+int.from_bytes(raw[pe+20:pe+22],'little')
    preferred=int.from_bytes(raw[optional+24:optional+32],'little')
    newbase=int.from_bytes(bytes.fromhex(f['mapped_base_hex']),'little')
    size=int.from_bytes(raw[optional+56:optional+60],'little')
    image=bytearray(size);mapped=[];rejected=[]
    for i in range(sections):
        at=table+40*i;name=text(raw[at:at+8]);virtual,rva,count,pointer=struct.unpack_from('<IIII',raw,at+8)
        if rva+max(virtual,count)>size or pointer+count>len(raw):rejected.append(name);continue
        image[rva:rva+count]=raw[pointer:pointer+count];mapped.append(name)
    modules=unpack_modules(bytes.fromhex(f['modules_hex']))
    def resolve(module,symbol,ordinal=None):
        visited=set()
        while True:
            mi=next((i for i,m in enumerate(modules) if m['name'].casefold()==module.casefold()),None)
            if mi is None:return None,'missing-module'
            m=modules[mi]
            if ordinal is not None:
                index=ordinal-m['ordinal']
                if not 0<=index<len(m['entries']):return None,'ordinal-out-of-range'
            else:
                index=next((i for i,x in enumerate(m['entries']) if x['name']==symbol),None)
                if index is None:return None,'missing-export'
            if (mi,index) in visited:return None,'forwarder-cycle'
            visited.add((mi,index));entry=m['entries'][index]
            if not m['start']<=entry['rva']<m['end']:
                return m['name']+'!'+entry['name'],'resolved'
            module,symbol=entry['forwarder'].rsplit('.',1)
            if not module.casefold().endswith('.dll'):module+='.dll'
            ordinal=int(symbol[1:]) if symbol.startswith('#') else None
    requests=bytes.fromhex(f['imports_hex']);success=[];failure=[]
    for i in range(requests[0]):
        at=1+59*i;module=text(requests[at:at+24]);kind=requests[at+24];symbol=text(requests[at+25:at+57]);ordinal=int.from_bytes(requests[at+57:at+59],'little') if kind else None
        requested=module+'!'+('#'+str(ordinal) if kind else symbol)
        resolved,reason=resolve(module,symbol,ordinal)
        (success if resolved else failure).append({'requested':requested,**({'resolved':resolved} if resolved else {'reason':reason})})
    reloc=bytes.fromhex(f['relocations_hex']);page,sizeblock=struct.unpack_from('<II',reloc);rvas=[];values=[];skipped=[]
    for at in range(8,sizeblock,2):
        entry=int.from_bytes(reloc[at:at+2],'little');kind=entry>>12;rva=page+(entry&4095)
        if kind==0:continue
        if kind!=10 or rva+8>len(image):skipped.append(rva);continue
        value=(int.from_bytes(image[rva:rva+8],'little')+newbase-preferred)%(1<<64)
        image[rva:rva+8]=value.to_bytes(8,'little');rvas.append(rva);values.append(value)
    return {'schema_version':1,'answers':{
        'mapping':{'image':f['image_name'],'entrypoint':newbase+int.from_bytes(raw[optional+16:optional+20],'little'),'sections':mapped,'rejected_sections':rejected},
        'imports':{'bindings':success},'rejected':{'imports':failure},
        'relocations':{'rvas':rvas,'values':values,'skipped_rvas':skipped}}}
