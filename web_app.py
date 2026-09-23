"""Small local web UI for creating and monitoring reservation tasks.

Run with: ``uv run web_app.py`` and open http://127.0.0.1:8000.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import shlex
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
tasks: dict[str, dict] = {}
lock = threading.Lock()


def start_task(payload: dict) -> dict:
    task_id = uuid.uuid4().hex[:10]
    venue = str(payload.get("venue", "")).strip()
    date = str(payload.get("date", "")).strip()
    times = str(payload.get("times", "")).strip().split()
    spaces = str(payload.get("spaces", "")).strip().split()
    if not venue or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not times:
        raise ValueError("venue、date（YYYY-MM-DD）和 times 不能为空")
    command = [sys.executable, str(ROOT / "main.py"), "--venue", venue,
               "--date", date, "--times", *times]
    if spaces:
        command += ["--spaces", *spaces]
    if venue in ("108", "二体"):
        court_type = str(payload.get("court_type", "auto"))
        command += ["--court-type", "half" if court_type == "auto" else court_type]
    if payload.get("skip_pay"):
        command.append("--skip-pay")
    env = os.environ.copy()
    env["TZ"] = "Asia/Shanghai"
    session = f"pku-{task_id}"
    task_dir = ROOT / "logs" / "web-tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    output_path = task_dir / f"{task_id}.log"
    exit_path = task_dir / f"{task_id}.exit"
    script = ("TZ=Asia/Shanghai PYTHONUNBUFFERED=1 " + shlex.join(command)
              + " > " + shlex.quote(str(output_path)) + " 2>&1; "
              + "printf '%s' \"$?\" > " + shlex.quote(str(exit_path)))
    subprocess.run(["tmux", "new-session", "-d", "-s", session, script],
                   cwd=ROOT, env=env, check=True)
    task = {"id": task_id, "status": "running", "command": command,
            "tmux_session": session,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "lines": [], "returncode": None}
    with lock:
        tasks[task_id] = task

    def read_output() -> None:
        while True:
            lines = output_path.read_text(encoding="utf-8", errors="replace").splitlines() if output_path.exists() else []
            ended = exit_path.exists()
            missing = subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode != 0
            if ended or missing:
                # Read again after exit so the last output is included.
                lines = output_path.read_text(encoding="utf-8", errors="replace").splitlines() if output_path.exists() else []
            with lock:
                task["lines"] = lines[-300:]
                if task["status"] == "aborted": return
                if ended or missing:
                    code = int(exit_path.read_text()) if exit_path.exists() else -1
                    results = []
                    for line in lines:
                        if line.startswith("PKU_RESULT "):
                            try: results.append(json.loads(line[len("PKU_RESULT "):]))
                            except json.JSONDecodeError: pass
                    result = next((r for r in results if r.get("success")), None)
                    if result is None:
                        result = results[-1] if results else {"success": False, "message": "\n".join(lines[-8:]) or "任务异常退出，未返回预约结果"}
                    task["result"] = result
                    task["returncode"] = code
                    task["status"] = "finished" if result["success"] else "failed"
                    return
            threading.Event().wait(1)

    threading.Thread(target=read_output, daemon=True).start()
    return task


def stop_task(task_id: str) -> dict:
    with lock:
        task = tasks.get(task_id)
        if not task:
            raise ValueError("task not found")
        if task["status"] != "running":
            return task
        task["status"] = "aborted"
    subprocess.run(["tmux", "kill-session", "-t", task["tmux_session"]], check=False)
    task["returncode"] = -15
    return task


HTML = """<!doctype html><html lang=zh-CN><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>PKU Auto Venues</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#172033;background:#f4f7fb;line-height:1.5}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 10% 0,#dbeafe 0,transparent 34%),linear-gradient(135deg,#f8fafc,#eef2ff)}.shell{max-width:1080px;margin:auto;padding:42px 20px}.hero{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:26px}.eyebrow{color:#4f46e5;font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.hero h1{font-size:clamp(28px,5vw,42px);margin:7px 0 5px;letter-spacing:-.04em}.hero p{margin:0;color:#64748b}.pill{background:#e0e7ff;color:#4338ca;border-radius:999px;padding:8px 13px;font-size:13px;font-weight:700;white-space:nowrap}.grid{display:grid;grid-template-columns:minmax(300px,390px) 1fr;gap:20px}.card{background:rgba(255,255,255,.86);border:1px solid rgba(255,255,255,.9);box-shadow:0 16px 45px rgba(30,41,59,.1);border-radius:20px;padding:25px;backdrop-filter:blur(12px)}.card h2{font-size:18px;margin:0 0 5px}.hint{font-size:13px;color:#718096;margin:0 0 20px}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:block;color:#334155;font-size:13px;font-weight:700;margin:14px 0 0}input,select{display:block;width:100%;border:1px solid #d8dee9;border-radius:10px;background:#fff;color:#172033;font:inherit;padding:11px 12px;margin-top:6px;outline:none;transition:.2s}input:focus,select:focus{border-color:#6366f1;box-shadow:0 0 0 4px #e0e7ff}.check{display:flex;gap:9px;align-items:center;font-weight:500}.check input{width:16px;margin:0;accent-color:#4f46e5}.primary{width:100%;border:0;border-radius:11px;margin-top:22px;padding:12px 16px;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;font:inherit;font-weight:800;cursor:pointer;box-shadow:0 8px 18px #4f46e544;transition:transform .15s,box-shadow .15s}.primary:hover{transform:translateY(-1px);box-shadow:0 11px 24px #4f46e566}.primary:disabled{opacity:.6;cursor:wait;transform:none}.status{display:flex;align-items:center;gap:10px;min-height:30px;color:#475569;font-size:14px}.dot{width:9px;height:9px;border-radius:50%;background:#94a3b8}.dot.live{background:#10b981;box-shadow:0 0 0 5px #d1fae5}.dot.done{background:#6366f1}.dot.fail{background:#ef4444}.logbox{background:#101827;border-radius:13px;padding:16px;min-height:430px;max-height:560px;overflow:auto;color:#cbd5e1;font:12px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap}.loghead{display:flex;justify-content:space-between;align-items:center;margin:0 0 12px}.loghead span{font-size:12px;color:#94a3b8}.empty{display:grid;place-items:center;min-height:390px;color:#64748b;text-align:center}.empty strong{display:block;color:#334155;margin-bottom:4px}@media(max-width:760px){.shell{padding:25px 14px}.hero{display:block}.pill{display:inline-block;margin-top:15px}.grid{grid-template-columns:1fr}.row{grid-template-columns:1fr}.logbox{min-height:300px}}
#kill{width:auto;margin-top:0;white-space:nowrap;flex-shrink:0}#kill:disabled{cursor:not-allowed}.loghead{gap:12px;flex-wrap:wrap}
.time-picker{border:0;padding:0;margin:14px 0 0;min-width:0}.time-picker legend{font-size:13px;font-weight:700;color:#334155}.time-picker .hint{margin:6px 0 10px}.time-options{display:grid;gap:10px}.time-option{display:flex;align-items:flex-end;gap:8px}.time-option label{flex:1;min-width:0;margin:0;font-size:12px}.time-option select{margin-top:4px;padding:9px 6px}.time-option .remove-time{width:auto;margin:0;padding:10px;flex-shrink:0;font-size:12px}.add-time{margin-top:12px;padding:10px;font-size:13px}

#court-type-field[hidden]{display:none}.space-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.space-options label{display:flex;align-items:center;gap:6px;margin:0;padding:8px;border:1px solid #d8dee9;border-radius:10px;background:#fff}.space-options input{width:16px;margin:0;accent-color:#4f46e5}#space-order{margin-top:10px;overflow-wrap:anywhere}
.result-card{margin:14px 0;padding:16px;border:1px solid #c7d2fe;border-radius:13px;background:#eef2ff;color:#3730a3}.result-card[hidden]{display:none}.result-card.success{background:#ecfdf5;border-color:#a7f3d0;color:#065f46}.result-card.failure{background:#fef2f2;border-color:#fecaca;color:#991b1b}.result-card h3{margin:0 0 6px;font-size:16px}.result-card p{margin:0;font-size:14px;white-space:pre-wrap;overflow-wrap:anywhere}
.log-card{display:flex;flex-direction:column;min-width:0}.log-card .logbox{flex:1 1 0;margin:0;max-height:none;min-height:300px}.log-card .empty{flex:1}
#task{overflow-wrap:anywhere;user-select:text}
.task-info{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0}.copy-session{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;padding:5px;border:0;border-radius:6px;background:transparent;color:#64748b;cursor:pointer;flex-shrink:0;transition:background .15s,color .15s}.copy-session:hover:not(:disabled){background:#e0e7ff;color:#4f46e5}.copy-session:focus-visible{outline:2px solid #6366f1;outline-offset:2px}.copy-session:disabled{opacity:.4;cursor:not-allowed}
</style><body><div class=shell><header class=hero><div><div class=eyebrow>PKU AUTO VENUES</div><h1>预约控制台</h1><p>配置一次预约任务，实时掌握抢场进度。</p></div><div class=pill>● 本地运行</div></header><div class=grid><section class=card><h2>创建预约任务</h2><p class=hint>任务会在后台运行，关闭页面不会中断预约。</p><form id=f><div class=row><label>场馆<select name=venue required><option value=60>邱德拔羽毛球馆</option><option value=86>五四羽毛球馆</option><option value=68>邱德拔篮球馆</option><option value=82>五四篮球场</option><option value=108>二体篮球场</option></select></label><label>预约日期<input name=date type=date required></label></div><fieldset class=time-picker><legend>目标时段</legend><p class=hint>按列表顺序尝试，每项可预约连续 1 或 2 小时。</p><div id=time-options class=time-options></div><button type=button class="primary add-time" id=add-time>＋ 添加目标时间</button></fieldset><label id=court-type-field hidden>预约类型<select name=court_type disabled><option value=auto>未指定（默认半场）</option><option value=half>半场</option><option value=full>整场</option></select></label><fieldset class=time-picker><legend>优先场地</legend><p class=hint>可多选，按勾选顺序优先尝试；不选则随机选择。</p><div id=space-options class=space-options></div><p id=space-order class=hint aria-live=polite></p></fieldset><label class=check><input name=skip_pay type=checkbox>跳过自动支付</label><button class=primary id=submit>启动预约任务</button></form></section><section class="card log-card"><div class=loghead><div><h2>运行状态</h2><div id=s class=status><i class=dot></i><span>等待创建任务</span></div></div><div class=task-info><span id=task></span><button type=button class=copy-session id=copy-session title="复制 tmux 会话名" aria-label="复制 tmux 会话名" disabled><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button><span id=copy-feedback role=status aria-live=polite></span></div><button class=primary type=button id=kill onclick="stop()" disabled>中止任务</button></div><div id=reservation-result class=result-card role=status aria-live=polite hidden><h3 id=result-title></h3><p id=result-message></p></div><div id=empty class=empty><div><strong>还没有运行日志</strong><span>创建任务后，验证码、查询和提交进度会显示在这里</span></div></div><pre id=log class=logbox hidden></pre></section></div></div>
<script>
const venueSelect=document.querySelector('[name=venue]');
const courtTypeField=document.querySelector('#court-type-field');
const courtTypeSelect=document.querySelector('[name=court_type]');
const spaceOptions=document.querySelector('#space-options');
const spaceOrder=document.querySelector('#space-order');
let selectedSpaces=[];
function updateSpaces(){
 selectedSpaces=[];
 spaceOptions.replaceChildren();
 spaceOrder.textContent='';
 const venue=venueSelect.value;
 const halves=venue==='82'||venue==='68'||(venue==='108'&&courtTypeSelect.value!=='full');
 const count=({'60':12,'86':9,'82':8,'68':2,'108':4})[venue];
 for(let number=1;number<=count;number++){
  const names=halves?['南'+number,'北'+number]:[number+'号场'];
  for(const name of names){
   const label=document.createElement('label');
   const input=document.createElement('input');input.type='checkbox';
   input.value=halves?name:(venue==='108'&&courtTypeSelect.value==='full'?'北'+number+',南'+number:number+'号');
   input.onchange=()=>{
    if(input.checked)selectedSpaces.push({value:input.value,label:name});
    else selectedSpaces=selectedSpaces.filter(space=>space.value!==input.value);
    spaceOrder.textContent=selectedSpaces.length?'优先顺序：'+selectedSpaces.map(space=>space.label).join(' → '):'';
   };
   label.append(input,document.createTextNode(name));spaceOptions.appendChild(label);
  }
 }
}
courtTypeSelect.addEventListener('change',updateSpaces);
function updateCourtType(){
 const isErti=venueSelect.value==='108';
 courtTypeField.hidden=!isErti;
 courtTypeSelect.disabled=!isErti;
 if(!isErti)courtTypeSelect.value='auto';
 updateSpaces();
}
venueSelect.addEventListener('change',updateCourtType);
updateCourtType();
const timeOptions=document.querySelector('#time-options');
function addTime(){
 const row=document.createElement('div');row.className='time-option';
 const hours=Array.from({length:24},(_,hour)=>{const time=String(hour).padStart(2,'0')+':00';return '<option value="'+time+'"'+(hour===17?' selected':'')+'>'+time+'</option>'}).join('');
 row.innerHTML='<label>开始时间<select class="start-time">'+hours+'</select></label><label>连续时长<select class="duration"><option value="1">1 小时</option><option value="2">2 小时</option></select></label><button type="button" class="primary remove-time" aria-label="删除目标时间">删除</button>';
 row.querySelector('button').onclick=()=>{row.remove();updateRemoveButtons()};
 timeOptions.appendChild(row);updateRemoveButtons();
}
function updateRemoveButtons(){timeOptions.querySelectorAll('.remove-time').forEach(button=>{button.hidden=timeOptions.children.length===1})}
document.querySelector('#add-time').onclick=addTime;
addTime();
function showResult(title,message,kind=''){
 const panel=document.querySelector('#reservation-result');
 panel.className='result-card'+(kind?' '+kind:'');
 document.querySelector('#result-title').textContent=title;
 document.querySelector('#result-message').textContent=message;
 panel.hidden=false;
}
let tmuxSession='';
const copySessionButton=document.querySelector('#copy-session');
const copyFeedback=document.querySelector('#copy-feedback');
copySessionButton.onclick=async()=>{
 if(!tmuxSession)return;
 try{
  await navigator.clipboard.writeText(tmuxSession);
  copyFeedback.textContent='已复制';
 }catch(error){
  copyFeedback.textContent='复制失败，请手动复制会话名';
 }
};
let id;const statusEl=document.querySelector('#s'),logEl=document.querySelector('#log'),emptyEl=document.querySelector('#empty'),submit=document.querySelector('#submit');function showStatus(t,c=''){statusEl.innerHTML='<i class="dot '+c+'"></i><span>'+t+'</span>'}function showLog(){emptyEl.hidden=true;emptyEl.style.display='none';logEl.hidden=false;logEl.style.display='block'}f.onsubmit=async e=>{e.preventDefault();const times=[...timeOptions.querySelectorAll('.time-option')].map(row=>{const duration=row.querySelector('.duration').value;return row.querySelector('.start-time').value+(duration==='2'?'/2':'')});if(!times.length){showStatus('请至少选择一个目标时段','fail');return}submit.disabled=true;showStatus('正在启动任务');showResult('正在启动任务','正在创建预约任务，请稍候。');let o=Object.fromEntries(new FormData(f));o.times=times.join(' ');o.spaces=selectedSpaces.map(space=>space.value).join(' ');o.skip_pay=!!o.skip_pay;try{let r=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)}),j=await r.json();if(!r.ok)throw Error(j.error);id=j.id;task.textContent='任务 '+id+' · tmux: '+j.tmux_session;tmuxSession=j.tmux_session;copySessionButton.disabled=!tmuxSession;copyFeedback.textContent='';document.querySelector('#kill').disabled=false;showLog();poll()}catch(e){showStatus(e.message,'fail');showResult('启动失败',e.message,'failure');submit.disabled=false}};async function stop(){if(!id)return;await fetch('/api/tasks/'+id+'/kill',{method:'POST'});poll()}async function poll(){if(!id)return;let j=await(await fetch('/api/tasks/'+id)).json();showStatus(j.status==='running'?'运行中':j.status==='finished'?'已完成':j.status==='aborted'?'已中止':'执行失败',j.status==='running'?'live':j.status==='finished'?'done':'fail');if(j.result){showResult(j.result.success?'预约成功':'预约失败',j.result.message,j.result.success?'success':'failure')}else if(j.status==='aborted'){showResult('任务已中止','任务已停止，请以预约系统中的订单状态为准。')}else if(j.status==='running'){showResult('预约进行中','任务正在运行，预约结果将在这里显示。')}showLog();logEl.textContent=j.lines.join('\\n');logEl.scrollTop=logEl.scrollHeight;if(j.status==='running')setTimeout(poll,1000);else {submit.disabled=false;document.querySelector('#kill').disabled=true;}}</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, code=200):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            raw = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if path.startswith("/api/tasks/"):
            with lock: task = tasks.get(path.rsplit("/", 1)[-1])
            self.send_json(task or {"error": "task not found"}, 200 if task else 404); return
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path.endswith("/kill"):
            try: self.send_json(stop_task(urlparse(self.path).path.split("/")[-2]), 200)
            except ValueError as exc: self.send_json({"error": str(exc)}, 404)
            return
        if urlparse(self.path).path != "/api/tasks": self.send_json({"error": "not found"}, 404); return
        try:
            length = int(self.headers.get("Content-Length", 0)); payload = json.loads(self.rfile.read(length)); task = start_task(payload); self.send_json(task, 201)
        except (ValueError, json.JSONDecodeError, OSError) as exc: self.send_json({"error": str(exc)}, 400)

    def log_message(self, *_): pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000")); print(f"Open http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
