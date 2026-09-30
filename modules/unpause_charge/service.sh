#!/system/bin/sh
MODDIR=${0%/*}
while [ "$(getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
  sleep 2
done
if command -v setsid >/dev/null 2>&1; then
  setsid sh "$MODDIR/watchdog.sh" >/dev/null 2>&1 &
else
  nohup sh "$MODDIR/watchdog.sh" >/dev/null 2>&1 &
fi
