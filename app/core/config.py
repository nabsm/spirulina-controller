from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Spirulina Lux Control"
    timezone: str = "Asia/Kuala_Lumpur"

    # Sampling
    sample_seconds: int = 5
    avg_samples: int = 6  # 6 readings => 30s avg

    # Control protections
    hysteresis_lux: float = 50.0
    min_switch_interval_seconds: int = 60

    # Defaults when no schedule window matches
    default_min_lux: float = 3000
    default_max_lux: float = 6000

    # Storage
    sqlite_path: str = Field(default="spirulina.db")

    # Mode: "sim" for development; later "real"
    mode: str = Field(default="sim")

    # Safety: if sensor fails repeatedly, what to do?
    fail_safe_light_state: bool = False  # False = OFF



    # Sensor mode: "sim" or "rs485"
    sensor_mode: str = "sim"

    # RS485 / Modbus RTU
    rs485_port: str = "/dev/ttyUSB0"      # Windows example: "COM3"
    rs485_baudrate: int = 9600
    rs485_slave_id: int = 1

    # Lux register definition
    lux_functioncode: int = 3             # 3=holding, 4=input
    lux_register_address: int = 0
    lux_register_count: int = 1
    lux_scale: float = 1.0



settings = Settings()
