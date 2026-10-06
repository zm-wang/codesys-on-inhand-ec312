# CODESYS Control for Linux ARM64 SL runtime, containerized for an aarch64
# Debian edge gateway (e.g. InHand EC312).
#
# Base MUST be debian:12 (glibc 2.36) — the runtime needs glibc >= 2.34, and the
# typical EC312 host (Debian 11) only has glibc 2.31. Containers bring their own
# userspace, so debian:12 runs fine on the Debian-11 host kernel.
#
# You must supply the runtime .deb yourself (NOT redistributed in this repo):
# extract it from the "CODESYS Control for Linux ARM64 SL" package downloaded
# from the CODESYS Store, and place it next to this Dockerfile as:
#   codesyscontrol_linuxarm64_4.22.0.0_arm64.deb
#
# Build for arm64 (build ON the arm64 device, or use buildx --platform linux/arm64).

FROM debian:12-slim

ARG DEB=codesyscontrol_linuxarm64_4.22.0.0_arm64.deb
COPY ${DEB} /tmp/rt.deb

# Install runtime. --force-depends: we run the binary directly (no systemd in the
# container); the postinst detects the container and skips the daemon.
RUN dpkg -i --force-depends /tmp/rt.deb || true \
 && mkdir -p /var/opt/codesys \
 && rm -f /tmp/rt.deb

# --- DEMO / LEARNING ONLY: relax two security gates so a headless IDE login can
#     connect and download without interactive setup. DO NOT use in production. ---
# 1) Don't enforce device user management (else first headless login hangs on the
#    "create device user" prompt).
# 2) Allow unsigned application download (else download is denied).
RUN sed -i '/UserLogin_AuthenticationType/a SECURITY.UserMgmtEnforce=NO' \
        /etc/codesyscontrol/CODESYSControl_User.cfg \
 && sed -i 's/SECURITY.UnsignedApplicationFileTransfer=DENY/SECURITY.UnsignedApplicationFileTransfer=ALLOW/' \
        /etc/codesyscontrol/CODESYSControl_User.cfg

# Runtime listens on 11740 (programming). Run in foreground as the container PID.
CMD ["/opt/codesys/bin/codesyscontrol.bin", "/etc/codesyscontrol/CODESYSControl.cfg"]
