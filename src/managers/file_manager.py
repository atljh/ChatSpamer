import os

from src.console import console

class FileManager:
    @staticmethod
    def read_groups(file='groups.txt') -> list:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return [line.strip().replace("https://", "") for line in f.readlines()]
        except FileNotFoundError:
            console.log("Файл groups.txt не найден", style="bold red")
            return None

    @staticmethod
    def read_post_and_image(post_path="post") -> tuple[str, str | None]:
        post_text = ""
        image_path = None

        post_file_path = os.path.join(post_path, "post.txt")
        try:
            with open(post_file_path, 'r', encoding='utf-8') as f:
                post_text = f.read()
        except FileNotFoundError:
            console.log(f"Файл {post_file_path} не найден", style="bold red")

        image_file_path = os.path.join(post_path, "image.jpg")
        if os.path.exists(image_file_path):
            image_path = image_file_path
        else:
            console.log(f"Изображение {image_file_path} не найдено", style="bold yellow")

        return post_text, image_path
    
    @staticmethod
    def read_blacklist(file='blacklist.txt') -> dict:
        """return {account_phone: [groups]}."""
        blacklist = {}
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                console.log(f"Файл {file} создан, так как он отсутствовал.", style="bold yellow")
            return blacklist
        try:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    phone, group = line.strip().split(':', 1)
                    if phone not in blacklist:
                        blacklist[phone] = []
                    blacklist[phone].append(group)
        except FileNotFoundError:
            console.log("Файл blacklist.txt не найден", style="bold yellow")
        except Exception as e:
            console.log(f"Ошибка при чтении файла {file}: {e}", style="bold red")
        return blacklist
    
    @staticmethod
    def add_to_blacklist(account_phone, group, file='blacklist.txt'):
        try:
            with open(file, 'a', encoding='utf-8') as f:
                f.write(f"{account_phone}:{group}\n")
            console.log(f"Группа {group} добавлена в черный список для аккаунта {account_phone}.", style="yellow")
        except Exception as e:
            console.log(f"Ошибка при добавлении в черный список: {e}", style="red")

    @staticmethod
    def is_group_blacklisted(account_phone, group) -> bool:
        blacklist = FileManager.read_blacklist()
        return group in blacklist.get(account_phone, [])