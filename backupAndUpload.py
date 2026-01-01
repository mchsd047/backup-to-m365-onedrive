#!/usr/bin/env python3
import os, sys, json, tarfile, time, requests
from datetime import datetime, timedelta, timezone
from msal import ConfidentialClientApplication

# --- config (oder lade aus config.json) ---
CONFIG = {
  "client_id":"YOUR_CLIENT_ID",
  "client_secret":"YOUR_CLIENT_SECRET",
  "tenant_id":"common",
  "backup_sources":[
    "/opt/mosquitto/config/mosquitto.conf",
    "/opt/nginxproxymanager/nginx/"
    ],
  "onedrive_folder":"/Backups/Ubuntu",
  "archive_prefix":"pi1-backup",
  "keep_days":30
}

AUTHORITY = f"https://login.microsoftonline.com/{CONFIG['tenant_id']}"
SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH = "https://graph.microsoft.com/v1.0"

def get_token():
    app = ConfidentialClientApplication(CONFIG['client_id'], authority=AUTHORITY, client_credential=CONFIG['client_secret'])
    result = app.acquire_token_silent(SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def make_archive():
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{CONFIG['archive_prefix']}-{ts}.tar.gz"
    with tarfile.open(name,"w:gz") as tar:
        for src in CONFIG['backup_sources']:
            tar.add(src, arcname=os.path.basename(src))
    return name

def upload_file(token, local_path, remote_path):
    url = f"{GRAPH}/me/drive/root:{remote_path}:/content"
    headers = {"Authorization":f"Bearer {token}"}
    with open(local_path,"rb") as f:
        r = requests.put(url, headers=headers, data=f)
    r.raise_for_status()
    return r.json()

def delete_old_backups(token):
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONFIG['keep_days'])
    url = f"{GRAPH}/me/drive/root:{CONFIG['onedrive_folder']}:/children"
    headers = {"Authorization":f"Bearer {token}"}
    r = requests.get(url, headers=headers); r.raise_for_status()
    for item in r.json().get("value",[]):
        created = datetime.fromisoformat(item['createdDateTime'].replace('Z','+00:00')).astimezone(timezone.utc)
        if created < cutoff and item['name'].startswith(CONFIG['archive_prefix']):
            del_url = f"{GRAPH}/me/drive/items/{item['id']}"
            requests.delete(del_url, headers=headers)

def ensure_remote_folder(token):
    # create folder if not exists (simple attempt)
    path = CONFIG['onedrive_folder']
    url = f"{GRAPH}/me/drive/root:{path}"
    headers = {"Authorization":f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code==404:
        parent = os.path.dirname(path) or "/"
        name = os.path.basename(path)
        create_url = f"{GRAPH}/me/drive/root:{parent}:/children"
        body = {"name":name,"folder":{}}
        requests.post(create_url, headers={**headers,"Content-Type":"application/json"}, json=body).raise_for_status()

def main():
    #token = get_token()
    #ensure_remote_folder(token)
    archive = make_archive()
    #remote = f"{CONFIG['onedrive_folder']}/{archive}"
    #upload_file(token, archive, remote)
    #delete_old_backups(token)
    print("Backup complete:", archive)

if __name__=="__main__":
    main()
