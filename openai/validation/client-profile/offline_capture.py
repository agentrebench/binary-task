"""Capture a stock CLI request against loopback only; never call a real model."""
from pathlib import Path
import hashlib
import http.server
import json
import os
import subprocess
import threading

ROOT = Path('/capture')
requests = []
SCENARIO = os.environ.get('OFFLINE_SCENARIO', 'capture')

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        data = json.loads(raw)
        # Never retain authorization headers, even though this test uses a dummy.
        requests.append({'path': self.path, 'body': data})
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        if self.path.endswith('/responses'):
            call = None
            if SCENARIO == 'dispatch' and len(requests) <= 3:
                name, arguments = [
                    ('bash', {'command':'touch /workspace/forbidden-must-not-exist','description':'Unlisted tool rejection control'}),
                    ('static_file', {'path':'target.bin'}),
                    ('static_final_answer', {'schema_version':1,'answers':{}}),
                ][len(requests)-1]
                call = {'id':'fc_'+str(len(requests)), 'type':'function_call', 'call_id':'call_'+str(len(requests)),
                        'name':name, 'arguments':json.dumps(arguments), 'status':'completed'}
            response={'id':'resp_offline','object':'response','created_at':0,'status':'completed','model':data['model'],
                      'output':[{'id':'msg_offline','type':'message','role':'assistant','status':'completed',
                                 'content':[{'type':'output_text','text':'Offline registry capture complete.','annotations':[]}]}],
                      'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}
            frames=[{'type':'response.created','response':dict(response,status='in_progress',output=[])},
                    {'type':'response.output_item.added','output_index':0,'item':dict(response['output'][0],content=[])},
                    {'type':'response.content_part.added','item_id':'msg_offline','output_index':0,'content_index':0,'part':{'type':'output_text','text':'','annotations':[]}},
                    {'type':'response.output_text.delta','item_id':'msg_offline','output_index':0,'content_index':0,'delta':'Offline registry capture complete.'},
                    {'type':'response.output_item.done','output_index':0,'item':response['output'][0]},
                    {'type':'response.completed','response':response}]
            if call:
                response['output'] = [call]
                frames = [
                    {'type':'response.created','response':dict(response,status='in_progress',output=[])},
                    {'type':'response.output_item.added','output_index':0,'item':dict(call,arguments='',status='in_progress')},
                    {'type':'response.function_call_arguments.delta','item_id':call['id'],'output_index':0,'delta':call['arguments']},
                    {'type':'response.function_call_arguments.done','item_id':call['id'],'output_index':0,'arguments':call['arguments']},
                    {'type':'response.output_item.done','output_index':0,'item':call},
                    {'type':'response.completed','response':response},
                ]
            for frame in frames:
                self.wfile.write(('event: '+frame['type']+'\ndata: '+json.dumps(frame)+'\n\n').encode())
        else:
            frame={'id':'chatcmpl-offline','object':'chat.completion.chunk','created':0,'model':data['model'],
                   'choices':[{'index':0,'delta':{'content':'Offline registry capture complete.'},'finish_reason':None}]}
            self.wfile.write(('data: '+json.dumps(frame)+'\n\n').encode())
            frame['choices'][0].update(delta={},finish_reason='stop')
            self.wfile.write(('data: '+json.dumps(frame)+'\n\ndata: [DONE]\n\n').encode())
        self.wfile.flush()

server=http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
port=server.server_port
config={
 'provider':{'openai':{'options':{'baseURL':f'http://127.0.0.1:{port}/v1','apiKey':'offline-dummy-no-credential'},
                       'models':{'gpt-5.3-codex':{'name':'Offline control model','limit':{'context':128000,'output':4096}}}}},
 'mcp':{'static':{'type':'local','command':['python3','-I','/opt/static-tools/server.py']}},
 # Deliberate conflicts must lose to root-managed settings.
 'permission':{'*':'allow'},'agent':{'build':{'permission':{'*':'allow'}}}
}
Path('/home/analyst/.config/opencode').mkdir(parents=True,exist_ok=True)
Path('/home/analyst/.config/opencode/opencode.json').write_text(json.dumps(config))
Path('/workspace/opencode.json').write_text(json.dumps({'permission':{'*':'allow'},'agent':{'build':{'permission':{'*':'allow'}}}}))
env=dict(os.environ)
env.update({'OPENAI_API_KEY':'offline-dummy-no-credential','OPENCODE_DISABLE_MODELS_FETCH':'true',
            'OPENCODE_DISABLE_AUTOUPDATE':'true','OPENCODE_DISABLE_DEFAULT_PLUGINS':'true',
            'OPENCODE_DISABLE_EXTERNAL_SKILLS':'true','OPENCODE_DISABLE_CLAUDE_CODE':'true',
            'OPENCODE_DISABLE_LSP_DOWNLOAD':'true','OPENCODE_FAKE_VCS':'git',
            'OPENCODE_CONFIG_CONTENT':json.dumps({'permission':{'*':'allow'},'agent':{'build':{'permission':{'*':'allow'}}}})})
command=['/opt/opencode','--model=openai/gpt-5.3-codex','run','--format=json','--thinking',
         '--dangerously-skip-permissions','--','Offline control: reply briefly without using tools.']
result=subprocess.run(command,env=env,cwd='/workspace',capture_output=True,text=True,timeout=60)
server.shutdown()
(ROOT/'cli.stdout').write_text(result.stdout)
(ROOT/'cli.stderr').write_text(result.stderr)
(ROOT/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
names=[]
for req in requests:
    tools=req['body'].get('tools',[])
    names.append([t.get('name',t.get('function',{}).get('name',t.get('type'))) for t in tools])
report={'returncode':result.returncode,'request_count':len(requests),'tool_names_per_request':names,
        'command':command,'external_network':'Docker --network none','real_model_calls':0,'target_executions':0}
expected=sorted('static_'+name for name in ('file','strings','readelf','objdump','nm','hexdump','xxd','entropy','final_answer'))
report['scenario']=SCENARIO
report['exact_nine_tools_every_request']=bool(names) and all(sorted(row)==expected for row in names)
report['unlisted_bash_did_not_execute']=not Path('/workspace/forbidden-must-not-exist').exists()
if SCENARIO == 'dispatch':
    report['structured_submission_created']=Path('/workspace/submission/answer.json').exists()
    if report['structured_submission_created']:
        report['submission']=json.loads(Path('/workspace/submission/answer.json').read_text())
    audit=Path('/logs/agent/static-tools.jsonl')
    report['actual_mcp_tools_called']=[json.loads(line)['tool'] for line in audit.read_text().splitlines()]
report['all_passed']=result.returncode==0 and report['exact_nine_tools_every_request'] and report['unlisted_bash_did_not_execute']
if SCENARIO == 'dispatch':
    report['all_passed']=report['all_passed'] and report.get('submission')=={'schema_version':1,'answers':{}} and report['actual_mcp_tools_called']==['file','final_answer']
(ROOT/'capture-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
