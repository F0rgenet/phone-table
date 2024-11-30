from typing import Optional
from pydantic import BaseModel


class ParentTableInfo(BaseModel):
    table_name: str
    id_column: str
    data_column: str


class ColumnInfo(BaseModel):
    ui_title: str
    db_column: str
    editable: bool = True
    parent_table: Optional[ParentTableInfo] = None


class ColumnsInfo(BaseModel):
    columns: list[ColumnInfo]
