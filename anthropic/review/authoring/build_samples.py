"""Build seven inert artifacts with their data behavior reachable from main.

Existing framework/campaign sources are never edited. Target and reference
hashes are recorded separately. Expected answers are used only for comparison.
The generic entry wrapper consumes core outputs but prints no answers. Only
separately compiled native ARM references, never x86 targets, are executed.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, platform, re, shutil, struct, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from agentre_bench.harbor.verifier import validate_contract, grade
from agentre_bench.harbor.package import verify_no_embedded_self_tests

RUST=ROOT/'.toolchain/rust-1.85.1/installed/bin/rustc'
WRAPPER=BASE/'entry_wrapper.c'
CXX=[str(ROOT/'.toolchain/cross-cxx/usr/bin/x86_64-linux-gnu-g++-13'),
 '-nostdinc','-nostdinc++',
 '-isystem',str(ROOT/'.toolchain/cross-cxx/usr/x86_64-linux-gnu/include/c++/13'),
 '-isystem',str(ROOT/'.toolchain/cross-cxx/usr/x86_64-linux-gnu/include/c++/13/x86_64-linux-gnu'),
 '-isystem',str(ROOT/'.toolchain/cross-cxx/usr/x86_64-linux-gnu/include/c++/13/backward'),
 '-isystem','/usr/lib/gcc-cross/x86_64-linux-gnu/13/include',
 '-isystem','/usr/x86_64-linux-gnu/include',
 '-B/usr/x86_64-linux-gnu/bin/','-B/usr/lib/gcc-cross/x86_64-linux-gnu/13/',
 '-B/usr/x86_64-linux-gnu/lib/']

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def run(cmd,**kw):
    r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=180,**kw)
    if r.returncode: raise RuntimeError(f'command failed: {cmd}\n{r.stdout}\n{r.stderr}')
    return r.stdout
def get_path(obj,path):
    for k in path: obj=obj[k]
    return obj
def put_path(obj,path,value):
    cur=obj
    for i,key in enumerate(path):
        last=i==len(path)-1
        if isinstance(cur,list):
            while len(cur)<=key: cur.append(None)
            if last: cur[key]=value;return
            if cur[key] is None: cur[key]=[] if isinstance(path[i+1],int) else {}
        else:
            if last: cur[key]=value;return
            cur.setdefault(key,[] if isinstance(path[i+1],int) else {})
        cur=cur[key]

def map_words(words,mapping):
    result={'schema_version':1,'answers':{}}
    for f in mapping['fields']:
        o=f['offset'];kind=f['kind'];n=words[f['length_offset']] if 'length_offset' in f else f.get('count',1)
        assert 0<=o<len(words) and 0<=n<=len(words)-o
        if kind=='u64': value=words[o]
        elif kind=='bool':
            assert words[o] in (0,1);value=bool(words[o])
        elif kind=='u64_array': value=words[o:o+n]
        elif kind=='ascii': value=bytes(words[o:o+n]).decode('ascii')
        elif kind=='bytes_hex': value=bytes(words[o:o+n]).hex()
        elif kind=='enum': value=f['values'][str(words[o])]
        else: raise ValueError(kind)
        put_path(result,f['path'],value)
    for a in mapping.get('assertions',[]): assert words[a['offset']]==a['equals'],a
    return result

def elf_bytes(path,addr,size):
    b=Path(path).read_bytes();assert b[:6]==b'\x7fELF\x02\x01'
    phoff=struct.unpack_from('<Q',b,32)[0]
    ent,num=struct.unpack_from('<HH',b,54)
    for i in range(num):
        typ,flags,off,va,pa,fs,ms,align=struct.unpack_from('<IIQQQQQQ',b,phoff+i*ent)
        if typ==1 and va<=addr and addr+size<=va+fs:
            return b[off+addr-va:off+addr-va+size]
    raise ValueError('address outside file-backed load segments')

def symbols(path):
    result={}
    for line in run(['x86_64-linux-gnu-nm','-S','--defined-only',path]).splitlines():
        p=line.split()
        if len(p)==4 and re.fullmatch('[0-9a-fA-F]+',p[0]): result[p[3]]={'address':int(p[0],16),'size':int(p[1],16),'type':p[2]}
    return result

def source_inputs(task,target,syms):
    fixtures=json.loads((task/'fixtures.json').read_text());checks=[]
    for item in json.loads((task/'source-input-map.json').read_text())['symbols']:
        raw=bytes.fromhex(item['expected_hex']);p=get_path(fixtures,item['fixture_path'])
        actual_fixture=p.encode('ascii') if item.get('encoding')=='ascii' else bytes(p) if isinstance(p,list) else bytes.fromhex(p)
        assert raw==actual_fixture,item['symbol']
        sym=syms[item['symbol']];assert sym['size']>=len(raw)
        assert elf_bytes(target,sym['address'],len(raw))==raw,item['symbol']
        checks.append({'symbol':item['symbol'],'address':hex(sym['address']),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return checks

def make_native_driver(count):
    return '''#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int sample_entry(uint64_t *out);
void rust_eh_personality(void) {}
int main(void) {
 struct { uint64_t before[8], out[COUNT], after[8]; } b;
 uint64_t saved[COUNT]; int first_rc=0;
 for(unsigned pass=0;pass<3;pass++) {
  for(unsigned i=0;i<8;i++) b.before[i]=b.after[i]=0xa71c85d3f19b620eULL;
  for(unsigned i=0;i<COUNT;i++) b.out[i]=pass?0xa5a5a5a5a5a5a5a5ULL:0;
  int rc=sample_entry(b.out);
  for(unsigned i=0;i<8;i++) if(b.before[i]!=0xa71c85d3f19b620eULL || b.after[i]!=0xa71c85d3f19b620eULL) return 90;
  if(pass==0) { first_rc=rc;memcpy(saved,b.out,sizeof(saved)); }
  else if(first_rc!=rc || memcmp(saved,b.out,sizeof(saved))) return 91;
 }
 printf("%d\\n",first_rc);
 for(unsigned i=0;i<COUNT;i++) printf("%llu\\n",(unsigned long long)saved[i]);
 return 0;
}
'''.replace('COUNT',str(count))

def compile_target(task,source,kind,outdir):
    flags=['-O2','-g0','-fno-ident','-ffunction-sections','-fdata-sections']
    obj=outdir/('core.a' if kind=='Rust' else 'core.o')
    if kind=='Rust':
        cmd=[RUST,source,'--crate-name',task.name,'--crate-type=staticlib','--edition=2021',
             '--target=x86_64-unknown-linux-gnu','--remap-path-prefix='+str(task/'source')+'=/source','-C','panic=abort','-C','opt-level=2','-C','debuginfo=0','-o',obj]
    else:
        cmd=(CXX+['-std=c++17','-fno-exceptions','-fno-rtti'] if kind=='C++' else ['x86_64-linux-gnu-gcc','-std=c11'])+flags+['-c',source,'-o',obj]
    run(cmd)
    count=json.loads((task/'native-driver.json').read_text())['output_words']
    assert type(count) is int and 0<count<=8192
    main=outdir/'entry.c';main.write_bytes(WRAPPER.read_bytes())
    un=outdir/'unstripped.elf';target=outdir/'target.elf'
    retained=[x['symbol'] for x in json.loads((task/'source-input-map.json').read_text())['symbols']]
    # Fixture-only retention preserves the separately reviewed data-byte map.
    # The core is retained solely by main's ordinary symbol reference/call.
    assert 'sample_entry' not in retained
    link=['x86_64-linux-gnu-gcc','-std=c11','-O2','-fno-ident','-g0','-DOUTPUT_WORDS='+str(count),
          main,obj,'-Wl,--build-id=none,--gc-sections,--strip-debug',
          *['-Wl,--undefined='+name for name in retained],'-o',un]
    run(link);run(['x86_64-linux-gnu-strip','--strip-all','-o',target,un]);target.chmod(0o444)
    return cmd,link

def inspect_reachability(target,un,syms,link):
    """Bind the actual ELF entry/main/core path without running the artifact."""
    assert all(name in syms for name in ('_start','main','sample_entry','observation_sink'))
    assert not any('--undefined=sample_entry' in str(arg) for arg in link)
    start=syms['_start'];main=syms['main'];core=syms['sample_entry'];sink=syms['observation_sink']
    entry=struct.unpack_from('<Q',Path(target).read_bytes(),24)[0]
    assert entry==start['address']
    def disassemble(symbol):
        return run(['x86_64-linux-gnu-objdump','-d','-Mintel',
                    '--start-address='+hex(symbol['address']),
                    '--stop-address='+hex(symbol['address']+symbol['size']),un])
    startup=disassemble(start);body=disassemble(main)
    load=re.search(r'(?m)^\s*([0-9a-f]+):.*\blea\s+rdi,.*#\s*'+format(main['address'],'x')+r'\s+<main>',startup)
    runtime=re.search(r'(?m)^\s*([0-9a-f]+):.*\bcall\b.*<__libc_start_main[^>]*>',startup)
    call=re.search(r'(?m)^\s*([0-9a-f]+):.*\bcall\s+'+format(core['address'],'x')+r'\s+<sample_entry>',body)
    store=re.search(r'(?m)^\s*([0-9a-f]+):.*\bmov\s+QWORD PTR \[rip[^\]]*\],.*#\s*'+format(sink['address'],'x')+r'\s+<observation_sink>',body)
    assert load and runtime and call and store,(startup,body)
    assert int(load[1],16)<int(runtime[1],16)
    assert int(call[1],16)<int(store[1],16)
    sections=run(['x86_64-linux-gnu-readelf','-W','-S',target])
    assert not re.search(r'\]\s+\.(?:symtab|strtab|debug\S*|zdebug\S*)\s',sections)
    dynamic=run(['x86_64-linux-gnu-nm','-D','--defined-only',target])
    exported={line.split()[-1].split('@')[0] for line in dynamic.splitlines() if line.strip()}
    authored=set(syms)-{'_start','__abi_tag','completed.0'}
    assert exported.isdisjoint(authored),(exported & authored)
    return {
        'elf_entry':hex(entry),'main_address':hex(main['address']),
        'core_address':hex(core['address']),'sink_address':hex(sink['address']),
        'startup_main_argument_instruction':hex(int(load[1],16)),
        'startup_libc_call_instruction':hex(int(runtime[1],16)),
        'main_core_call_instruction':hex(int(call[1],16)),
        'main_sink_store_instruction':hex(int(store[1],16)),
        'main_calls_core_without_undefined_retention':True,
        'main_observably_consumes_outputs':True,'main_returns_normally':True,
        'stripped_and_debug_free':True,'no_exported_authored_names':True,
        'dynamic_defined_names':sorted(exported),
        'startup_disassembly_sha256':hashlib.sha256(startup.encode()).hexdigest(),
        'main_disassembly_sha256':hashlib.sha256(body.encode()).hexdigest(),
        'basis':'ELF e_entry, actual CRT RDI main argument, libc startup call, direct main-to-core call and subsequent volatile sink store; section-byte preservation binds stripped target.'
    },startup,body

def validate_native_wrapper(task,val,obj,words,status,san):
    """Call the same wrapper in a separately compiled, reviewed ARM reference."""
    count=len(words)
    wrapper_obj=val/'entry-wrapper-native.o'
    command=['gcc','-std=c11',*san,'-DOUTPUT_WORDS='+str(count),
             '-Dmain=reviewed_wrapper_main','-c',WRAPPER,'-o',wrapper_obj]
    run(command)
    driver=val/'wrapper-driver.c'
    driver.write_text('''#include <stdint.h>
#include <stdio.h>
extern int reviewed_wrapper_main(void);
extern volatile uint64_t observation_sink;
int main(void) {
    for (unsigned i = 0; i < 2; ++i) {
        observation_sink = UINT64_C(0xa5a5a5a5a5a5a5a5);
        int status = reviewed_wrapper_main();
        printf("%d %llu\\n", status, (unsigned long long)observation_sink);
    }
    return 0;
}
''')
    native=val/'wrapper-native'
    run(['gcc',*san,driver,wrapper_obj,obj,'-o',native])
    assert 'aarch64' in run(['file',native])
    result=subprocess.run([str(native)],capture_output=True,text=True,timeout=30,
        env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    assert result.returncode==0 and not result.stderr,(result.returncode,result.stderr)
    rows=[[int(value) for value in line.split()] for line in result.stdout.splitlines()]
    expected=((status & 0xffffffff)+sum(words)) & ((1<<64)-1)
    assert rows==[[0,expected],[0,expected]],rows
    (val/'wrapper-native-output.txt').write_text(result.stdout)
    evidence={
        'passed':True,'reference_architecture':'aarch64','native_wrapper_calls':2,
        'native_wrapper_compile':[str(x) for x in command],
        'wrapper_source':{'path':str(WRAPPER.relative_to(ROOT)),'sha256':digest(WRAPPER)},
        'driver_source_sha256':digest(driver),'native_binary_sha256':digest(native),
        'native_output_sha256':digest(val/'wrapper-native-output.txt'),
        'wrapper_returns':[row[0] for row in rows],'observed_sink_values':[row[1] for row in rows],
        'expected_sink_from_independently_validated_core_words':expected,
        'sink_is_private_validation_only_not_a_graded_question':True,
        'normal_wrapper_contains_no_expected_values_or_output_printer':True,
        'target_executions':0,'original_executions':0,'model_api_calls':0,
        'sanitizer_scope':'Native C entry wrapper and driver instrumented; core scope is recorded separately.',
    }
    save(val/'wrapper-native-validation.json',evidence)
    return evidence

def build(task):
    assert platform.machine()=='aarch64','Only reviewed native ARM reference executions are allowed'
    freeze=json.loads((task/'truth-freeze.json').read_text())
    for name,sha in freeze['files'].items(): assert digest(task/name)==sha,('frozen-file-changed',task.name,name)
    kinds=[('C',task/'source/core.c'),('C++',task/'source/core.cpp'),('Rust',task/'source/core.rs')]
    kind,source=next((k,p) for k,p in kinds if p.exists())
    val=task/'validation';val.mkdir(exist_ok=True)
    fixtures=json.loads((task/'fixtures.json').read_text())
    ms=importlib.util.spec_from_file_location('reference_'+task.name,task/'reference.py');m=importlib.util.module_from_spec(ms);sys.modules[ms.name]=m;ms.loader.exec_module(m)
    computed=m.solve(fixtures);expected=json.loads((task/'expected.json').read_text());assert computed==expected
    shape=json.loads((task/'answer-shape.json').read_text());contract={'schema_version':1,'answer_shape':shape,'expected':expected['answers']};validate_contract(contract)
    cmd,link=compile_target(task,source,kind,task)
    target=task/'target.elf';un=task/'unstripped.elf';syms=symbols(un)
    assert 'sample_entry' in syms
    a='\n'.join(run(['x86_64-linux-gnu-objdump','-s',un]).splitlines()[2:]);b='\n'.join(run(['x86_64-linux-gnu-objdump','-s',target]).splitlines()[2:]);assert a==b
    reachability,startup,main=inspect_reachability(target,un,syms,link)
    (val/'startup-disassembly.txt').write_text(startup)
    (val/'main-disassembly.txt').write_text(main)
    save(val/'entry-reachability.json',reachability)
    mappings=source_inputs(task,target,syms)
    verify_no_embedded_self_tests(target)
    dis=run(['x86_64-linux-gnu-objdump','-d',target]);(task/'disassembly.txt').write_text(dis)
    headers=run(['x86_64-linux-gnu-readelf','-W','-l','-d',target]);(task/'headers.txt').write_text(headers)
    assert not re.search(r'^\s*LOAD.*\bRWE\b',headers,re.M)
    assert not re.search(r'^\s*GNU_STACK.*\bRWE\b',headers,re.M)
    assert not re.search(r'\b(syscall|sysenter)\b',dis)
    undefined=run(['x86_64-linux-gnu-nm','-u',un])
    allowed={'__libc_start_main','__cxa_finalize','__gmon_start__','__stack_chk_fail','_ITM_deregisterTMCloneTable','_ITM_registerTMCloneTable','memcpy','memset','memcmp','memmove','bcmp','abort'}
    imports=[line.split()[-1].split('@')[0] for line in undefined.splitlines() if line.strip()]
    assert set(imports)<=allowed,imports
    mapping=json.loads((task/'native-driver.json').read_text())
    driver=val/'driver.c';driver.write_text(make_native_driver(mapping['output_words']))
    san=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
    run(['gcc',*san,'-c',driver,'-o',val/'driver.o'])
    if kind=='Rust':
        native_compile=[RUST,source,'--crate-name',task.name+'_reference','--crate-type=staticlib','--edition=2021',
            '-C','panic=abort','-C','opt-level=1','-C','overflow-checks=yes','-C','debug-assertions=yes','-o',val/'core-native.a']
        run(native_compile);obj=val/'core-native.a'
    else:
        native_compile=(['g++','-std=c++17','-fno-exceptions','-fno-rtti'] if kind=='C++' else ['gcc','-std=c11'])+san+['-c',source,'-o',val/'core-native.o']
        run(native_compile);obj=val/'core-native.o'
    native=val/'driver-native';run(['gcc',*san,val/'driver.o',obj,'-o',native])
    assert 'ARM aarch64' in run(['file',native]) or 'aarch64' in run(['file',native])
    r=subprocess.run([str(native)],capture_output=True,text=True,timeout=30,
        env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    assert r.returncode==0,(r.returncode,r.stderr)
    assert not r.stderr,r.stderr
    (val/'native-words.txt').write_text(r.stdout)
    nums=[int(x) for x in r.stdout.splitlines()];assert nums[0]==mapping['return_value'];words=nums[1:]
    assert len(words)==mapping['output_words']
    actual=map_words(words,mapping);save(val/'native-answer.json',actual)
    assert actual==expected,{'native':actual,'expected':expected}
    assert grade(json.dumps(actual).encode(),contract)['reward']==1
    native_wrapper=validate_native_wrapper(task,val,obj,words,nums[0],san)
    with tempfile.TemporaryDirectory(prefix='agentre-rebuild-') as tmp:
        compile_target(task,source,kind,Path(tmp));assert digest(Path(tmp)/'target.elf')==digest(target)
    save(task/'symbols.json',syms)
    result={'task_id':task.name,'language':kind,'passed':True,'recorded_at':datetime.now(timezone.utc).isoformat(),
      'build_driver':{'path':str(Path(__file__).relative_to(ROOT)),'sha256':digest(Path(__file__))},
      'entry_wrapper_source':{'path':str(WRAPPER.relative_to(ROOT)),'sha256':digest(WRAPPER)},
      'entry_wrapper_copy_sha256':digest(task/'entry.c'),
      'truth_freeze_sha256':digest(task/'truth-freeze.json'),'source_files':{str(p.relative_to(task)):digest(p) for p in (task/'source').rglob('*') if p.is_file()},
      'target_sha256':digest(target),'target_bytes':target.stat().st_size,'entry_virtual_address':hex(syms['sample_entry']['address']),
      'ordinary_elf_entry_virtual_address':reachability['elf_entry'],
      'ordinary_main_virtual_address':reachability['main_address'],
      'ordinary_entry_reaches_core':True,'core_not_retained_by_undefined_flag':True,
      'no_exported_authored_names':True,'stripped_and_debug_free':True,
      'entry_reachability':{'path':str((val/'entry-reachability.json').relative_to(ROOT)),'sha256':digest(val/'entry-reachability.json')},
      'native_wrapper_validation':{'path':str((val/'wrapper-native-validation.json').relative_to(ROOT)),'sha256':digest(val/'wrapper-native-validation.json')},
      'target_executions':0,'original_executions':0,'model_api_calls':0,'reference_native_arch':'aarch64',
      'native_compile':[str(x) for x in native_compile],'target_compile':[str(x) for x in cmd],'target_link':[str(x) for x in link],
      'independent_reference_matches_frozen_truth':True,'native_matches_frozen_truth':True,'native_word_count':len(words),
      'native_canaries_and_three_repeats':True,'native_asan_ubsan_clean':True,
      'sanitizer_scope':'C driver only; Rust core has bounds/overflow/debug checks, not Rust ASan instrumentation' if kind=='Rust' else 'C/C++ core and C driver',
      'source_input_checks':mappings,'strip_preserves_section_bytes':True,'rebuild_identical':True,
      'imports':imports,'no_syscall_instructions':True,'no_writable_executable_segments':True,
      'target_not_executable_file_mode':oct(target.stat().st_mode&0o777),
      'ground_truth_claim':'Independent fixture model + separately compiled native source agree; human compiled-code review remains separate.'}
    save(val/'build-results.json',result)
    print(json.dumps({k:result[k] for k in ['task_id','language','passed','target_sha256','entry_virtual_address','native_word_count']}),flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('tasks',nargs='+');args=parser.parse_args()
    for name in args.tasks: build(BASE/name)
