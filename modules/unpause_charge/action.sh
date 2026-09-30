#!/system/bin/sh
# Module action button: (re)start the watchdog without rebooting.
MODDIR=${0%/*}
LOG=/data/local/tmp/unpause_charge.log
echo "$(date) action pressed: (re)starting watchdog" >> "$LOG"
if [ -f "$MODDIR/.wd.pid" ]; then
  kill "$(cat "$MODDIR/.wd.pid" 2>/dev/null)" 2>/dev/null
  rm -f "$MODDIR/.wd.pid"
fi
pkill -f "unpause_charge/watchdog.sh" 2>/dev/null
sleep 1
if command -v setsid >/dev/null 2>&1; then
  setsid sh "$MODDIR/watchdog.sh" >/dev/null 2>&1 &
else
  nohup sh "$MODDIR/watchdog.sh" >/dev/null 2>&1 &
fi
sleep 2
if [ -f "$MODDIR/.wd.pid" ] && kill -0 "$(cat "$MODDIR/.wd.pid" 2>/dev/null)" 2>/dev/null; then
  echo "watchdog started (pid $(cat "$MODDIR/.wd.pid")). Charging should now hold. Log: /data/local/tmp/unpause_charge.log"
else
  echo "watchdog start FAILED - check $LOG"
fi
