#!/bin/bash

if [[ `/sbin/init --version` =~ upstart ]]; then stop graphite-beacon;
elif [[ `systemctl` =~ -\.mount ]]; then systemctl stop graphite-beacon;
elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/graphite-beacon stop;
fi

