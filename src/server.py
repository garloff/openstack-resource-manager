#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
import sys
import os

from dateutil import parser
from loguru import logger
import openstack
from oslo_config import cfg
from prompt_toolkit import prompt

default_cloud = os.getenv("OS_CLOUD") or "service"

PROJECT_NAME = "server"
CONF = cfg.CONF
opts = [
    cfg.BoolOpt("debug", help="Enable debug logging", default=False),
    cfg.StrOpt("cloud", help="Cloud name in clouds.yaml (defaults to OS_CLOUD env)", default=default_cloud),
]
CONF.register_cli_opts(opts)
CONF(sys.argv[1:], project=PROJECT_NAME)

if CONF.debug:
    level = "DEBUG"
else:
    level = "INFO"

log_fmt = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, format=log_fmt, level=level, colorize=True)


# Connect to the OpenStack environment
cloud = openstack.connect(cloud=CONF.cloud)

# build
for server in cloud.compute.servers(all_projects=True, status="build"):
    duration = datetime.now(timezone.utc) - parser.parse(server.created_at)
    if duration.total_seconds() > 7200:
        logger.info(f"Server {server.id} hangs in BUILD status for more than 2 hours")
        result = prompt(f"Delete server {server.id} [yes/no]: ")
        if result == "yes":
            logger.info(f"Deleting server {server.id}")
            cloud.compute.delete_server(server.id, force=True)

# error
for server in cloud.compute.servers(all_projects=True, status="error"):
    logger.info(f"Server {server.id} ({server.name}) is in ERROR status")
    result = prompt(f"Delete server {server.id} [yes/no]: ")
    if result == "yes":
        logger.info(f"Deleting server {server.id}")
        cloud.compute.delete_server(server.id, force=True)
