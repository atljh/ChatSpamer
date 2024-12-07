import random
import asyncio
import logging

from telethon import events
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

    async def is_participant(self, client, group):
        try:
            await client.get_permissions(group, 'me')
            return True
        except UserNotParticipantError:
            return False
        except Exception as e:
            console.log(f"Ошибка при обработке канала {group}: {e}")
            return False
        
    async def sleep_before_send_message(self):
        delay =  self.delay_before_sending
        console.log(f"Задержка перед отправкой сообщения {delay} сек")
        await asyncio.sleep(delay)

    async def sleep_before_enter_channel(self):
        delay = self.delay_before_subscription
        console.log(f"Задержка перед подпиской на канал {delay} сек")
        await asyncio.sleep(delay)

    async def join_groups(self, client, account_phone):
        for group in self.groups:
            try:
                entity = await client.get_entity(group)
                if await self.is_participant(client, entity):
                    continue
            except Exception:
                try:
                    await self.sleep_before_enter_channel()
                    await client(ImportChatInviteRequest(group[6:]))
                    console.log(f"Аккаунт {account_phone} присоединился к приватному каналу {group}")
                    continue
                except Exception as e:
                    if "is not valid anymore" in str(e):
                        console.log("Вы забанены в канале")
                        continue
                    else:
                        console.log(f"Ошибка при присоединении к каналу {group}: {e}")
                        continue
            try:
                await self.sleep_before_enter_channel()
                await client(JoinChannelRequest(group))
                console.log(f"Аккаунт присоединился к каналу {group}")
            except Exception as e:
                console.log(f"Ошибка при подписке на канал {group}: {e}")
                    
    async def monitor_groups(self, client, account_phone):
        for group in self.groups:
            client.add_event_handler(
                lambda event: self.new_post_handler(client, event, self.prompt_tone, account_phone),
                events.NewMessage(chats=group)
            )
        console.log(f"Мониторинг каналов начался для аккаунта {account_phone}...")
        await self.stop_event.wait()

    async def get_channel_entity(self, client, group):
        try:
            return await client.get_entity(group)
        except Exception as e:
            console.log(f"Ошибка получения объекта канала: {e}", style="red")
            return None

    async def send_comment(self, client, account_phone, group, comment, message_id, attempts=0):

        try:
            channel_entity = await self.get_channel_entity(client, group)
            if not channel_entity:
                console.log("Канал не найден или недоступен.", style="red")
                return
            await client.send_message(
                entity=channel_entity,
                message=comment,
                comment_to=message_id
            )
            console.log(f"Комментарий отправлен от аккаунта {account_phone} в канал {group.title}", style="green")
            self.account_comment_count[account_phone] = self.account_comment_count.get(account_phone, 0) + 1
            if self.account_comment_count[account_phone] >= self.comment_limit:
                await self.switch_to_next_account()
                await self.sleep_account(account_phone)
        except FloodWaitError as e:
            logging.warning(f"Слишком много запросов от аккаунта {account_phone}. Ожидание {e.seconds} секунд.", style="yellow")
            await asyncio.sleep(e.seconds)
            await self.switch_to_next_account()
        except UserBannedInChannelError:
            console.log(f"Аккаунт {account_phone} заблокирован в канале {group.title}", style="red")
            await self.switch_to_next_account()
        except MsgIdInvalidError:
            console.log("Канал не связан с чатом", style="red")
            await self.switch_to_next_account()
        except Exception as e:
            if "private and you lack permission" in str(e):
                console.log(f"Канал {group.title} недоступен для аккаунта {account_phone}. Пропускаем.", style="yellow")
            elif "You can't write" in str(e):
                console.log(f"Канал {group.title} недоступен для аккаунта {account_phone}. Пропускаем.", style="yellow")
            else:
                console.log(f"Ошибка при отправке комментария: {e}", style="red")
            
            if attempts < self.MAX_SEND_ATTEMPTS:
                console.log(f"Попытка {attempts + 1}/{self.MAX_SEND_ATTEMPTS} отправить сообщение c другого аккаунта...")
                await self.switch_to_next_account()
                next_client = self.accounts.get(self.active_account)
                if next_client:
                    await self.sleep_before_send_message()
                    await self.send_comment(next_client, account_phone, group, comment, message_id, attempts + 1)
                else:
                    console.log("Нет доступных аккаунтов для отправки.", style="red")
            else:
                console.log(f"Не удалось отправить сообщение после {self.MAX_SEND_ATTEMPTS} попыток.", style="red")
