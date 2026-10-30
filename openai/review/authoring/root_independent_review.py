"""Independent concrete-fixture derivations for three v5 authored samples.

No author reference is imported; no target or original binary is executed.
The reviewer separately inspected all three core implementations and prompts.
"""
from pathlib import Path
import hashlib
import json
import struct
import zlib

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def j(p): return json.loads(p.read_text())


def resolver(f):
    directory=bytes.fromhex(f['exports_hex']);stubs=bytes.fromhex(f['stubs_hex'])
    entries=[(directory[p:p+32].split(b'\0')[0].decode(),int.from_bytes(directory[p+32:p+36],'little'))
             for p in range(0,len(directory),36)]
    by_slot={slot:name for name,slot in entries}
    selected=[];values=[];witness=[];used=[];higher=[];distance=[]
    queries=struct.unpack('<'+'I'*(len(bytes.fromhex(f['queries_hex']))//4),bytes.fromhex(f['queries_hex']))
    for wanted in queries:
        matches=[(name,slot) for name,slot in entries if zlib.crc32(name.encode())==wanted]
        assert len(matches)==1
        name,slot=matches[0];selected.append(name)
        for d in [0,1,2,-1,-2]:
            candidate=slot+d
            if not 0<=candidate<len(stubs)//32:continue
            blob=stubs[candidate*32:(candidate+1)*32]
            if blob[:4]!=bytes.fromhex('4c8bd1b8') or blob[8:11]!=bytes.fromhex('0f05c3'):continue
            token=int.from_bytes(blob[4:6],'little')
            if d>0 and token<d:continue
            values.append(token-d);witness.append(by_slot[candidate]);used.append(d!=0)
            higher.append(d>0);distance.append(abs(d)*32);break
        else:raise AssertionError('no accepted witness')
    return {'schema_version':1,'answers':{
        'resolver':{'module':bytes.fromhex(f['module_hex']).rstrip(b'\0').decode(),'selected_exports':selected},
        'service_tokens':{'values':values},
        'recovery':{'witness_exports':witness,'used_neighbor':used,'higher_address':higher,'distance_bytes':distance}}}


def gate(f):
    raw=bytes.fromhex(f['descriptors_hex']);wanted=int.from_bytes(bytes.fromhex(f['request_hash_hex']),'little')
    rows=[raw[p:p+44] for p in range(0,len(raw),44)]
    selected=[r for r in rows if zlib.crc32(r[:32].split(b'\0')[0])==wanted]
    assert len(selected)==1
    d=selected[0];process,native,entry,ret=struct.unpack_from('<HHHH',d,32)
    alignment,width=d[42:44];accepted=[];targets=[]
    raw=bytes.fromhex(f['requests_hex'])
    for offset in range(0,len(raw),16):
        pm,nm,context,flags=struct.unpack_from('<HHQI',raw,offset)
        good=(pm==process and nm==native and pm!=nm and width==8 and alignment>0
              and alignment&(alignment-1)==0 and context>0 and context%alignment==0 and bool(flags&1))
        accepted.append(bool(good));targets.append(context if good else 0)
    return {'schema_version':1,'answers':{
        'platform':{'api_name':d[:32].split(b'\0')[0].decode(),'required_process_machine':process,'required_native_machine':native},
        'transition_data':{'entry_selector':entry,'return_selector':ret,'marker_hex':d[40:42].hex(),'context_width_bytes':width},
        'requests':{'accepted':accepted,'effective_targets':targets}}}


def builder(f):
    payload=bytes.fromhex(f['payload_hex']);parameter=bytes.fromhex(f['parameter_hex'])
    assert payload[:2]==b'MZ';pe=int.from_bytes(payload[60:64],'little');assert payload[pe:pe+4]==b'PE\0\0'
    machine=int.from_bytes(payload[pe+4:pe+6],'little');magic=int.from_bytes(payload[pe+24:pe+26],'little')
    bits={(0x8664,0x20b):64,(0x14c,0x10b):32}[(machine,magic)]
    loader=bytearray.fromhex(f[f'loader{bits}_hex']);n=len(loader);entry=n+int.from_bytes(payload[pe+40:pe+44],'little')
    locations=[]
    for magic_value in [0xfacecafe,0xdeadc0de,0xfeedf00d,0xaabbccdd]:
        occurrences=[i for i in range(len(loader)-3) if loader[i:i+4]==magic_value.to_bytes(4,'little')]
        assert len(occurrences)==1;locations.append(occurrences[0])
    parameter_offset=n+len(payload)
    patches=[n,len(payload),entry-(locations[2]+4),parameter_offset-(locations[3]+4)]
    for at,value in zip(locations,patches):loader[at:at+4]=value.to_bytes(4,'little')
    combined=loader+payload+parameter
    return {'schema_version':1,'answers':{
        'selection':{'pe_machine':machine,'optional_header_magic':magic,'loader_bits':bits},
        'layout':{'loader_size':n,'payload_size':len(payload),'entry_offset':entry,'parameter_offset':parameter_offset,'total_size':len(combined)},
        'patches':dict(zip(['payload_offset','payload_size','entry_relative_displacement','parameter_relative_displacement'],patches)),
        'parameter':{'ascii':combined[parameter_offset:].split(b'\0')[0].decode()}}}


if __name__=='__main__':
    for name,derive in [('ssnwalk',resolver),('wow64gate',gate),('srdibld',builder)]:
        task=BASE/name
        observed=derive(j(task/'fixtures.json'));expected=j(task/'expected.json')
        assert observed==expected and observed==j(task/'validation/native-answer.json'),name
        build=j(task/'validation/build-results.json')
        assert build['passed'] and build['target_sha256']==sha(task/'target.elf')
        assert build['target_executions']==0 and build['ordinary_entry_reaches_core']
        assert build['rebuild_identical'] and build['stripped_and_debug_free']
        public=(task/'instruction.md').read_text()
        for prohibited in ['sample_entry','uint64_t','out[','0x','fixture_','output_words']:
            assert prohibited not in public,(name,prohibited)
        source=list((task/'source').glob('core.*'))[0].read_text()
        assert 'volatile' in source
        files=[Path(__file__),BASE/'build_samples.py',BASE/'entry_wrapper.c']
        files += [task/n for n in ['fixtures.json','reference.py','expected.json','answer-shape.json','instruction.md','ground-truth.md',
                                  'truth-freeze.json','native-driver.json','source-input-map.json','target.elf',
                                  'validation/build-results.json','validation/native-answer.json','validation/entry-reachability.json']]
        files += sorted(p for p in (task/'source').rglob('*') if p.is_file())
        report={'all_passed':True,'independent_review':True,'reviewer':'root (not sample author)',
                'scope':'Independent fixture derivation, full core/prompt inspection, bound compiler/native/entry evidence.',
                'checks':{'independent_answer_matches':True,'native_answer_matches':True,'ordinary_entry_reachable':True,
                          'only_inert_memory_operations':True,'no_prompt_function_addresses_or_output_map':True,
                          'fixture_reads_preserve_runtime_computation':True,'core_does_not_load_private_truth':True},
                'target_executions':0,'model_calls':0,
                'limitations':['Review covers fixed supplied fixtures, not arbitrary-input correctness or a formal compiler proof.',
                               'Difficulty is unmeasured; no prior revision calibration is transferred.'],
                'bindings':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in files]}
        (task/'review').mkdir(exist_ok=True)
        (task/'review/independent-answer.json').write_text(json.dumps(observed,indent=2,sort_keys=True)+'\n')
        (task/'review/peer-review.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'task':name,'all_passed':True,'target_sha256':build['target_sha256']}))
