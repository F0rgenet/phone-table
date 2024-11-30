from database.base import Base
from database.entry import Entry

from database.connection import Connection
from schema.table import ColumnsInfo, ColumnInfo, ParentTableInfo

connection = Connection()
connection.connect()

entries_table = Entry(connection)
entries_table.columns_info = ColumnsInfo(columns=[
    ColumnInfo(ui_title="ID", db_column="entry_id", editable=False),
    ColumnInfo(ui_title="Имя", db_column="name_id",
               parent_table=ParentTableInfo(
                   table_name="names", id_column="name_id", data_column="name")
               ),
    ColumnInfo(ui_title="Фамилия", db_column="surname_id",
               parent_table=ParentTableInfo(
                   table_name="surnames", id_column="surname_id", data_column="surname")
               ),
    ColumnInfo(ui_title="Отчество", db_column="patronymic_id",
               parent_table=ParentTableInfo(
                   table_name="patronymics", id_column="patronymic_id", data_column="patronymic")
               ),
    ColumnInfo(ui_title="Улица", db_column="street_id",
               parent_table=ParentTableInfo(
                   table_name="streets", id_column="street_id", data_column="street")
               ),
    ColumnInfo(ui_title="Дом", db_column="building"),
    ColumnInfo(ui_title="Квартира", db_column="apartment"),
    ColumnInfo(ui_title="Телефон", db_column="phone")
])

names_table = Base("names", ["name_id", "name"], connection, "name_id")
names_table.columns_info = ColumnsInfo(columns=[
    ColumnInfo(ui_title="ID", db_column="name_id", editable=False),
    ColumnInfo(ui_title="Имя", db_column="name")
])
surnames_table = Base("surnames", ["surname_id", "surname"], connection, "surname_id")
surnames_table.columns_info = ColumnsInfo(columns=[
    ColumnInfo(ui_title="ID", db_column="surname_id", editable=False),
    ColumnInfo(ui_title="Фамилия", db_column="surname")
])
patronymics_table = Base("patronymics", ["patronymic_id", "patronymic"], connection, "patronymic_id")
patronymics_table.columns_info = ColumnsInfo(columns=[
    ColumnInfo(ui_title="ID", db_column="patronymic_id", editable=False),
    ColumnInfo(ui_title="Отчество", db_column="patronymic")
])
streets_table = Base("streets", ["street_id", "street"], connection, "street_id")
streets_table.columns_info = ColumnsInfo(columns=[
    ColumnInfo(ui_title="ID", db_column="street_id", editable=False),
    ColumnInfo(ui_title="Улица", db_column="street")
])

tables = {
    "entries": entries_table,
    "names": names_table,
    "surnames": surnames_table,
    "patronymics": patronymics_table,
    "streets": streets_table
}
