#!/bin/bash
PIDFILE=transmissionRobot.pid
if [ x"$1" = x-daemon ]; then
  if test -f "$PIDFILE"; then exit; fi
  echo $$ > "$PIDFILE"
  trap "rm '$PIDFILE'" EXIT SIGTERM ERR
  while true; do
    python2 transmissionRobot.py &> /dev/null
    wait 
  done
elif [ x"$1" = x-stop ]; then
  kill `cat "$PIDFILE"`
else
  nohup "$0" -daemon 
fi

