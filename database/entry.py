from typing import List, Dict, Tuple, Any

from loguru import logger

from database.base import Base
from database.connection import Connection


class Entry(Base):
    def __init__(self, connection: Connection):
        super().__init__("entries", [
            "entry_id", "name_id", "surname_id", "patronymic_id",
            "street_id", "building", "apartment", "phone"
        ], connection, "entry_id")

    @staticmethod
    def _parse_agg(json_data: List[Dict[str, Any]]):
        if json_data is None:
            return []
        parsed = [(list(item.values())[0], list(item.values())[1]) for item in json_data]
        return sorted(parsed, key=lambda x: x[0])

    def get_all(self) -> List[Dict[str, List[Tuple[int, str]]]]:
        logger.info(f"Получение всех записей из таблицы {self.table_name} со связями")
        with self.connection.cursor(False) as cursor:
            cursor.execute("""
                SELECT 
                    e.entry_id, 
                    n.name_id, 
                    s.surname_id, 
                    p.patronymic_id, 
                    st.street_id, 
                    e.building, 
                    e.apartment, 
                    e.phone
                FROM entries e
                LEFT JOIN names n ON e.name_id = n.name_id
                LEFT JOIN surnames s ON e.surname_id = s.surname_id
                LEFT JOIN patronymics p ON e.patronymic_id = p.patronymic_id
                LEFT JOIN streets st ON e.street_id = st.street_id
            """)
            result = cursor.fetchall()
            clean = []
            for row in result:
                values = []
                for row_value in row:
                    if isinstance(row_value, str):
                        values.append(row_value.strip())
                    elif isinstance(row_value, (tuple, list, set)):
                        cleared_values = [value.strip() if isinstance(value, str) else value for value in row_value]
                        values.append(cleared_values)
                    else:
                        values.append(row_value)
                clean.append(values)

            result = [{
                "entry_id": row[0],
                "name_id": row[1],
                "surname_id": row[2],
                "patronymic_id": row[3],
                "street_id": row[4],
                "building": row[5],
                "apartment": row[6],
                "phone": row[7]
            } for row in clean]
            return result

    def get_default_entry_data(self) -> dict:
        with self.connection.cursor(False) as cursor:
            cursor.execute("""
            SELECT
                (SELECT name_id FROM names ORDER BY name_id LIMIT 1),
                (SELECT surname_id FROM surnames ORDER BY surname_id LIMIT 1),
                (SELECT patronymic_id FROM patronymics ORDER BY patronymic_id LIMIT 1),
                (SELECT street_id FROM streets ORDER BY street_id LIMIT 1),
                '' AS building,
                0 AS apartment,
                79123456789 AS phone
            """)
            result = cursor.fetchone()
        return {
            "name_id": result[0],
            "surname_id": result[1],
            "patronymic_id": result[2],
            "street_id": result[3],
            "building": result[4],
            "apartment": result[5],
            "phone": result[6]
        }

    def duplicate(self, entry_ids: List[str]) -> List[Dict]:
        logger.info(f"Дублирование записей с ID {entry_ids}")
        with self.connection.cursor() as cursor:
            query = """
                INSERT INTO entries (name_id, surname_id, patronymic_id, street_id, building, apartment, phone)
                SELECT 
                    name_id, 
                    surname_id, 
                    patronymic_id, 
                    street_id, 
                    building, 
                    apartment, 
                    phone
                FROM entries
                WHERE entry_id = ANY(%s)
                RETURNING entry_id, name_id, surname_id, patronymic_id, street_id, building, apartment, phone
            """
            cursor.execute(query, (entry_ids,))
            results = cursor.fetchall()
            logger.success(f"Дублирование записей успешно выполнено")
            result_dicts = [
                {
                    "entry_id": result[0],
                    "name_id": result[1],
                    "surname_id": result[2],
                    "patronymic_id": result[3],
                    "street_id": result[4],
                    "building": result[5],
                    "apartment": result[6],
                    "phone": result[7],
                }
                for result in results
            ]
            return result_dicts

