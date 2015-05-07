#!/bin/sh

ps -eaf | grep [u]pstart && stop graphite-beacon
ps -eaf | grep [s]ystemd && systemctl stop graphite-beacon
