import os
import sys
import shutil
import asyncio
import time
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, UserBannedInChannelError, ChatWriteForbiddenError, 
    ChatAdminRequiredError, UserIsBlockedError, InputUserDeactivatedError, 
    PeerFloodError, ChannelPrivateError, UsernameNotOccupiedError, 
    InviteRequestSentError, InviteHashExpiredError, ChatSendMediaForbiddenError, UserDeactivatedBanError, PhoneNumberInvalidError
)
from telethon.sessions import StringSession

from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
import json
import subprocess
import requests
import configparser

import logging

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

def load_config(filename='config.txt'):
    config = {}
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip("'")
    return config

# Загрузка конфигурации
config = load_config()

# Извлечение данных
api_id = int(config.get('api_id', '0'))
api_hash = config.get('api_hash', '')



DELAY_BEFORE_SENDING = int(config.get('DELAY_BEFORE_SENDING', '1'))
DELAY_BEFORE_SUBSCRIPTION = int(config.get('DELAY_BEFORE_SUBSCRIPTION', '1'))
DELAY_BETWEEN_ACCOUNTS = int(config.get('DELAY_BETWEEN_ACCOUNTS', '1'))
DELAY_AFTER_MUTE = int(config.get('DELAY_AFTER_MUTE', '600'))
CYCLES_BEFORE_UNBLACKLIST = int(config.get('CYCLES_BEFORE_UNBLACKLIST', '2'))
DELAY_BEFORE_SECOND_SUBSCRIPTION = int(config.get('DELAY_BEFORE_SECOND_SUBSCRIPTION', '3'))



def get_settings():
    try:
        with open("settings.json", "r") as f:
            return json.loads(f.read())
    except:
        return {}

def set_settings(data):
    with open("settings.json", "w") as f:
        f.write(json.dumps(data))


settings = get_settings()


def register_user():
    print("Связываемся с сервером...")
    current_machine_id = (
        str(subprocess.check_output("wmic csproduct get uuid"), "utf-8")
        .split("\n")[1]
        .strip()
    )

    admin_username = settings.get("ADMIN_USERNAME")
    script_name = settings.get("SCRIPTNAME")  # Подгружаем SCRIPTNAME из settings.json
    BASE_API_URL = settings.get("BASE_API_URL", "http://142.93.105.98:8000")

    db_id = requests.get(
        f"{BASE_API_URL}/api/{script_name}/{current_machine_id}/{admin_username}"
    )
    db_id = db_id.json()
    if db_id.get("message"):
        print("Неправильный логин")
        sys.exit()
    file_key = settings.get("ACCESS_KEY")
    print(f"Ваш ID в системе: {db_id['id']}")
    if file_key:
        key = file_key
    else:
        key = input("Введите ваш ключ доступа: ")
    while True:
        is_correct = requests.post(
            f"{BASE_API_URL}/api/{script_name}/check/",
            data={"pk": current_machine_id, "key": key},
        ).json()["message"]
        if is_correct:
            print("Вход успешно выполнен!")
            settings["ACCESS_KEY"] = key
            set_settings(settings)
            return
        else:
            print("Неправильный ключ!")
            key = input("Введите ваш ключ доступа: ")


register_user()



CURRENT_POSITION_PATH = 'current_position.txt'

SESSIONS_PATH = "accounts/"
POST_PATH = "post/"
BLACKLIST_PATH = "blacklist.txt"
GROUPS_PATH = "group.txt"

mute_count = 0


with open(GROUPS_PATH, 'r', encoding='utf-8') as f:
    groups = [line.strip() for line in f.readlines()]

with open(BLACKLIST_PATH, 'r', encoding='utf-8') as f:
    blacklist = [line.strip() for line in f.readlines()]

def load_current_position():
    if os.path.exists(CURRENT_POSITION_PATH):
        with open(CURRENT_POSITION_PATH, 'r') as f:
            return int(f.read().strip())
    return 0

def save_current_position(position):
    with open(CURRENT_POSITION_PATH, 'w') as f:
        f.write(str(position))


with open(os.path.join(POST_PATH, "post.txt"), 'r', encoding='utf-8') as f:
    post_text = f.read()

image_path = os.path.join(POST_PATH, "image.jpg") if os.path.exists(os.path.join(POST_PATH, "image.jpg")) else None

def update_blacklist(chat):
    if chat not in blacklist:
        blacklist.append(chat)
        with open(BLACKLIST_PATH, 'a', encoding='utf-8') as f:
            f.write(chat + "\n")

def move_session(session_path, reason):
    target_dir = os.path.join(SESSIONS_PATH, reason)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    basename = os.path.basename(session_path)
    target_path = os.path.join(target_dir, basename)
    
    shutil.move(session_path, target_path)

