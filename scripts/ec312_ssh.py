#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run one command on the EC312 over SSH (password auth) using paramiko.

Why not plain ssh? On a Windows/Git-Bash host there is often no sshpass, so
password SSH can't be piped. paramiko handles it. Install with:  pip install paramiko

Credentials are read from `cred.txt` next to this script (git-ignored):
    line 1: host (e.g. 192.168.x.x)
    line 2: user (e.g. edge)
    line 3: password
    line 4: port (optional, default 22)

Usage:  python ec312_ssh.py "docker ps"
"""
import sys, os, paramiko

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "cred.txt"), "r", encoding="utf-8") as f:
    lines = [l.rstrip("\n") for l in f.readlines()]
host, user, password = lines[0].strip(), lines[1].strip(), lines[2]
port = int(lines[3].strip()) if len(lines) > 3 and lines[3].strip() else 22

cmd = sys.argv[1] if len(sys.argv) > 1 else "echo no-command"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(host, port=port, username=user, password=password,
                   timeout=15, allow_agent=False, look_for_keys=False)
except Exception as e:
    print("CONNECT_FAILED:", repr(e))
    sys.exit(2)

stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
out = stdout.read().decode("utf-8", "replace")
err = stderr.read().decode("utf-8", "replace")
rc = stdout.channel.recv_exit_status()
sys.stdout.write(out)
if err.strip():
    sys.stderr.write("\n[STDERR]\n" + err)
client.close()
sys.exit(rc)
