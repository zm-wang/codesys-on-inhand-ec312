# CODESYS scripting-engine script: create a project, add the ARM64 SL device,
# write a tiny ST counter into PLC_PRG, set the gateway/IP to the EC312, build,
# download and start -- fully headless.
#
# Run:
#   CODESYS.exe --profile="CODESYS V3.5 SP22 Patch 4" --noUI --runscript="deploy_counter.py"
#
# Notes learned the hard way:
#  * proj.add("Device", 4096, "0000 0007", "4.22.0.0") returns None but DOES add
#    the device (with Plc Logic -> Application -> Library Manager). Find nodes by
#    walking get_children() recursively.
#  * Pass CODESYS.exe args as ONE quoted string via PowerShell Start-Process
#    -ArgumentList, e.g.  '--profile="..." --noUI --runscript="..."' -- Windows
#    PowerShell 5.1 otherwise mangles the --profile value (spaces).
#  * The device description (import_device_description.py) must be installed first.
#  * A local CODESYS Gateway service must be running (installed with the IDE).
#  * This counter uses ONLY operators/IF -> no library needed, so it builds & runs
#    headlessly. Library-dependent programs did not resolve symbols headlessly
#    (see docs/lessons-learned.md).

EC312_IP = "192.168.1.100"                         # <-- EDIT: the EC312's IP (programming path)
PROJ     = r"C:\Temp\EC312_Test.project"           # <-- EDIT
RESULT   = r"C:\Temp\cds_result.txt"
import os

def log(m):
    with open(RESULT, "a") as f:
        f.write(str(m) + "\n")
open(RESULT, "w").close()

def kids_of(o):
    try: return list(o.get_children())
    except Exception: return []

def find_by_name(root, target):
    for k in kids_of(root):
        try:
            if k.get_name() == target: return k
        except Exception: pass
        r = find_by_name(k, target)
        if r is not None: return r
    return None

if os.path.exists(PROJ): os.remove(PROJ)
proj = projects.create(PROJ)
proj.add("Device", 4096, "0000 0007", "4.22.0.0")  # CODESYS Control for Linux ARM64 SL
device = find_by_name(proj, "Device")
app    = find_by_name(proj, "Application")

# PLC_PRG: a simple counter (pure operators -> no library dependency)
pou = app.create_pou("PLC_PRG", PouType.Program)
pou.textual_declaration.replace(new_text=
    "PROGRAM PLC_PRG\nVAR\n\tnCounter : INT := 0;\n\tbToggle : BOOL := FALSE;\nEND_VAR")
pou.textual_implementation.replace(new_text=
    "nCounter := nCounter + 1;\nIF nCounter >= 1000 THEN\n\tnCounter := 0;\n\tbToggle := NOT bToggle;\nEND_IF")

# Task: cyclic 20 ms calling PLC_PRG
tc = app.create_task_configuration()
task = tc.create_task("MainTask")
task.kind_of_task = KindOfTask.Cyclic
task.interval = "20"; task.interval_unit = "ms"; task.priority = "10"
task.pous.add("PLC_PRG")

# Gateway (local service) + target IP:11740
gw = None
for g in online.gateways:
    gw = g; break
if gw is None:
    drv = online.gateway_drivers.default_driver
    params = {}
    for pd in drv.gateway_parameters:
        low = pd.name.lower()
        if "address" in low or ("ip" in low and "port" not in low):
            params[pd.name] = "localhost"
    gw = online.gateways.add_new_gateway("LocalGateway", params, drv)
device.set_gateway_and_ip_address(gw, EC312_IP, 11740)

app.build()
log("BUILT")

oa = online.create_online_application(app)
oa.login(OnlineChangeOption.Never, True)   # full download
oa.start()
log("DOWNLOADED_AND_STARTED is_logged_in=" + str(oa.is_logged_in))
oa.logout()
proj.save()
log("DONE")
