#!/system/bin/sh
PK=com.miui.powerkeeper
if pm list packages -d | grep -q "$PK"; then
  pm enable "$PK"
  echo "=== 已切到【日常模式】: PowerKeeper 已启用"
  echo "性能模式/省电模式开关恢复可用; 三角洲等游戏会被云端策略压回 60 帧。"
  echo "打游戏前再点一次本按钮切回高帧模式。"
else
  pm disable-user --user 0 "$PK"
  echo "=== 已切到【高帧模式】: PowerKeeper 已禁用"
  echo "三角洲等游戏恢复 165 帧; 性能/省电模式开关暂时不可用。"
  echo "想用性能模式时再点一次本按钮切回。"
fi
