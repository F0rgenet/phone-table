from loguru import logger

from database.connection import Connection


def reset_database():
    connection = Connection()
    connection.connect()
    logger.warning("Сброс базы данных...")
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM entries;
            
            DELETE FROM names;
            DELETE FROM surnames;
            DELETE FROM patronymics;
            DELETE FROM streets;
            
            alter sequence entries_entry_id_seq restart with 1;
            alter sequence names_name_id_seq restart with 1;
            alter sequence patronymics_patronymic_id_seq restart with 1;
            alter sequence streets_street_id_seq restart with 1;
            alter sequence surnames_surname_id_seq restart with 1;
        """)
    logger.success("База данных сброшена")