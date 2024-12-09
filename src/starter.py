import asyncio
from pathlib import Path
from asyncio import Semaphore
from typing import Generator

from tooler import move_item

from src.console import console
from src.thon import BaseSession
from .spamer import Spamer
from src.managers import FileManager

class Starter(BaseSession):
    def __init__(
        self,
        threads: int,
        config
    ):
        self.semaphore = Semaphore(threads)
        self.config = config
        super().__init__()
        self.file_manager = FileManager()

    async def _main(
        self,
        item: Path,
        json_file: Path,
        json_data: dict,
        config
    ):
        try:
            spamer = Spamer(item, json_file, json_data, config)
            async with self.semaphore:
                try:
                    r = await spamer.main()
                except Exception as e:
                    console.log(f"Ошибка при работе аккаунта {item}: {e}", style="red")
                    r = "ERROR_UNKNOWN"
            if "OK" not in r:
                console.log(item.name, r, style="red")
            if "ERROR_AUTH" in r:
                move_item(item, self.banned_dir, True, True)
                move_item(json_file, self.banned_dir, True, True)
                console.log(f"Аккаунт {item.name} забанен или разлогинен", style="red")
                return
            if "ERROR" in r:
                move_item(item, self.errors_dir, True, True)
                move_item(json_file, self.errors_dir, True, True)
            if "MUTE" in r:
                move_item(item, self.muted_dir, True, True)
                move_item(json_file, self.muted_dir, True, True)
            if "OK" in r:
                console.log(f"Аккаунт {item.name} успешно закончил работу", style="green")
        except Exception as e:
            console.log(f"Ошибка при работе аккаунта {item}: {e}", style="red")

    def __get_sessions_and_users(self) -> Generator:
        for item, json_file, json_data in self.find_sessions():
            yield item, json_file, json_data

    async def main(self) -> bool:
        cycle_count = 1
        while True:
            console.log(f"Цикл №{cycle_count}")
            for item, json_file, json_data in self.__get_sessions_and_users():
                console.log(f"Задержка {self.config.delay_between_accounts} секунд перед сменой аккаунта.")
                await asyncio.sleep(self.config.delay_between_accounts)
                await self._main(item, json_file, json_data, self.config)
            cycle_count += 1
            print(self.config.cycles_before_unblacklist, cycle_count)
            if cycle_count >= self.config.cycles_before_unblacklist:
                self.file_manager.clear_blacklist()
                cycle_count = 1
