#!/usr/bin/env python3
"""
CheckMK Agent-Based Check Plugin für Reolink Kameras.
Erzeugt folgende Services:
  - Reolink HDD <index>   → CRIT wenn nicht montiert/formatiert; WARN ab 85% voll
  - Reolink Performance   → WARN ab 80% CPU, CRIT ab 95%
  - Reolink Info          → zeigt Firmware/Modell
  - Reolink Recording     → CRIT wenn Aufnahme deaktiviert, WARN wenn Zeitplan aus
"""

import json
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    render,
)


def parse_reolink_hdd(string_table: StringTable) -> dict:
    try:
        return json.loads(string_table[0][0])
    except Exception:
        return {}


agent_section_reolink_hdd = AgentSection(
    name="reolink_hdd",
    parse_function=parse_reolink_hdd,
)


def discover_reolink_hdd(section: dict) -> DiscoveryResult:
    if not section.get("ok"):
        return
    for disk in section.get("disks", []):
        idx = str(disk.get("index", disk.get("Index", 0)))
        yield Service(item=idx)


def check_reolink_hdd(item: str, section: dict) -> CheckResult:
    if not section.get("ok"):
        err = section.get("error", "Keine Daten vom Agenten")
        yield Result(state=State.CRIT, summary=f"Agentenfehler: {err}")
        return

    target_disk = None
    for disk in section.get("disks", []):
        idx = str(disk.get("index", disk.get("Index", 0)))
        if idx == item:
            target_disk = disk
            break

    if target_disk is None:
        yield Result(state=State.UNKNOWN, summary=f"HDD {item} nicht gefunden")
        return

    capacity_mb = target_disk.get("capacity", target_disk.get("Capacity", 0))
    used_mb     = target_disk.get("size",     target_disk.get("Size", 0))
    formatted   = target_disk.get("format",   target_disk.get("Format", -1))
    mounted     = target_disk.get("mount",    target_disk.get("Mount", -1))

    if mounted == 0:
        yield Result(state=State.CRIT, summary="HDD ist NICHT eingehängt (mount=0)")
    elif formatted == 0:
        yield Result(state=State.CRIT, summary="HDD ist NICHT formatiert (format=0)")
    elif capacity_mb == 0:
        yield Result(state=State.WARN, summary="HDD-Kapazität = 0 MB, Disk eventuell defekt")
    else:
        used_pct = (used_mb / capacity_mb * 100) if capacity_mb > 0 else 0

        if used_pct >= 95:
            state = State.CRIT
            summary = f"HDD fast voll: {used_pct:.1f}%"
        elif used_pct >= 85:
            state = State.WARN
            summary = f"HDD läuft voll: {used_pct:.1f}%"
        else:
            state = State.OK
            summary = f"HDD OK — {used_pct:.1f}% belegt"

        cap_gb   = capacity_mb / 1024
        used_gb  = used_mb / 1024
        free_gb  = (capacity_mb - used_mb) / 1024

        summary += f" ({used_gb:.1f} GB / {cap_gb:.1f} GB, frei: {free_gb:.1f} GB)"
        yield Result(state=state, summary=summary)

        yield Metric("disk_used_gb",   used_gb,     boundaries=(0, cap_gb))
        yield Metric("disk_capacity_gb", cap_gb)
        yield Metric("disk_utilization", used_pct,
                     levels=(85.0, 95.0), boundaries=(0, 100))


check_plugin_reolink_hdd = CheckPlugin(
    name="reolink_hdd",
    service_name="Reolink HDD %s",
    discovery_function=discover_reolink_hdd,
    check_function=check_reolink_hdd,
)


def parse_reolink_performance(string_table: StringTable) -> dict:
    try:
        return json.loads(string_table[0][0])
    except Exception:
        return {}


agent_section_reolink_performance = AgentSection(
    name="reolink_performance",
    parse_function=parse_reolink_performance,
)


def discover_reolink_performance(section: dict) -> DiscoveryResult:
    if section.get("ok"):
        yield Service()


def check_reolink_performance(section: dict) -> CheckResult:
    if not section.get("ok"):
        yield Result(state=State.CRIT, summary=section.get("error", "Keine Performancedaten"))
        return

    data = section.get("data", {})
    cpu = None
    for key in ("cpuUsed", "CpuUsed", "cpu_used"):
        if key in data:
            cpu = data[key]
            break
    if cpu is None and isinstance(data.get("Performance"), dict):
        cpu = data["Performance"].get("cpuUsed")

    if cpu is None:
        yield Result(state=State.UNKNOWN, summary="CPU-Wert nicht in API-Antwort gefunden")
        return

    try:
        cpu = float(cpu)
    except (TypeError, ValueError):
        yield Result(state=State.UNKNOWN, summary=f"Ungültiger CPU-Wert: {cpu!r}")
        return

    if cpu >= 95:
        state = State.CRIT
    elif cpu >= 80:
        state = State.WARN
    else:
        state = State.OK

    yield Result(state=state, summary=f"CPU-Auslastung: {cpu:.0f}%")
    yield Metric("cpu_utilization", cpu, levels=(80.0, 95.0), boundaries=(0, 100))


