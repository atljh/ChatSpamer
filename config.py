import sys
import yaml
from pydantic import BaseModel, Field

from src.logger import logger


class Config(BaseModel):
    delay_before_sending: int = Field(
        default=7, 
        ge=0, 
        description="Задержка перед отправкой сообщения (в секундах)"
    )
    delay_before_subscription: int = Field(
        default=7, 
        ge=0, 
        description="Задержка перед подпиской (в секундах)"
    )
    delay_before_second_subscription: int = Field(
        default=7, 
        ge=0, 
        description="Задержка перед повторной подпиской (в секундах)"
    )
    delay_between_accounts: int = Field(
        default=7, 
        ge=0, 
        description="Задержка между сменой аккаунта (в секундах)"
    )
    delay_after_mute: int = Field(
        default=600, 
        ge=0, 
        description="Задержка после блокировки/мута (в секундах)"
    )
    cycles_before_unblacklist: int = Field(
        default=7, 
        ge=1, 
        description="Количество циклов до снятия из черного списка"
    )

class ConfigManager:
    @staticmethod
    def load_config(config_file: str = 'config.yaml') -> Config:
        try:
            with open(config_file, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                if not isinstance(config_data.get('settings'), dict):
                    raise ValueError("Секция 'settings' отсутствует или имеет неверный формат")
                return Config(**config_data['settings'])
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            sys.exit(1)
