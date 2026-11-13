DOMAIN = "ecohome"
MANUFACTURER = "New Energy"
ISSUE_TRACKER_URL = "https://github.com/sgielen/ha-ecohome/issues"
CONF_UPDATE_INTERVAL = "update_interval_minutes"
# Language of the names and labels from the Eco-Home API; empty means Home Assistant's language.
CONF_LANGUAGE = "language"
DEFAULT_UPDATE_INTERVAL_MINUTES = 1
# How long a heat pump must be offline before a Repairs issue is shown.
OFFLINE_ISSUE_DELAY_MINUTES = 10

# The "card" field of the cards in the device detail's cardList. Cards are identified by whether they
# have a modeList; these IDs (as seen on a Batavia Heat unit) are only used to reject a mismatch.
HEATING_CARD_ID = "0"
HOT_WATER_CARD_ID = "2"

# Target temperature range used when a card reports no valid range, and for heating while it follows
# a heating or cooling curve. Wide enough for the water temperatures of both heating and hot water.
WIDE_MIN_TEMP = 5.0
WIDE_MAX_TEMP = 75.0
