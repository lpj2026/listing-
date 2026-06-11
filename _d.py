import os, sys, time, urllib.request, json, paramiko
B = os.path.dirname(os.path.abspath(__file__))
F = ["backend/attribute_presets.py", "backend/schema_service.py", "frontend/app.js", "frontend/index.html"]
pw = os.environ.get("REMOTE_SSH_PASSWORD", "")
if pw:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("8.137.177.25", username="root", password=pw, timeout=20)
    s = c.open_sftp()
    for f in F:
        s.put(os.path.join(B, f.replace("/", os.sep)), f"/opt/product-listing/{f}")
    s.close()
    c.exec_command("sed -i 's/\\r$//' /opt/product-listing/scripts/server_start.sh")
    c.exec_command("pkill -f '/opt/product-listing/backend/app.py' || true")
    c.exec_command("cd /opt/product-listing && setsid bash scripts/server_start.sh > logs/app.log 2>&1 &")
    time.sleep(3)
    c.close()
    print("deployed")
d = json.loads(urllib.request.urlopen("http://127.0.0.1:8001/api/schema?product_type=AUTO_PART", timeout=20).read())
f = next(x for x in d["attributes"] if x.get("key") == "exterior_finish")
print("type", f["type"], "options", len(f.get("options", [])), [o["label"] for o in f.get("options", [])])
