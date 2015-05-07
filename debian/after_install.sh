#!/bin/sh

ps -eaf | grep [u]pstart && start graphite-beacon
ps -eaf | grep [s]ystemd && systemctl start graphite-beacon