async def send_message(client, chat, message, image):
    try:
        print(f"Отправка сообщения в чат...")
        if image:
            await client.send_file(chat, image, caption=message, parse_mode='HTML')
        else:
            await client.send_message(chat, message, parse_mode='HTML')
        print(f"Сообщение успешно отправлено.")
        return True
    except FloodWaitError as e:
        print(f"Аккаунт ушел в мут, перемещаем аккаунт и начинаем другую сессию..")
        await client.disconnect()
        move_session(client.session.filename, 'mute')
        return 'flood_wait'
    except UserDeactivatedBanError:
        print(f"The user has been deleted/deactivated")
        move_session(client.session.filename, 'ban')
        return False
    except UserBannedInChannelError:
        print(f"UserBannedInChannelError: аккаунт забанен в чате.")
        return False
    except ChatWriteForbiddenError:
        print(f"ChatWriteForbiddenError: нет прав на отправку сообщений в чат.")
        return False
    except ChatSendMediaForbiddenError:
        print(f"ChatSendMediaForbiddenError: запрещено отправлять картинки в этом чате. Повторная отправка без картинки.")
        return await send_message(client, chat, message, None) 
    except (ChatAdminRequiredError, UserIsBlockedError, InputUserDeactivatedError, ChannelPrivateError, InviteRequestSentError) as e:
        print(f"Ошибка отправки сообщения в чат: {type(e).__name__}")
        if isinstance(e, InviteRequestSentError):
            return 'invite_request_sent'
        return False
    except PeerFloodError:
        print(f"PeerFloodError: Аккаунт временно заблокирован за спам. Перемещаем аккаунт в папку спамблок.")
        move_session(client.session.filename, 'spamblock')
        return False
    except Exception as e:
        if "CHAT_SEND_PHOTOS_FORBIDDEN" in str(e):
            print(f"Ошибка: запрещено отправлять фото в этом чате. Повторная отправка без картинки.")
            return await send_message(client, chat, message, None)  # Повторная отправка без картинки
        print(f"Произошла неизвестная ошибка при отправке сообщения в: {type(e).__name__} - {str(e)}")
        return False

# Функция для проверки типа объекта
async def check_username(client, username):
    try:
        result = await client(ResolveUsernameRequest(username))
        if result.chats:
            chat = result.chats[0]
            if chat.broadcast:
                return 'channel'
            else:
                return 'chat'
        elif result.users:
            user = result.users[0]
            return 'user'
    except UsernameNotOccupiedError:
        return 'does not exist'
    except Exception as e:
        print(f"Произошла ошибка при проверке username {username}: {type(e).__name__} - {str(e)}")
        return 'unknown'

