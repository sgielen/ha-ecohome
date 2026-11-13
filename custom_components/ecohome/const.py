DOMAIN = "ecohome"
MANUFACTURER = "New Energy"
ISSUE_TRACKER_URL = "https://github.com/sgielen/ha-ecohome/issues"
CONF_UPDATE_INTERVAL = "update_interval_minutes"
DEFAULT_UPDATE_INTERVAL_MINUTES = 1
# How long a heat pump must be offline before a Repairs issue is shown.
OFFLINE_ISSUE_DELAY_MINUTES = 10

# The "card" field of the cards in the device detail's cardList. Cards are identified by whether they
# have a modeList; these IDs (as seen on a Batavia Heat unit) are only used to reject a mismatch.
HEATING_CARD_ID = "0"
HOT_WATER_CARD_ID = "2"
