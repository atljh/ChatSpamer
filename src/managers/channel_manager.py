import asyncio

from telethon.errors.rpcerrorlist import UserBannedInChannelError, MsgIdInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    FloodWaitError, UserBannedInChannelError, UserNotParticipantError, ChatWriteForbiddenError, 
    ChatAdminRequiredError, UserIsBlockedError, InputUserDeactivatedError, 
    PeerFloodError, ChannelPrivateError, UsernameNotOccupiedError, 
    InviteRequestSentError, InviteHashExpiredError, ChatSendMediaForbiddenError, UserDeactivatedBanError
)

from src.console import console
from .file_manager import FileManager

class ChannelManager:

    def __init__(self, config):
        self.config = config
        self.delay_before_sending = self.config.delay_before_sending
        self.delay_before_subscription = self.config.delay_before_subscription
        self.delay_before_second_subscription = self.config.delay_before_second_subscription
        self.delay_between_accounts = self.config.delay_between_accounts
        self.cycles_before_unblacklist = self.config.cycles_before_unblacklist

        self.file_manager = FileManager()
        self.groups = FileManager.read_groups()
        self.post_text, self.image  = FileManager.read_post_and_image()

    async def process_groups(self, client, account_phone):
        groups = self.groups
        last_position = self.file_manager.get_last_position()
        if last_position is not None:
            groups = groups[last_position:]
        
        for index, group in enumerate(groups):
            current_position = last_position + index if last_position is not None else index
            self.file_manager.save_last_position(current_position)

            if self.file_manager.is_group_blacklisted(account_phone, group):
                console.log(f"Группа {group} в черном списке аккаунта {account_phone}. Пропускаем.", style="yellow")
                continue

            join_result = await self.join_group(client, account_phone, group)
            if "SKIP" in join_result:
                continue
            if "OK" not in join_result:
                return join_result

            await self.sleep_before_send_message()
            send_result = await self.send_post(client, account_phone, group)
            if "OK" not in send_result:
                return send_result

        self.file_manager.save_last_position(0)
        return "OK"

    
    async def join_group(self, client, account_phone, group):
        try:
            entity = await client.get_entity(group)
            is_member = await self.is_participant(client, entity, group, account_phone)
            if is_member:
                return is_member
        except Exception:
            try:
                await self.sleep_before_enter_group()
                await client(ImportChatInviteRequest(group[6:]))
                console.log(f"Аккаунт {account_phone} присоединился к приватной группе {group}", style="green")
                return "OK"
            except Exception as e:
                if "is not valid anymore" in str(e):
                    console.log(f"Аккаунт {account_phone} забанен в чате {group}, добавляем в черный список.", style="red")
                    self.file_manager.add_to_blacklist(account_phone, group)
                    return "SKIP"
                elif "successfully requested to join" in str(e):
                    console.log(f"Запрос на подписку в группу {group} уже отправлен и еще не подтвержден.", style="yellow")
                    return "SKIP"
                else:
                    console.log(f"Ошибка при присоединении к группе {group}: {e}", style="red")
                    return "ERROR"
        try:
            await self.sleep_before_enter_group()
            await client(JoinChannelRequest(group))
            console.log(f"Аккаунт присоединился к группе {group}", style="green")
        except Exception as e:
            console.log(f"Ошибка при подписке на группу {group}: {e}", style="red")
            return "ERROR"
        return "OK"
    
    async def send_post(self, client, account_phone, group, send_image=True):
        try:
            group_entity = await self.get_channel_entity(client, group)
            if not group_entity:
                console.log(f"Группа {group} не найдена или недоступна.", style="red")
                self.file_manager.add_to_blacklist(account_phone, group)
                return "OK"
            if self.image and send_image:
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
            console.log(f"Сообщение отправлено от аккаунта {account_phone} в группу {group_entity.title}", style="green")
        except FloodWaitError as e:
            console.log(f"Слишком много запросов от аккаунта {account_phone}. Ожидание {e.seconds} секунд.", style="yellow")
            return "MUTE"
        except PeerFloodError:
            console.log(f"Аккаунт {account_phone} временно заблокирован за спам. Перемещаем аккаунт в папку мут.", style="yellow")
            return "MUTE"
        except UserBannedInChannelError:
            console.log(f"Аккаунт {account_phone} заблокирован в группе {group_entity.title}", style="red")
            self.file_manager.add_to_blacklist(account_phone, group)
            return "OK"
        except MsgIdInvalidError:
            console.log("Канал не связан с чатом", style="red")
            self.file_manager.add_to_blacklist(account_phone, group)
            return "OK"
        except UserDeactivatedBanError:
            console.log(f"Аккаунт {account_phone} забанен", style="red")
            return "ERROR_AUTH"
        except ChatWriteForbiddenError:
            console.log(f"У аккаунта {account_phone} нет прав на отправку сообщений в чат.", style="yellow")
            self.file_manager.add_to_blacklist(account_phone, group)
            return "OK"
        except ChatSendMediaForbiddenError:
            console.log(f"Ошибка: запрещено отправлять фото в этом чате. Повторная отправка без картинки.", style="yellow")
            await self.send_post(client, account_phone, group, send_image=False)
            return "OK"
        except Exception as e:
            if "private and you lack permission" in str(e):
                console.log(f"Группа {group_entity.title} недоступна для аккаунта {account_phone}. Пропускаем.", style="yellow")
                self.file_manager.add_to_blacklist(account_phone, group)
                return "OK"
            elif "You can't write" in str(e):
                console.log(f"Группа {group_entity.title} недоступна для аккаунта {account_phone}. Пропускаем.", style="yellow")
                self.file_manager.add_to_blacklist(account_phone, group)
                return "OK"
            elif "CHAT_SEND_PHOTOS_FORBIDDEN" in str(e):
                console.log(f"Ошибка: запрещено отправлять фото в этом чате. Повторная отправка без картинки.", style="yellow")
                await self.send_post(client, account_phone, group, send_image=False)
                return "OK"
            elif "A wait of" in str(e):
                console.log(f"Слишком много запросов от аккаунта {account_phone}. Ожидание {e.seconds} секунд.", style="yellow")
                return "MUTE"
            else:
                console.log(f"Ошибка при отправке сообщения в группе {group_entity.title}, {account_phone}: {e}", style="red")
            return "ERROR"
        return "OK"


    async def is_participant(self, client, group, group_link, account_phone):
        try:
            await client.get_permissions(group, 'me')
            return "OK"
        except UserNotParticipantError:
            return False
        except Exception as e:
            if "private and you lack permission" in str(e):
                console.log(f"Аккаунт {account_phone} забанен в чате {group.title}, добавляем в черный список.", style="red")
                self.file_manager.add_to_blacklist(account_phone, group_link)
                return "SKIP"
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