#!/system/bin/sh
MODDIR=${0%/*}
(
  while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 2
  done
  sleep 20
  retry() {
    n=0
    while [ $n -lt 8 ]; do
      setprop "$1" "$2" && return 0
      n=$((n+1))
      sleep 2
    done
    return 1
  }
  for p in persist.sys.smartpower.limit.max.refresh.rate persist.sys.smartpower.limit.normal.max.refresh.rate.support; do
    cur=$(getprop $p)
    if [ "$cur" = "165" ]; then
      retry $p 166
    fi
    retry $p 165
  done
  settings put system peak_refresh_rate 165.0
  settings put system min_refresh_rate 165.0
  settings put secure user_refresh_rate 165
  settings put secure miui_refresh_rate 165
  cmd display set-user-preferred-display-mode 1904 3040 165
) &
