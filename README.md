# CODESYS Control Runtime on InHand EC312 (Docker, ARM64)

Run the **CODESYS Control SL** PLC runtime inside **Docker** on an **InHand EC312**
edge gateway (aarch64 / Debian 11), and deploy + download + run IEC 61131-3
programs to it from the CODESYS Development System — **fully headless**, driven by
the IDE's command-line scripting engine (no manual clicking in the IDE).

This repo is the cleaned-up, reproducible writeup of a real end-to-end bring-up,
shared for anyone (human or AI agent) doing the same on an ARM64 Linux edge device.

> ⚠️ **Demo / learning setup, not production.** The runtime runs unlicensed
> (CODESYS *demo mode*: 2 hours per start) and the container deliberately relaxes
> two runtime security settings (see [Caveats](#caveats)). Do **not** copy the
> security relaxation onto a production controller.

---

## Target environment (verified)

| Component | Value |
|-----------|-------|
| Device | InHand **EC312** (device-tree model `LG312`) |
| OS | Debian GNU/Linux 11 (bullseye) |
| Kernel / Arch | 5.10.x / **aarch64 (ARM64)** |
| Docker | 24.0.6 |
| Runtime | CODESYS Control for Linux ARM64 SL **3.5.22.30** (SL package 4.22.0.0) |
| IDE | CODESYS Development System **3.5.22.40** (Windows) |

The runtime binary needs **glibc ≥ 2.34**, which Debian 11 (glibc 2.31) does *not*
provide — so the container base is **`debian:12-slim`** (glibc 2.36). Containers
share the host kernel but bring their own userspace, so this is fine on the
Debian-11 host.

---

## Architecture

```
  Windows PC (engineering)                 InHand EC312 (execution)
┌──────────────────────────┐           ┌──────────────────────────────┐
│ CODESYS IDE 3.5.22        │  gateway  │ Docker container "cds422"     │
│  + Linux ARM64 device desc │  :1217    │  (debian:12 + Control SL)     │
│  + CLI scripting engine    │──────────▶│  codesyscontrol.bin           │
│  (CODESYS.exe --runscript) │  :11740   │  --network host --privileged  │
└──────────────────────────┘  download  │  listens on :11740 (+ :1217)  │
                                         └──────────────────────────────┘
```

The container runs with `--network host --privileged`, so the runtime's
programming port **11740** is reachable on the EC312's own IP. The IDE connects
through its local CODESYS gateway (localhost:1217) out to `<EC312_IP>:11740`.

---

## Prerequisites

1. **CODESYS Development System 3.5.22** on Windows (free, needs a free CODESYS
   account; use the international store `store.codesys.com` — the US store only
   serves US/CA/MX).
2. **CODESYS Control for Linux ARM64 SL** package downloaded from the CODESYS
   Store (free, demo mode). It is a `.package` (zip) that contains:
   - `Devices/AddOns/.../codesyscontrol.devdesc.xml` → the IDE **device description**
   - `Delivery/linuxarm64/codesyscontrol_linuxarm64_4.22.0.0_arm64.deb` → the **runtime**
3. SSH access to the EC312 (user in the `docker` group so `docker` works without `sudo`).
4. The EC312 able to reach the internet (to `docker pull debian:12-slim`), or
   side-load the image.

> **Vendor binaries are not redistributed here.** You must download the CODESYS
> package yourself; the `.deb` / `.package` are git-ignored.

---

## Quickstart

### 1. Build & run the runtime container on the EC312

Put `codesyscontrol_linuxarm64_4.22.0.0_arm64.deb` (extracted from the SL package)
next to [`docker/Dockerfile`](docker/Dockerfile), copy the folder to the EC312, then:

```bash
docker build -t codesyscontrol:4.22 ./docker
docker run -d --name cds422 --restart unless-stopped \
    --network host --privileged \
    codesyscontrol:4.22
# first boot generates an asymmetric key — wait ~15-30s, then:
grep -i 2DDC /proc/net/tcp && echo "runtime listening on 11740"
```

(2DDC = 11740 in hex.) See [docker/](docker/) for a `docker-compose.yml` too.

### 2. Install the device description into the IDE (no admin needed)

The APInstaller CLI needs admin to write into `Program Files`; instead import the
device description straight into the user-level device repository via the IDE's
scripting engine — see [`scripts/import_device_description.py`](scripts/import_device_description.py).

### 3. Deploy a program headlessly from the IDE

[`scripts/deploy_counter.py`](scripts/deploy_counter.py) creates a project, adds
the ARM64 device, writes a tiny ST counter, sets the gateway to `<EC312_IP>:11740`,
builds, downloads and starts it — all headless:

```powershell
& "C:\Program Files\CODESYS 3.5.22.40\CODESYS\Common\CODESYS.exe" `
  --profile="CODESYS V3.5 SP22 Patch 4" --noUI `
  --runscript="...\scripts\deploy_counter.py"
```

Verify from the device side (`docker exec cds422 ...`): the runtime log shows
`Application loaded via [Download]` and `/PlcLogic/Application/Application.app` exists.

---

## Repo structure

```
docker/        Dockerfile + compose to build/run the runtime container
scripts/       SSH helper + CODESYS headless scripting examples
docs/          detailed guide + lessons-learned (the gotchas)
```

## Caveats

- **Demo mode**: unlicensed runtime stops every 2 h; `docker restart cds422` to resume.
- **Relaxed security (demo only)** in `CODESYSControl_User.cfg`:
  `[CmpUserMgr] SECURITY.UserMgmtEnforce=NO` (otherwise a headless login hangs on
  the first-login user-creation prompt) and
  `[CmpApp] SECURITY.UnsignedApplicationFileTransfer=ALLOW` (otherwise downloads
  are denied). **Never ship this on a real controller.**
- **Headless library limitation**: projects created purely via scripting compiled
  fine for pure-operator code, but programs that pull in libraries (timers,
  string functions, Net Base Services) failed to resolve library symbols. Building
  a library-dependent project reliably still needed the IDE GUI. See
  [docs/lessons-learned.md](docs/lessons-learned.md).

## Credits

Brought up collaboratively with Claude (Anthropic). Shared so the next
person/agent doesn't have to rediscover the same gotchas.

## License

MIT — see [LICENSE](LICENSE). Note: the CODESYS runtime, device description and
libraries are **not** covered by this license and are **not** included here;
obtain them from the CODESYS Store under their terms.