# Функция для обработки одного аккаунта
async def process_account(client, groups):
    global mute_count
    error_counts = {}

    current_position = load_current_position()

    for idx in range(current_position, len(groups)):
        chat = groups[idx]

        # Сохраняем текущую позицию
        save_current_position(idx)

        if chat in blacklist:
            continue

        if chat not in error_counts:
            error_counts[chat] = 0

        attempt = 0
        max_attempts = 5

        while attempt < max_attempts:
            try:
                print(f"Обработка чата {chat}...")

                if 'joinchat' in chat:
                    chat_type = 'private'
                    username = chat.split('/')[-1].replace('+', '')
                else:
                    username = chat.split('/')[-1]
                    chat_type = await check_username(client, username)

                if chat_type == 'does not exist':
                    print(f"{chat} не существует или не может быть обработан.")
                    update_blacklist(chat)
                    break
                if chat_type == 'user':
                    print(f"Это пользователь. Отправка сообщения пользователю {chat}...")
                    print(f"Задержка перед отправкой сообщения {DELAY_BEFORE_SENDING} секунд...")
                    await asyncio.sleep(DELAY_BEFORE_SENDING)
                    result = await send_message(client, username, post_text, image_path)
                    if result == 'flood_wait':
                       return 
                    elif result == 'invite_request_sent' or result is False:
                        error_counts[chat] += 1
                        if error_counts[chat] >= 2:
                            print(f"Чат {chat} получил более двух ошибок. Добавляем в черный список.")
                            update_blacklist(chat)
                            break
                    break

                if chat_type == 'private':
                    join_attempts = 0
                    max_join_attempts = 2  # Количество попыток присоединиться к приватному чату

                    while join_attempts < max_join_attempts:
                        try:
                            await client(ImportChatInviteRequest(username))
                            print(f"Присоединение к приватному чату {chat} выполнено.")
                            print(f"Задержка перед подпиской на чат {DELAY_BEFORE_SUBSCRIPTION} секунд...")
                            await asyncio.sleep(DELAY_BEFORE_SUBSCRIPTION)

                            print(f"Задержка перед отправкой сообщения {DELAY_BEFORE_SENDING} секунд...")
                            await asyncio.sleep(DELAY_BEFORE_SENDING)
                            result = await send_message(client, chat, post_text, image_path)
                            if result == 'flood_wait':
                                return 
                            if result == 'invite_request_sent' or result is False:
                                error_counts[chat] += 1
                                if error_counts[chat] >= 2:
                                    print(f"Чат {chat} получил более двух ошибок. Добавляем в черный список.")
                                    update_blacklist(chat)
                                    break
                                join_attempts += 1
                                print(f"Повторная попытка присоединиться и отправить сообщение ({join_attempts}/{max_join_attempts})...")
                            elif result:
                                break
                        except ChannelPrivateError:
                            print(f"Невозможно подписаться на приватный канал {chat}.")
                            update_blacklist(chat)
                            break
                        except FloodWaitError as e:
                            if mute_count >= 2:
                                print(f"Аккаунт ушел в мут, перемещаем аккаунт и начинаем другую сессию.")
                                move_session(client.session.filename, 'mute')
                                
                                mute_count = 0
                                return 'flood_wait'
                            mute_count += 1
                            break
                        except InviteRequestSentError: 
                            print(f"Ошибка при попытке присоединиться (скорее всего чат закрыт) либо инвайт не принимают")
                            update_blacklist(chat)
                            break
                        except Exception as e:
                            print(f"Ошибка при попытке присоединиться или отправить сообщение  d в {chat}: {type(e).__name__} - {str(e)}")
                            join_attempts += 1
                            print(f"Задержка перед повторной попыткой подписки {DELAY_BEFORE_SECOND_SUBSCRIPTION} секунд...")
                            await asyncio.sleep(DELAY_BEFORE_SECOND_SUBSCRIPTION)

                    if join_attempts >= max_join_attempts:
                        print(f"Не удалось присоединиться и отправить сообщение в {chat} после {max_join_attempts} попыток.")
                        update_blacklist(chat)
                    break

                entity = await client.get_entity(chat)
                join_attempts = 0
                max_join_attempts = 2  # Количество попыток присоединиться к чату

                while join_attempts < max_join_attempts:
                    try:
                        
                        print(f"Задержка перед подпиской на чат {DELAY_BEFORE_SUBSCRIPTION} секунд...")
                        await asyncio.sleep(DELAY_BEFORE_SUBSCRIPTION)

                        await client(JoinChannelRequest(entity))
                        print(f"Подписка на чат/канал {chat} выполнена.")
                        print(f"Задержка перед отправкой сообщения {DELAY_BEFORE_SENDING} секунд...")
                        await asyncio.sleep(DELAY_BEFORE_SENDING)
                        result = await send_message(client, entity, post_text, image_path)
                        if result == 'flood_wait' or result == 'invite_request_sent' or result is False:
                            error_counts[chat] += 1
                            if error_counts[chat] >= 2:
                                print(f"Чат {chat} получил более двух ошибок. Добавляем в черный список.")
                                update_blacklist(chat)
                                break
                            join_attempts += 1
                            print(f"Повторная попытка присоединиться и отправить сообщение ({join_attempts}/{max_join_attempts})...")
                        elif result:
                            break
                    except ChannelPrivateError:
                        print(f"Невозможно подписаться на приватный канал {chat}.")
                        update_blacklist(chat)
                        break
                    except FloodWaitError as e:
                        if mute_count >= 2:
                            print(f"Аккаунт ушел в мут, перемещаем аккаунт и начинаем другую сессию")
                            await client.disconnect()
                            move_session(client.session.filename, 'mute')
                            mute_count = 0
                            return 'flood_wait'
                        mute_count += 1
                        break
                    except ConnectionError as e:
                        print(f"Аккаунт разлогигнен, перемещаем аккаунт и начинаем другую сессию.")
                        await client.disconnect()
                        move_session(client.session.filename, 'razlog')
                        break
                    except PermissionError as e:
                        print('PermissionError', e)
                    except Exception as e:
                        if isinstance(e, ValueError) and "Cannot get entity from a channel (or group)" in str(e):
                            attempt += 1  # Переместите эту строку внутрь условия
                            print(f"Произошла ошибка: {str(e)}. Повторная попытка ({attempt}/{max_attempts})...")
                            if attempt >= max_attempts:
                                print(f"Не удалось обработать чат {chat} после {max_attempts} попыток. Добавляем в черный список.")
                                update_blacklist(chat)
                                break  # добавьте выход из цикла, если превышено количество попыток
                            await asyncio.sleep(DELAY_BEFORE_SENDING)
                        else:
                            print(f"Ошибка при попытке присоединиться или отправить сообщение в {chat}: {type(e).__name__} - {str(e)}")
                            join_attempts += 1
                            print(f"Задержка перед повторной попыткой подписки {DELAY_BEFORE_SUBSCRIPTION} секунд...")
                            await asyncio.sleep(DELAY_BEFORE_SUBSCRIPTION)

                if join_attempts >= max_join_attempts:
                    print(f"Не удалось присоединиться и отправить сообщение в {chat} после {max_join_attempts} попыток.")
                    update_blacklist(chat)

                print(f"Задержка перед сменой группы {DELAY_BEFORE_SENDING} секунд...")
                await asyncio.sleep(DELAY_BEFORE_SENDING)
                break

            except UserBannedInChannelError:
                print(f"Аккаунт забанен в чате {chat}, добавляем в черный список.")
                update_blacklist(chat)
                move_session(client.session.filename, 'ban')
                
                break
            except FloodWaitError as e:
                error_counts[chat] += 1
                if error_counts[chat] >= 2:
                    print(f"Чат {chat} получил более двух ошибок. Добавляем в черный список.")
                    update_blacklist(chat)
                    break
            except InviteRequestSentError:
                error_counts[chat] += 1
                if error_counts[chat] >= 2:
                    print(f"Канал {chat} получил более двух ошибок InviteRequestSentError. Добавляем в черный список.")
                    update_blacklist(chat)
                    break
            except InviteHashExpiredError:  # account in ban
                error_counts[chat] += 1
                if error_counts[chat] >= 2:
                    print(f"Канал {chat} получил более двух ошибок InviteRequestSentError. Добавляем в черный список.")
                    update_blacklist(chat)
                    break
                print(f"Аккаунт в бане у чата.")
                update_blacklist(chat)
                break
            except Exception as e:
                if isinstance(e, ValueError) and "Cannot get entity from a channel (or group)" in str(e):
                    attempt += 1  # Переместите эту строку внутрь условия
                    print(f"Произошла ошибка: {str(e)}. Повторная попытка ({attempt}/{max_attempts})...")
                    if attempt >= max_attempts:
                        print(f"Не удалось обработать чат {chat} после {max_attempts} попыток. Добавляем в черный список.")
                        update_blacklist(chat)
                        break  # добавьте выход из цикла, если превышено количество попыток
                    await asyncio.sleep(DELAY_BEFORE_SENDING)
                else:
                    print(client.session.filename)
                    print(f"Произошла неизвестная ошибка при обработке чата {chat}: {type(e).__name__} - {str(e)}")
                    error_counts[chat] += 1
                    if error_counts[chat] >= 2:
                        print(f"Чат {chat} получил более двух ошибок. Добавляем в черный список.")
                        update_blacklist(chat)
                    break  # добавьте выход из цикла при неизвестной ошибке


