#!/usr/bin/env python3
"""launchd-owned gateway/tunnel supervisor. Log lifecycle only, never chat text."""
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / 'Library/Application Support/BibleCounsel'
STATE.mkdir(parents=True, exist_ok=True)
os.chmod(STATE, 0o700)
log = logging.getLogger('bible-counsel')
log.setLevel(logging.INFO)
handler = RotatingFileHandler(STATE/'lifecycle.log', maxBytes=2_000_000, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.addHandler(handler)
stop = threading.Event()
children = {}
lock = threading.Lock()


def shutdown(signum, frame):
    log.info('Supervisor received signal=%s', signum)
    stop.set()
    with lock:
        for process in children.values():
            if process.poll() is None: process.terminate()


for sig in (signal.SIGTERM, signal.SIGINT): signal.signal(sig, shutdown)


def publish(url):
    for attempt in range(1, 7):
        if stop.is_set(): return
        try:
            with urlopen(url+'/api/health', timeout=10) as response:
                json.load(response)
            path = ROOT/'counsel-config.js'
            old = path.read_text()
            new = re.sub(r'https://[a-z0-9-]+\.trycloudflare\.com/api/chat', url+'/api/chat', old)
            if new != old:
                temporary = path.with_suffix('.js.tmp')
                temporary.write_text(new)
                temporary.replace(path)
            def git(*args):
                subprocess.run(['/usr/bin/git',*args],cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
            changed = subprocess.run(['/usr/bin/git','diff','HEAD','--quiet','--','counsel-config.js'],cwd=ROOT).returncode
            if changed:
                git('-c','user.name=Wonseong620','-c','user.email=kindws@gmail.com','commit','--only','-m','Refresh supervised public tunnel endpoint','--','counsel-config.js')
            git('push','origin','master')
            log.info('Public endpoint synchronized url=%s',url)
            return
        except Exception as error:
            log.warning('Endpoint publish attempt=%s failed type=%s url=%s reason=%s',attempt,type(error).__name__,url,str(getattr(error,'reason','operation failed')))
            stop.wait(15)
    log.error('Endpoint publish failed; manual attention required url=%s',url)


def run_service(name, command):
    while not stop.is_set():
        started=time.monotonic()
        try:
            process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            with lock: children[name]=process
            log.info('Started service=%s pid=%s',name,process.pid)
            published=False
            for line in process.stdout:
                # Never record arbitrary subprocess lines: they may contain user data.
                if name=='tunnel':
                    match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
                    if match and not published:
                        log.info('New tunnel URL=%s',match.group())
                        published=True
                        threading.Thread(target=publish,args=(match.group(),),daemon=True).start()
                    if 'Registered tunnel connection' in line: log.info('Tunnel connection registered')
                    elif 'ERR ' in line: log.warning('Tunnel reported an error')
                elif 'Traceback (most recent call last)' in line: log.error('Gateway emitted a traceback; details suppressed to protect conversation data')
            code=process.wait()
            log.warning('Exited service=%s pid=%s exit_code=%s uptime_seconds=%.1f',name,process.pid,code,time.monotonic()-started)
        except Exception as error:
            log.error('Launch failure service=%s type=%s',name,type(error).__name__)
        if not stop.is_set():
            log.info('Restart scheduled service=%s delay_seconds=5',name)
            stop.wait(5)


log.info('Supervisor started pid=%s',os.getpid())
workers=[threading.Thread(target=run_service,args=('gateway',['/usr/bin/python3','-u',str(ROOT/'server/app.py')])),
         threading.Thread(target=run_service,args=('tunnel',[str(ROOT.parent/'.tools/cloudflared'),'tunnel','--url','http://127.0.0.1:8765','--http-host-header','127.0.0.1:8765','--no-autoupdate']))]
for worker in workers: worker.start()
while not stop.wait(1): pass
for worker in workers: worker.join(timeout=15)
with lock:
    for process in children.values():
        if process.poll() is None: process.kill()
log.info('Supervisor stopped')
