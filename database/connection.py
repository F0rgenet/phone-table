import os
import contextlib

import psycopg
from loguru import logger
from dotenv import load_dotenv


class Connection:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.connection = None

    def connect(self):
        logger.info("Подключение к базе данных...")
        try:
            self.connection = psycopg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.database
            )
            logger.success("Подключение к базе данных успешно выполнено")
        except Exception as exception:
            logger.error(f"Ошибка при подключении к базе данных: {str(exception)}")
            raise
        return True

    @contextlib.contextmanager
    def cursor(self, commit=True) -> psycopg.Cursor:
        if not self.connection:
            logger.warning("Подключение к базе данных ещё не было установлено")
            self.connect()
        cursor = self.connection.cursor()
        try:
            yield cursor
            if commit:
                self.connection.commit()
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {str(e)}")
            self.connection.rollback()
            raise e
        finally:
            cursor.close()
