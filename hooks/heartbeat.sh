#!/bin/bash
# Periodic heartbeat check — add to crontab: */5 * * * *
autoshorts pipeline heartbeat >> data/logs/heartbeat.log
