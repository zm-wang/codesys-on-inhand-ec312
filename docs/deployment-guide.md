# Deployment guide (end to end)

Full sequence to go from a bare EC312 + a Windows PC to a program running on the
EC312, deployed headlessly. Replace `<EC312_IP>` with your device IP.

## 0. Prerequisites

- CODESYS Development System 3.5.22 installed on Windows.
- CODESYS account; from the **international** store (`store.codesys.com`) download
  **CODESYS Control for Linux ARM64 SL** (free). Extract the `.package` (it's a zip):
  - device description: `Devices/AddOns/.../linuxarm64/<ver>/codesyscontrol.devdesc.xml`
  - runtime: `Delivery/linuxarm64/codesyscontrol_linuxarm64_4.22.0.0_arm64.deb`
- SSH to the EC312 (`edge` user, in the `docker` group).
- `pip install paramiko` on the PC (for the SSH/upload helpers).

## 1. Build the runtime container on the EC312

Copy `docker/` + the `.deb` to the device (e.g. with `scripts/ec312_upload.py`), then:

```bash
# on the EC312
docker build -t codesyscontrol:4.22 ./docker
docker run -d --name cds422 --restart unless-stopped \
    --network host --privileged codesyscontrol:4.22
sleep 20
grep -i 2DDC /proc/net/tcp && echo "11740 listening"   # 2DDC = 11740
docker exec cds422 sh -c 'grep -iE "ready|demo mode" /codesyscontrol.log | tail -2'
```

Expected: `CODESYS Control ready` and `running in demo mode(~2 hours)`.

## 2. Install the device description into the IDE (no admin)

Find your profile name:
```powershell
& "C:\Program Files (x86)\CODESYS\APInstaller\APInstaller.CLI.exe" --getInstallations
# -> ProfileFiles: "...\CODESYS V3.5 SP22 Patch 4.profile.xml"
```
Edit `scripts/import_device_description.py` (`DEVDESC` = the extracted
`codesyscontrol.devdesc.xml`), then:
```powershell
& "C:\Program Files\CODESYS 3.5.22.40\CODESYS\Common\CODESYS.exe" `
  --profile="CODESYS V3.5 SP22 Patch 4" --noUI `
  --runscript="...\scripts\import_device_description.py"
```
Check `C:\Temp\cds_result.txt` for `IMPORT_OK`.

## 3. Deploy a program (headless)

Edit `scripts/deploy_counter.py` (`EC312_IP`, `PROJ`), then run it the same way
(`CODESYS.exe --profile=... --noUI --runscript=...`). It creates the project, adds
the device, writes a counter, sets the gateway, builds, downloads and starts.

> Only pure-operator programs deploy reliably headless. For library-dependent
> programs (timers, strings, networking), create/finalize the project in the IDE
> GUI — see [lessons-learned.md](lessons-learned.md).

## 4. Verify from the device side

```bash
docker exec cds422 sh -c 'grep -i "loaded via \[Download\]" /codesyscontrol.log | tail -1'
docker exec cds422 sh -c 'ls -la /PlcLogic/Application/'   # Application.app present
```
Or read a live value from the IDE script:
`oa.read_value("PLC_PRG.nCounter")` — call twice; it should increment.

## 5. Connect the IDE GUI (optional, to watch live)

Open the generated `.project`, **Login (Alt+F8)**, watch variables in a Watch
window. Gateway is already set to `<EC312_IP>:11740`.

## Operations

- **Resume after demo expiry**: `docker restart cds422`.
- **Fresh runtime (clears app)**: `docker rm -f cds422 && docker run ...`.
- **Persist app/retains across re-create**: volume-mount `/var/opt/codesys` and
  `/PlcLogic` (see commented lines in `docker/docker-compose.yml`).
- **Create a boot application** (auto-start on restart): in the IDE, Online →
  Create Boot Application while logged in.