# Основная функция для обработки аккаунтов и отправки сообщений
async def main():
    if not os.path.exists(SESSIONS_PATH):
        os.makedirs(SESSIONS_PATH)

    accounts = [os.path.join(SESSIONS_PATH, f) for f in os.listdir(SESSIONS_PATH) if f.endswith('.session')]
    
    cycle_count = 0

    while accounts:
        session_path = accounts.pop(0)

        client = TelegramClient(session_path, api_id, api_hash)


        await client.connect()
        if not (await client.is_user_authorized()):
            print(f"Аккаунт {session_path[9:]} разлогигнен, перемещаем аккаунт и начинаем другую сессию.")
            await client.disconnect()
            move_session(session_path, 'razlog')
            continue

        print(f"Начался цикл: {cycle_count + 1} ")
        print(f"Используется аккаунт: {os.path.basename(session_path)}")
        valid_groups = [chat for chat in groups if chat not in blacklist]
        if not valid_groups:
            print("Group.txt пуст либо все группы находятся в черном списке. Работа скрипта завершена.")
            return
        await process_account(client, valid_groups)
        if client.is_connected():
            await client.disconnect()
        print(f"Задержка перед сменой аккаунта {DELAY_BETWEEN_ACCOUNTS} секунд...")
        time.sleep(DELAY_BETWEEN_ACCOUNTS)

        cycle_count += 1
        if cycle_count >= CYCLES_BEFORE_UNBLACKLIST:
            blacklist.clear()
            with open(BLACKLIST_PATH, 'w', encoding='utf-8') as f:
                f.write('')
            cycle_count = 0
            print("Черный список очищен.")

if __name__ == '__main__':
    asyncio.run(main())