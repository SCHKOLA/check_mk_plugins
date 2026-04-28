#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) 2023 Niklas Merkelt <niklasmerkelt@mail.de>

# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from .agent_based_api.v2 import (
    check_levels,
    CheckParameters,
    DiscoveryResult,
    Result,
    Service,
    SNMPTree,
    State,
    render,
    exists,
    startswith,
    CheckResult,
    CheckPlugin,
    SNMPSection,
)

def _map_connection_state(state):
    state_map = {
        0: "Init",
        1: "SetupWan",
        2: "Ready",
        3: "WaitForCb",
        4: "Dial",
        5: "IncommingCall",
        6: "Protocol",
        7: "Connection",
        8: "Disconnecting",
        9: "CallBack",
        10: "BundleConnect",
        11: "Protocol2",
        12: "Reserved",
        13: "Bundle"
    }
    return state_map.get(state, "Unknown State")

def parse_lancom_vpn_connection(string_table):
    if not string_table:
        return None
    section = {}
    for connection in string_table:
        section[connection[0]] = {
            'name': connection[0],
            'state': int(connection[1]),
            'connection_time': int(connection[2]),
            #'rx_bytes': int(connection[3]),
            #'tx_bytes': int(connection[4]),
        }
    return section

def discover_lancom_vpn_connection(section) -> DiscoveryResult:
    for item, data in section.items():
        yield Service(item=item)

def check_lancom_vpn_connection(item, section) -> CheckResult:
    if item in section:
        data = section[item]
        yield Result(state=State.OK, summary=data['name'])
        if data['state'] != 7:
            yield Result(state=State.WARN, summary=_map_connection_state(data['state']))
        yield from check_levels(
            data['connection_time'],
            metric_name='uptime',
            render_func=render.timespan,
            label='Uptime',
        )

SNMPSection(
    name = "lancom_vpn_connection",
    parse_function = parse_lancom_vpn_connection,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2356.11.8"),
    fetch = SNMPTree(
        base='.1.3.6.1.4.1.2356.11.1.26.17.1',
        oids=[
            '1',  # Name
            '11', # State
            '19', # ConnectionTime
            #'24', # RxBytes
            #'25', # TxBytes
        ],
    ),
)

CheckPlugin(
    name = "lancom_vpn_connection",
    sections = ["lancom_vpn_connection"],
    service_name = "VPN Connection %s",
    discovery_function = discover_lancom_vpn_connection,
    check_function = check_lancom_vpn_connection,
)
