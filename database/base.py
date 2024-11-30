import contextlib
from typing import List, Optional, Any

from loguru import logger

from database.connection import Connection
from psycopg import errors as psycopg_errors


class Base:
    def __init__(self, table_name: str, columns: List[str], connection: Connection, primary_key: str):
        self.table_name = table_name
        self.connection = connection
        self.columns = columns
        self.primary_key = primary_key

        self.columns_info = None

    @staticmethod
    def _log_query(query: str, params: Optional[List[Any]] = None) -> None:
        """
        Логирование SQL запроса с параметрами

        Args:
            query: SQL запрос
            params: Параметры запроса
        """
        if params:
            try:
                formatted_query = query % tuple(repr(p) for p in params)
            except:
                formatted_query = f"{query} [params: {params}]"
        else:
            formatted_query = query
        logger.debug(f"SQL запрос:\n{formatted_query.strip()}")

    def get_all(self) -> List[dict]:
        logger.info(f"Получение записей из таблицы {self.table_name}")
        with self.exception_handler(), self.connection.cursor() as cur:
            query = f"SELECT {', '.join(self.columns)} FROM {self.table_name}"
            self._log_query(query)
            cur.execute(query)
            result = cur.fetchall()
            logger.debug(f"Получено записей: {len(result)}")
            return [{column: row[i].strip() if isinstance(row[i], str) else row[i]
                     for i, column in enumerate(self.columns)} for row in result]

    def update(self, data: dict, target_id: str) -> tuple:
        logger.info(f"Обновление записи с ID {target_id} и данными {data}")
        columns = list(data.keys())
        values = list(data.values())
        set_expr = ", ".join(f"{col} = %s" for col in columns)
        
        query = f"""
            UPDATE {self.table_name} 
            SET {set_expr} 
            WHERE ({self.primary_key} = %s)
            RETURNING ({self.primary_key}, {", ".join(columns)})
        """
        
        with self.exception_handler(), self.connection.cursor() as cur:
            self._log_query(query, values + [target_id])
            cur.execute(query, values + [target_id])
            result = cur.fetchone()
            logger.debug(f"Обновлено записей: {cur.rowcount}")
            return result

    def delete(self, target_ids: List[str]):
        target_ids = [[target_id] for target_id in target_ids]
        logger.info(f"Удаление записей с ID {target_ids}")
        with self.exception_handler(), self.connection.cursor() as cur:
            query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s"
            self._log_query(query, [target_ids])
            cur.executemany(query, target_ids)
            rows_affected = cur.rowcount
            logger.debug(f"Удалено записей: {rows_affected}")

    def create(self, data_list: List[dict]) -> List[dict]:
        """
        Создаёт новые записи в таблице.

        :param data_list: Список словарей, где ключи - имена колонок, значения - данные для вставки.
        :return: Список созданных записей в виде словарей.
        """
        logger.info(f"Создание новых записей с данными {data_list}")
        if not data_list:
            logger.warning("Передан пустой список данных для создания записей.")
            return []

        keys = data_list[0].keys()
        values = [tuple(record[key] for key in keys) for record in data_list]

        query = (f"INSERT INTO {self.table_name} ({', '.join(keys)}) "
                 f"VALUES {', '.join(['(' + ', '.join(['%s'] * len(keys)) + ')' for _ in data_list])} "
                 f"RETURNING {self.primary_key}, {', '.join(keys)}")

        flattened_values = [value for record in values for value in record]

        with self.exception_handler(), self.connection.cursor() as cur:
            cur.execute(query, flattened_values)
            results = cur.fetchall()
            result_dicts = [{column: value for column, value in zip([self.primary_key] + list(keys), result)} for result in results]
            return result_dicts


    @contextlib.contextmanager
    def exception_handler(self):
        """Расширенный обработчик исключений для операций с БД"""
        try:
            yield
        except psycopg_errors.UniqueViolation as e:
            logger.error(f"Нарушение уникальности: {e.diag.message_detail if hasattr(e.diag, 'message_detail') else str(e)}")
            raise ValueError("Нарушение уникальности значения") from e
        except psycopg_errors.ForeignKeyViolation as e:
            logger.error(f"Нарушение внешнего ключа: {e.diag.message_detail if hasattr(e.diag, 'message_detail') else str(e)}")
            raise ValueError("Нарушение ссылочной целостности") from e
        except psycopg_errors.NotNullViolation as e:
            logger.error(f"Попытка записи NULL в NOT NULL поле: {e.diag.message_detail if hasattr(e.diag, 'message_detail') else str(e)}")
            raise ValueError("Обязательное поле не может быть пустым") from e
        except psycopg_errors.NumericValueOutOfRange as e:
            logger.error(f"Значение вне допустимого диапазона: {str(e)}")
            raise ValueError("Значение вне допустимого диапазона") from e
        except Exception as e:
            logger.error(f"Неожиданная ошибка при работе с БД: {str(e)}")
            raise
