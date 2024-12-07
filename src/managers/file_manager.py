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
