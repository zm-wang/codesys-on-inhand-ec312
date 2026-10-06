#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Upload a local file to the EC312 via SFTP (paramiko).

Reads credentials from `cred.txt` (same format as ec312_ssh.py).
Note: the device's SFTP may be chrooted — if an absolute path like /tmp/x fails
with "No such file", use a path relative to the login home (e.g. just "x.deb").

Usage:  python ec312_upload.py <local_path> <remote_path>
"""
import sys, os, paramiko

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "cred.txt"), "r", encoding="utf-8") as f:
    lines = [l.rstrip("\n") for l in f.readlines()]
host, user, password = lines[0].strip(), lines[1].strip(), lines[2]
port = int(lines[3].strip()) if len(lines) > 3 and lines[3].strip() else 22

local, remote = sys.argv[1], sys.argv[2]
t = paramiko.Transport((host, port))
t.connect(username=user, password=password)
sftp = paramiko.SFTPClient.from_transport(t)
sftp.put(local, remote)
print("UPLOADED %s -> %s (%d bytes)" % (local, remote, os.path.getsize(local)))
sftp.close()
t.close()
