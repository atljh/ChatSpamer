import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.DEBUG, 
    format="%(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),  
        logging.FileHandler("logs/bot.log", mode="a", encoding="utf-8") 
    ]
)

