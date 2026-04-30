#!/usr/bin/env bash
#
# Roll out the latest master to the deployed Pis. Run from a laptop on the
# same LAN as the Pis (typically the gallery network).
#
#   ./scripts/update_fleet.sh              # update every known tube
#   ./scripts/update_fleet.sh pwm1 pwm3    # update a subset
#
# For each target the script SSHes in and runs:
#
#   cd ~/cdf-plasma-controller && git pull && sudo make deploy
#
# Failures on one Pi are logged but do not abort the loop, so a bad host
# doesn't block the rest of the rollout.

set -u

SSH_USER="${SSH_USER:-pi}"
SSH_OPTS="${SSH_OPTS:--o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new}"

# Tube name → IP. Authoritative source is the comments in
# config/irobot.conf; mirror that here. When a new Pi gets added to the
# fleet, update both files.
declare -A TUBE_IPS=(
    [pwm1]=192.168.1.11
    [pwm2]=192.168.1.12
    [pwm3]=192.168.1.13
    [pwm4]=192.168.1.14
    # SC tubes — IPs not recorded in irobot.conf as of writing; fill in
    # before relying on this script for them.
    # [pwm5]=...
    # [pwm6]=...
    # [pwm7]=...
)

if [ "$#" -eq 0 ]; then
    targets=("${!TUBE_IPS[@]}")
else
    targets=("$@")
fi

failed=()
for tube in "${targets[@]}"; do
    ip="${TUBE_IPS[$tube]:-}"
    if [ -z "$ip" ]; then
        echo "[$tube] no IP configured; skipping" >&2
        failed+=("$tube")
        continue
    fi
    echo "===> [$tube] ${SSH_USER}@${ip}"
    if ssh ${SSH_OPTS} "${SSH_USER}@${ip}" \
        'cd ~/cdf-plasma-controller && git pull && sudo make deploy' \
        2>&1 | sed "s/^/[$tube] /"; then
        echo "[$tube] OK"
    else
        echo "[$tube] FAILED"
        failed+=("$tube")
    fi
done

if [ "${#failed[@]}" -ne 0 ]; then
    echo
    echo "Failed: ${failed[*]}" >&2
    exit 1
fi
