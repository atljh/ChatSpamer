import os
from pathlib import Path

from config import Config
from src.console import console
from src.thon import BaseThon
from src.managers import ChannelManager

class Spamer(BaseThon):
    def __init__(
        self,
        item: Path,
        json_file: Path,
        json_data: dict,
        config: Config,
    ):
        super().__init__(item=item, json_data=json_data)
        self.item = item
        self.config = config
        self.json_file = json_file
        self.account_phone = os.path.basename(self.item).split('.')[0]
        self.channel_manager = ChannelManager(self.config)

    async def _start_spam(self) -> str:
        console.log(f"Используется аккаунт {self.account_phone}", style="green")
        r = await self.channel_manager.process_groups(self.client, self.account_phone)
        return r
    
    async def main(self) -> str:
        r = await self.check()
        if "OK" not in r:
            await self.disconnect()
            return r
        r = await self._start_spam()
        if "OK" not in r:
            return r
        await self.disconnect()
        return r
