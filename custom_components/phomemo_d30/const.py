"""Constants for the Phomemo D30 integration."""

# Domain
DOMAIN = "phomemo_d30"

# Configuration keys
CONF_MODE = "mode"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_BLUETOOTH_MAC = "bluetooth_mac"
CONF_DARKNESS = "darkness"
CONF_SPEED = "speed"
CONF_RETRY_ATTEMPTS = "retry_attempts"
CONF_RETRY_DELAY = "retry_delay"
CONF_QUEUE_MAX_SIZE = "queue_max_size"
CONF_MOCK_PRINT_DELAY = "mock_print_delay"
CONF_MOCK_SAVE_PATH = "mock_save_path"

# Defaults
DEFAULT_MODE = "mock"
DEFAULT_MQTT_TOPIC = "homeassistant/phomemo/print"
DEFAULT_DARKNESS = 5
DEFAULT_SPEED = "normal"
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 5
DEFAULT_QUEUE_MAX_SIZE = 50
DEFAULT_MOCK_PRINT_DELAY = 2
DEFAULT_MOCK_SAVE_PATH = "/tmp/phomemo_test"

# Modes
MODE_MOCK = "mock"
MODE_BLUETOOTH = "bluetooth"

# Job statuses
STATUS_QUEUED = "queued"
STATUS_PRINTING = "printing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_RETRYING = "retrying"

# Printer statuses
PRINTER_STATUS_IDLE = "idle"
PRINTER_STATUS_PRINTING = "printing"
PRINTER_STATUS_ERROR = "error"
PRINTER_STATUS_DISCONNECTED = "disconnected"

# Services
SERVICE_PRINT = "print"
SERVICE_CLEAR_QUEUE = "clear_queue"
SERVICE_RETRY_FAILED = "retry_failed"

# Platforms
PLATFORMS = ["sensor"]
