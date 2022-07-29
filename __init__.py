###############################################################################
#
#                   The Klyqa Home Assistant Integration
#
#
# Company: QConnex GmbH / Klyqa
#
#
# Author: Frederick Stallmeyer
# E-Mail: frederick.stallmeyer@gmx.de
#
#
###############################################################################
#
# Todo:
#
#   Warnings:
#       + Klyqa integration not making unique entity ids.
#           - Bug occures when entities with same id as in the klyqa account
#             are definied in the configuration.yaml file
#
#   Features:
#       + On try switchup lamp, search the lamp in the network
#       + Load and cache profiles
#       + Address cache on discover devices and connections
#       + Mutexes asyncio lock based
#       + (Rooms working), Timers, Routines, Device Groups
#       + Remove entities when they are gone from the klyqa account
#
#   QA:
#       + Convert magicvalues to constants (commands, arguments, values)
#
#
##############################################################################

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent

from .const import DOMAIN, CONF_SYNC_ROOMS, LOGGER
from homeassistant.helpers.typing import ConfigType

# from .api import Klyqa
# import api.bulb_cli as api
# from . import api
from .api import bulb_cli as api
from datetime import timedelta
from .datacoordinator import KlyqaDataCoordinator, HAKlyqaAccount

import asyncio

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    CONF_SCAN_INTERVAL,
)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT]
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup(hass: HomeAssistant, yaml_config: ConfigType) -> bool:
    """Set up the klyqa component."""
    if DOMAIN in hass.data:
        return True
    component = hass.data[DOMAIN] = KlyqaDataCoordinator.instance(
        LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    await component.async_setup(yaml_config)
    component.entries = {}
    component.remove_listeners = []

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    """Set up or change Klyqa integration from a config entry."""

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    host = entry.data.get(CONF_HOST)
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL)
    global SCAN_INTERVAL
    SCAN_INTERVAL = timedelta(seconds=scan_interval)
    sync_rooms = (
        entry.data.get(CONF_SYNC_ROOMS) if entry.data.get(CONF_SYNC_ROOMS) else False
    )
    component: KlyqaDataCoordinator = hass.data[DOMAIN]
    klyqa_api: HAKlyqaAccount = None
    if (
        DOMAIN in hass.data
        and hasattr(component, "entries")
        and entry.entry_id in component.entries
    ):
        klyqa_api: HAKlyqaAccount = component.entries[entry.entry_id]
        await hass.async_add_executor_job(klyqa_api.shutdown)

        klyqa_api.username = username
        klyqa_api.password = password
        klyqa_api.host = host
        # klyqa_api.sync_rooms = sync_rooms
    else:
        klyqa_api: HAKlyqaAccount = HAKlyqaAccount(
            component.udp,
            component.tcp,
            username,
            password,
            host,
            hass,
            # sync_rooms,
            # int(hass.data["light"].scan_interval.total_seconds()),
        )
        if not hasattr(component, "entries"):
            component.entries = {}
        component.entries[entry.entry_id] = klyqa_api

    # if not await hass.async_create_task(klyqa_api.login()):
    if not await klyqa_api.login():
        return False

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, klyqa_api.shutdown)

    # For previous config entries where unique_id is None
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=entry.data[CONF_USERNAME]
        )

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not unload_ok:
        return unload_ok

    for remove_listener in hass.data[DOMAIN].remove_listeners:
        remove_listener()

    if DOMAIN in hass.data:
        if entry.entry_id in hass.data[DOMAIN].entries:
            if hass.data[DOMAIN].entries[entry.entry_id]:
                await hass.async_add_executor_job(
                    hass.data[DOMAIN].entries[entry.entry_id].shutdown
                )
            hass.data[DOMAIN].entries.pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)
