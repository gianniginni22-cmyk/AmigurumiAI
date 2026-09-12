"""Desktop entry point with automatic HTTPS update check."""
import json, os, socket, subprocess, sys, threading, time, urllib.parse, urllib.request
from pathlib import Path
import uvicorn, webview
from app.main import app
from app.update_utils import validate_update_manifest, version_tuple

APP_VERSION='0.7.4'
UPDATE_MANIFEST_URL=os.getenv('AMIGURUMI_UPDATE_MANIFEST','https://raw.githubusercontent.com/gianniginni22-cmyk/AmigurumiAI/main/update-manifest.json')

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return int(s.getsockname()[1])

def run_server(port):
    config=uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False)
    server=uvicorn.Server(config); server.install_signal_handlers=lambda:None; server.run()

def wait_ready(url,timeout=15):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=.5) as r:
                if r.status==200:return
        except Exception: time.sleep(.1)
    raise RuntimeError('Il server locale non è diventato disponibile.')

def check_update():
    if not UPDATE_MANIFEST_URL: return None
    try:
        req=urllib.request.Request(UPDATE_MANIFEST_URL,headers={'User-Agent':'AmigurumiAI'})
        with urllib.request.urlopen(req,timeout=5) as r: m=json.load(r)
        return validate_update_manifest(m, APP_VERSION)
    except Exception: return None

def start_update(info):
    latest,url,sha=info
    exe=Path(sys.executable).resolve().parent/'AmigurumiAI-Updater.exe'
    if not exe.exists(): return False
    subprocess.Popen([str(exe),url,sha,str(os.getpid())],close_fds=True)
    return True

def main():
    port=free_port(); threading.Thread(target=run_server,args=(port,),daemon=True).start(); wait_ready(f'http://127.0.0.1:{port}/api/health')
    info=check_update()
    if info and start_update(info):
        return
    window=webview.create_window('Amigurumi AI Designer',f'http://127.0.0.1:{port}/',width=1440,height=920,min_size=(1000,700),resizable=True)
    webview.start(debug=False)

if __name__=='__main__': main()
