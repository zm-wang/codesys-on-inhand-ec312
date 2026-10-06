# Lessons learned / gotchas

The non-obvious things that cost time during this bring-up. Written for the next
human or AI agent doing CODESYS-on-ARM64-Docker.

## Runtime / Docker

- **glibc version**: the official `codesyscontrol` 3.5.22.30 `.deb` depends on
  `libc6 >= 2.34`. Debian 11 (the EC312 host) ships glibc 2.31 → the binary won't
  run on the host userspace. Fix: containerize on **debian:12-slim** (glibc 2.36).
  Containers share the host kernel but have their own userspace, so this is fine.
- **host network + privileged**: the runtime needs `--network host --privileged`
  so it can bind 11740 on the device IP and touch host device resources. With host
  networking the container's listening ports show up in the *host* `/proc/net/tcp`
  (11740 = hex `2DDC`).
- **First-boot delay**: on first start the runtime generates an asymmetric key
  ("Create asymmetric key..."). Until it finishes, 11740 isn't listening. Allow
  ~15–30 s (sometimes longer on a busy/low-entropy device) before deciding it failed.
- **CodeMeter errors are harmless** in demo mode ("CodeMeter access denied" →
  "no runtime license - running in demo mode"). Demo = 2 hours per start, then
  `**** ERROR: demo mode expired` and the app stops. `docker restart <name>` resumes.
- **Boot application persists across `docker restart`** (not across re-create
  unless you volume-mount `/var/opt/codesys` + `/PlcLogic`). If a boot project was
  created, the runtime reloads it on restart ("Bootproject ... loaded").
- Runtime log inside the container: `/codesyscontrol.log` (not `docker logs`).

## Runtime security (why headless login hung)

The official runtime config enforces, by default:
- `[CmpUserMgr] SECURITY.UserLogin_AuthenticationType=ONLY_ASYMMETRIC` + enforced
  user management → on first connect the IDE must interactively create a device
  user. A **headless** (`--noUI`) login just **hangs** on this prompt.
- `[CmpApp] SECURITY.UnsignedApplicationFileTransfer=DENY` → download refused.

For a demo/learning box, relax both in `CODESYSControl_User.cfg`:
```
[CmpUserMgr]
SECURITY.UserMgmtEnforce=NO
[CmpApp]
SECURITY.UnsignedApplicationFileTransfer=ALLOW
```
**Never do this on a production controller.**

## Version matching (IDE ↔ runtime)

The project's device version must match the runtime. IDE 3.5.22 pairs with the
**4.22.0.0** SL package (runtime reports `3.5.22.30`). A mismatch shows at login:
`The device in the project does not match ... in project=4.22.0.0, in target
device=4.9.0.0`. The public Hilscher Docker image
(`hilschernetiotedge/codesys_control_sl_linux`) is handy for a no-account demo but
was stuck at 4.9 — so we switched to the official 4.22 `.deb` to match the IDE.

## Installing the device description without admin

`APInstaller.CLI --installAddOnFromFile` writes into `Program Files` → needs
elevation (UAC). To avoid UAC, import the device description into the **user**
device repository via the scripting engine:
`device_repository.import_device(devdesc_path, device_repository.sources[0])`
(`sources[0]` = "System Repository" at `C:\ProgramData\CODESYS\Devices`, writable).

## Headless CODESYS scripting (`CODESYS.exe --runscript`)

- `--noUI` **requires** `--profile="CODESYS V3.5 SP22 Patch 4"` (exact profile name;
  find it via `APInstaller.CLI --getInstallations`, field `ProfileFiles`).
- **PowerShell 5.1 arg mangling**: passing `--profile="..."` directly to the exe
  loses the value (spaces). Pass the whole tail as ONE string to
  `Start-Process -ArgumentList '--profile="..." --noUI --runscript="..."'`.
- The scripting Python is **IronPython 2.7**; globals injected include `projects`,
  `device_repository`, `online`, `system`, `PouType`, `KindOfTask`,
  `OnlineChangeOption`.
- `proj.add("Device", 4096, "0000 0007", "4.22.0.0")` returns `None` but *does* add
  the device. Navigate the tree with `get_children()` recursively.
- Project build structure to add by hand: `app.create_pou(name, PouType.Program)`
  → `pou.textual_declaration/textual_implementation.replace(new_text=...)`;
  `app.create_task_configuration().create_task("MainTask")`,
  `task.kind_of_task = KindOfTask.Cyclic`, `task.pous.add("PLC_PRG")`.
- Gateway: `online.gateways.add_new_gateway(name, {"IP-Address":"localhost"},
  online.gateway_drivers.default_driver)` then
  `device.set_gateway_and_ip_address(gw, "<EC312_IP>", 11740)`.
- Download + run: `oa = online.create_online_application(app);
  oa.login(OnlineChangeOption.Never, True); oa.start()`. Read live values with
  `oa.read_value("PLC_PRG.nCounter")`.

### Reading compile errors from a headless build

`app.build()` is incremental and `system.get_messages()` defaults to the
*ScriptMessage* category → you see **0** messages even when a build fails. To get
the real compiler errors:
```python
COMPILE_CAT = "{97F48D64-A2A3-4856-B640-75C046E37EA9}"
app.clean(); app.generate_code()
errs = [m for m in system.get_message_objects(COMPILE_CAT)
        if str(m.severity) in ("Error", "FatalError")]
```

## The limitation we hit: libraries in scripted projects

A project created purely via `projects.create()` built & ran fine for
**pure-operator** code (the counter). But any program using **library** symbols
(`TON`, `CONCAT`, `LEN`, `NBS.*` from Net Base Services) failed with
`Unknown type: 'TON'` / `Identifier 'CONCAT' not defined`, **even after**
`add_library(...)` (the libs showed in the Library Manager) and save+reopen.

Likely cause: the GUI "Standard Project" wizard sets up a compiler-version /
library-resolution context that scripted creation doesn't, and the fixing API
(`set_compilerversion_to_newest`, added in scripting API 4.2.0.0) isn't present in
the 3.5.22 scripting engine. The practical workaround was to create/finalize a
library-dependent project **in the IDE GUI once**; pure-operator programs deploy
fully headless. If you solve the headless library-resolution, please send a PR.
