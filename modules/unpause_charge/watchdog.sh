#!/system/bin/sh
# Persistent counter-measure for the FP8300 port charging bug: a system service
# keeps setting persist.sys.pause_charge=1 (observed every ~2-3s), which makes
# the charge service accept a charger for 1-3s and then suspend charging.
# Clear it every second. Quiet by design; writes a summary line every 30 min.
MODDIR=${0%/*}
LOG=/data/local/tmp/unpause_charge.log
MARK=$MODDIR/.wd.pid

if [ -f "$MARK" ] && kill -0 "$(cat $MARK 2>/dev/null)" 2>/dev/null; then
  echo "$(date) watchdog already running (pid $(cat $MARK))" >> "$LOG"
  exit 0
fi
echo $$ > "$MARK"

echo "$(date) watchdog start (uptime $(cat /proc/uptime))" >> "$LOG"
count=0
n=0
while true; do
  if [ "$(getprop persist.sys.pause_charge)" != "0" ]; then
    if command -v resetprop >/dev/null 2>&1; then
      resetprop persist.sys.pause_charge 0 2>/dev/null
    else
      setprop persist.sys.pause_charge 0 2>/dev/null
    fi
    count=$((count + 1))
  fi
  n=$((n + 1))
  if [ "$n" -ge 1800 ]; then
    echo "$(date) watchdog alive: cleared $count times in last 1800s (uptime $(cat /proc/uptime))" >> "$LOG"
    n=0
    count=0
  fi
  sleep 1
done
