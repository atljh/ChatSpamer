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

    async def __main(self):
        await self.channel_manager.join_groups(self.client, self.account_phone)
        console.log(f"Аккаунт {self.account_phone} успешно подключен и добавлен в очередь.", style="green")

    async def _main(self) -> str:
        r = await self.check()
        if "OK" not in r:
            return r
        await self.__main()
        return r

    async def main(self) -> str:
        r = await self._main()
        return r
