#!/system/bin/sh
# Runs early on every boot with root. The persist.sys.pause_charge flag is a
# latched "suspend charging" state: when set to 1, the charge service accepts a
# newly plugged charger for 1-3 seconds and then suspends charging, leaving the
# device net-discharging. It persists across reboots via the persist property
# file, and the settings-layer bypass_charge_state does not control it.
if command -v resetprop >/dev/null 2>&1; then
  resetprop persist.sys.pause_charge 0
else
  setprop persist.sys.pause_charge 0
fi
