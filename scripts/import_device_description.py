# CODESYS scripting-engine script: import the "CODESYS Control for Linux ARM64 SL"
# device description into the USER-level device repository -- no admin / UAC needed.
#
# Why this instead of the APInstaller CLI? `APInstaller.CLI --installAddOnFromFile`
# installs into the Program Files installation and requires elevation (UAC). The
# scripting engine imports straight into the user repository (C:\ProgramData\
# CODESYS\Devices) without admin.
#
# 1) Download "CODESYS Control for Linux ARM64 SL" (.package) from the CODESYS Store.
# 2) A .package is a zip; extract it and find:
#      Devices/AddOns/CODESYS Control for Linux ARM64 SL/linuxarm64/<ver>/codesyscontrol.devdesc.xml
# 3) Set DEVDESC below to that path.
# 4) Run:
#    CODESYS.exe --profile="CODESYS V3.5 SP22 Patch 4" --noUI --runscript="import_device_description.py"
#
# Results are written to RESULT so you can read them from outside the headless run.

DEVDESC = r"C:\path\to\extracted\...\linuxarm64\4.22.0.0\codesyscontrol.devdesc.xml"  # <-- EDIT
RESULT  = r"C:\Temp\cds_result.txt"                                                   # <-- optional

def log(m):
    with open(RESULT, "a") as f:
        f.write(str(m) + "\n")
open(RESULT, "w").close()

# `device_repository` is a global injected by the CODESYS scripting engine.
src = device_repository.sources[0]          # [0] = "System Repository" (ProgramData, user-writable)
did = device_repository.import_device(DEVDESC, src)
log("IMPORT_OK: " + str(did))
found = device_repository.get_all_devices("Linux ARM64", None)
log("FOUND_BY_NAME_COUNT: " + str(len(found)))
