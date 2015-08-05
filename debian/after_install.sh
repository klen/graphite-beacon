#!/bin/bash

if [[ `/sbin/init --version` =~ upstart ]]; then start graphite-beacon;
elif [[ `systemctl` =~ -\.mount ]]; then systemctl start graphite-beacon;
elif [[ -f /etc/init.d/cron && ! -h /etc/init.d/cron ]]; then /etc/init.d/graphite-beacon start;
fi
