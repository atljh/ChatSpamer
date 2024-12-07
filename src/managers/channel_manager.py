import asyncio

from telethon.errors import UserNotParticipantError, FloodWaitError
from telethon.errors.rpcerrorlist import UserBannedInChannelError, MsgIdInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from src.console import console
from .file_manager import FileManager

class ChannelManager:
    MAX_SEND_ATTEMPTS = 3 

    def __init__(self, config):
        self.config = config
        self.delay_before_sending = self.config.delay_before_sending
        self.delay_before_subscription = self.config.delay_before_subscription
        self.delay_before_second_subscription = self.config.delay_before_second_subscription
        self.delay_between_accounts = self.config.delay_between_accounts
        self.delay_after_mute = self.config.delay_after_mute
        self.cycles_before_unblacklist = self.config.cycles_before_unblacklist

        self.groups = FileManager.read_groups()
        self.post_text, self.image  = FileManager.read_post_and_image()

    async def process_groups(self, client, account_phone):
        for group in self.groups:
            join_result = await self.join_group(client, account_phone, group)
            if "OK" not in join_result:
                return join_result
            send_result = await self.send_post(client, account_phone, group)
            if "OK" not in send_result:
                return send_result
        return "OK"
    
    async def join_group(self, client, account_phone, group):
        try:
            entity = await client.get_entity(group)
            if await self.is_participant(client, entity):
                return "OK"
        except Exception:
            try:
                await self.sleep_before_enter_group()
                await client(ImportChatInviteRequest(group[6:]))
                console.log(f"Аккаунт {account_phone} присоединился к приватной группе {group}")
                return "OK"
            except Exception as e:
                if "is not valid anymore" in str(e):
                    console.log("Вы забанены в канале")
                    return "OK"
                else:
                    console.log(f"Ошибка при присоединении к группе {group}: {e}")
                    return
        try:
            await self.sleep_before_enter_group()
            await client(JoinChannelRequest(group))
            console.log(f"Аккаунт присоединился к группе {group}")
        except Exception as e:
            console.log(f"Ошибка при подписке на группу {group}: {e}")
            return "ERROR"
        return "OK"
    
    async def send_post(self, client, account_phone, group, attempts=0):
        try:
            group = await self.get_channel_entity(client, group)
            if not group:
                console.log("Канал не найден или недоступен.", style="red")
                return
            if self.image:
                await client.send_file(
                    group, self.image,
                    caption=self.post_text,
                    parse_mode='HTML'
                )
            else:
                await client.send_message(
                    group, self.post_text, 
                    parse_mode='HTML'
                )

            console.log(f"Сообщение отправлено от аккаунта {account_phone} в группу {group.title}", style="green")
        except FloodWaitError as e:
            console.log(f"Слишком много запросов от аккаунта {account_phone}. Ожидание {e.seconds} секунд.", style="yellow")
        except UserBannedInChannelError:
            console.log(f"Аккаунт {account_phone} заблокирован в группе {group.title}", style="red")
        except MsgIdInvalidError:
            console.log("Канал не связан с чатом", style="red")
        except Exception as e:
            if "private and you lack permission" in str(e):
                console.log(f"Группа {group.title} недоступен для аккаунта {account_phone}. Пропускаем.", style="yellow")
            elif "You can't write" in str(e):
                console.log(f"Группа {group.title} недоступен для аккаунта {account_phone}. Пропускаем.", style="yellow")
            else:
                console.log(f"Ошибка при отправке сообщения: {e}", style="red")
        return "OK"

    async def is_participant(self, client, group):
        try:
            await client.get_permissions(group, 'me')
            return True
        except UserNotParticipantError:
            return False
        except Exception as e:
            console.log(f"Ошибка при обработке канала {group}: {e}")
            return False
    
    async def get_channel_entity(self, client, group):
        try:
            return await client.get_entity(group)
        except Exception as e:
            console.log(f"Ошибка получения объекта канала: {e}", style="red")
            return None

    async def sleep_before_send_message(self):
        delay =  self.delay_before_sending
        console.log(f"Задержка перед отправкой сообщения {delay} сек")
        await asyncio.sleep(delay)

    async def sleep_before_enter_group(self):
        delay = self.delay_before_subscription
        console.log(f"Задержка перед подпиской на группу {delay} сек")
        await asyncio.sleep(delay)