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
    exists,
    startswith,
    CheckResult,
    CheckPlugin,
    SNMPSection,
)

def parse_lancom_vpn_licenses(string_table):
    if not string_table:
        return None
    result = {}
    result["licenses"] = int(string_table[0][0])
    result["licenses_used"] = int(string_table[0][1])
    return result

def discover_lancom_vpn_licenses(section) -> DiscoveryResult:
    if section["licenses"] > 0:
        yield Service()

def check_lancom_vpn_licenses(section) -> CheckResult:
    licenses = section["licenses"]
    licenses_used = section["licenses_used"]
    licenses_used_warn = 0.8 * licenses
    licenses_used_crit = 1.0 * licenses
    yield Result(state=State.OK, summary=f"VPN Licenses available: {licenses}")
    yield from check_levels(
        float(licenses_used),
        levels_upper=(licenses_used_warn, licenses_used_crit),
        metric_name="vpn_licenses_used",
        label="Licenses used",
        boundaries=(0.0, float(licenses))
    )

SNMPSection(
    name = "lancom_vpn_licenses",
    parse_function = parse_lancom_vpn_licenses,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2356.11.8"),
    fetch = SNMPTree(base='.1.3.6.1.4.1.2356.11.1.26', oids=['40.0', '44.0']),
)

CheckPlugin(
    name = "lancom_vpn_licenses",
    sections = ["lancom_vpn_licenses"],
    service_name = "LANCOM VPN Licenses",
    discovery_function = discover_lancom_vpn_licenses,
    check_function = check_lancom_vpn_licenses,
)