check_plugin_reolink_performance = CheckPlugin(
    name="reolink_performance",
    service_name="Reolink Performance",
    discovery_function=discover_reolink_performance,
    check_function=check_reolink_performance,
)


def parse_reolink_info(string_table: StringTable) -> dict:
    try:
        return json.loads(string_table[0][0])
    except Exception:
        return {}


agent_section_reolink_info = AgentSection(
    name="reolink_info",
    parse_function=parse_reolink_info,
)


def discover_reolink_info(section: dict) -> DiscoveryResult:
    yield Service()


def check_reolink_info(section: dict) -> CheckResult:
    if not section.get("ok"):
        yield Result(state=State.CRIT, summary=section.get("error", "Verbindungsfehler"))
        return

    data = section.get("data", {})
    dev = data.get("DevInfo", data)

    model    = dev.get("model",    dev.get("Model",   "unbekannt"))
    firmware = dev.get("firmVer",  dev.get("FirmVer", "unbekannt"))
    name     = dev.get("name",     dev.get("Name",    ""))
    serial   = dev.get("serial",   dev.get("Serial",  ""))

    details = f"Modell: {model}, Firmware: {firmware}"
    if name:
        details += f", Name: {name}"
    if serial:
        details += f", S/N: {serial}"

    yield Result(state=State.OK, summary=details)


check_plugin_reolink_info = CheckPlugin(
    name="reolink_info",
    service_name="Reolink Info",
    discovery_function=discover_reolink_info,
    check_function=check_reolink_info,
)


def parse_reolink_recording(string_table: StringTable) -> dict:
    try:
        return json.loads(string_table[0][0])
    except Exception:
        return {}


agent_section_reolink_recording = AgentSection(
    name="reolink_recording",
    parse_function=parse_reolink_recording,
)


def discover_reolink_recording(section: dict) -> DiscoveryResult:
    if section.get("ok"):
        yield Service()


def check_reolink_recording(section: dict) -> CheckResult:
    if not section.get("ok"):
        yield Result(state=State.CRIT, summary=section.get("error", "Keine Aufnahmedaten"))
        return

    data = section.get("data", {})
    rec  = data.get("Rec", data)

    master_enable   = rec.get("enable",   rec.get("Enable",   None))
    schedule        = rec.get("schedule", rec.get("Schedule", {}))
    schedule_enable = schedule.get("enable", schedule.get("Enable", None))
    overwrite       = rec.get("overwrite", rec.get("Overwrite", None))
    save_day        = rec.get("saveDay",   rec.get("SaveDay",   None))
    pre_rec         = rec.get("preRec",    rec.get("PreRec",    None))
    post_rec        = rec.get("postRec",   rec.get("PostRec",   None))

    if master_enable is None:
        yield Result(
            state=State.UNKNOWN,
            summary="Aufnahme-Status nicht in API-Antwort gefunden",
        )
        return

    if master_enable == 0:
        yield Result(
            state=State.CRIT,
            summary="Aufnahme ist DEAKTIVIERT (Hauptschalter aus)",
        )
        return

    if schedule_enable is not None and schedule_enable == 0:
        yield Result(
            state=State.WARN,
            summary="Aufnahme aktiv, aber Zeitplan deaktiviert",
        )
        return

    extras = []
    if pre_rec is not None:
        extras.append(f"Pre-Rec: {pre_rec}s")
    if post_rec is not None:
        extras.append(f"Post-Rec: {post_rec}")
    if save_day is not None:
        extras.append(f"Speicherdauer: {save_day} Tage")
    if overwrite is not None:
        extras.append(f"Überschreiben: {'Ja' if overwrite else 'Nein'}")

    summary = "Aufnahme aktiv"
    if extras:
        summary += f" — {', '.join(extras)}"

    yield Result(state=State.OK, summary=summary)


check_plugin_reolink_recording = CheckPlugin(
    name="reolink_recording",
    service_name="Reolink Recording",
    discovery_function=discover_reolink_recording,
    check_function=check_reolink_recording,
)