#!/usr/bin/env python3
import json
import os
import paramiko

HOST = "8.137.177.25"
PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
APP_ID = os.environ.get("LINGXING_APP_ID", "")
APP_SECRET = os.environ.get("LINGXING_APP_SECRET", "")

REMOTE = r"""
import base64, hashlib, json, time, urllib.parse, requests
from Crypto.Cipher import AES
APP_ID="__APP_ID__"; SECRET="__APP_SECRET__"; BASE="https://openapi.lingxing.com"
SID=12518; MARKETPLACE="ATVPDKIKX0DER"; SELLER="AUF98RFGA31T9"

def aes_encrypt(text, key):
    c = AES.new(key.encode(), AES.MODE_ECB)
    d = text.encode(); p = 16-len(d)%16; d += bytes([p])*p
    return base64.b64encode(c.encrypt(d)).decode()
def sign(params):
    parts=[]
    for k in sorted(params):
        v=params[k]
        if isinstance(v,(dict,list)): v=json.dumps(v,ensure_ascii=False,separators=(',',':'))
        else: v=str(v)
        parts.append('%s=%s'%(k,v))
    return aes_encrypt(hashlib.md5('&'.join(parts).encode()).hexdigest().upper(), APP_ID)
def get_token():
    u=BASE+'/api/auth-server/oauth/access-token?appId='+APP_ID+'&appSecret='+urllib.parse.quote(SECRET)
    d=requests.post(u,timeout=30).json()
    return d['data']['access_token']
def call(path, body):
    t=get_token(); ts=str(int(time.time()))
    q={'app_key':APP_ID,'access_token':t,'timestamp':ts}
    sp=dict(q); sp.update(body); q['sign']=sign(sp)
    r=requests.post(BASE+path, params=q, json=body, timeout=60)
    try: return r.json()
    except: return {'raw': r.text[:300]}

tests = []
param_variants = [
    {'sid': SID},
    {'store_id': SID},
    {'storeId': SID},
    {'sid': SID, 'marketplace_id': MARKETPLACE},
    {'store_id': SID, 'marketplace_id': MARKETPLACE},
]
for body in param_variants:
    resp = call('/basicOpen/openapi/publish/manage/categoryRoot', body)
    tests.append({'api':'categoryRoot','body':body,'code':resp.get('code'),'msg':resp.get('msg'),'count':len(resp.get('data') or []) if isinstance(resp.get('data'),list) else resp.get('data')})

# publish list with store_id
resp = call('/listing/publish/openapi/amazon/product/list', {'store_id': SID, 'offset':0, 'length':3})
tests.append({'api':'publish-list','code':resp.get('code'),'msg':resp.get('msg'),'data':resp.get('data')})

# search existing - need sellerId marketplaceId mskus
resp = call('/listing/publish/openapi/amazon/product/search', {'sellerId': SELLER, 'marketplaceId': MARKETPLACE, 'mskus': ['MLYR-US-230722-0828']})
tests.append({'api':'product-search','code':resp.get('code'),'msg':resp.get('msg'),'data':resp.get('data')})

print(json.dumps(tests, ensure_ascii=False, indent=2))
"""

script = REMOTE.replace("__APP_ID__", APP_ID).replace("__APP_SECRET__", APP_SECRET)
client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username='root', password=PASSWORD, timeout=15)
sftp = client.open_sftp()
with sftp.file('/tmp/lx_pub2.py','w') as f: f.write(script)
sftp.close()
_, stdout, _ = client.exec_command('python3 /tmp/lx_pub2.py', timeout=120)
print(stdout.read().decode('utf-8','replace'))
client.close()
