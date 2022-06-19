"""Constants for the QConnex integration."""

import logging

# logging.basicConfig(
#     format="%(asctime)s %(levelname)-8s %(message)s"
# )  # , level=logging.INFO
LOGGER = logging.getLogger(__package__)
# logging = logging.getLogger(__package__)

DOMAIN = "klyqa"


CONF_POLLING = "polling"
CONF_SYNC_ROOMS = "sync_rooms"
EVENT_KLYQA_NEW_LIGHT = "klyqa_new_light"
REQUEST_TIMEOUT = 11000
