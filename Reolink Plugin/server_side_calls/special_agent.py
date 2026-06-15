#!/usr/bin/env python3

from collections.abc import Iterator
from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_arguments(params, host_config):
    yield SpecialAgentCommand(
        command_arguments=[
            "--host",     host_config.primary_ip_config.address,
            "--user",     params["user"],
            "--password", Secret(params["password"]),
            "--port",     str(params.get("port", 80)),
        ]
    )

special_agent_reolink = SpecialAgentConfig(
    name="reolink",
    commands_function=_agent_arguments,
)