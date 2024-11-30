from typing import Dict, Any, List

from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtWidgets import QStyledItemDelegate, QMenu, QTableWidgetItem
from loguru import logger

from database.tables import entries_table, names_table, surnames_table, patronymics_table, streets_table
from ui.table_base import CRUDTableWidget


from modules.generate import generate_entries


class PhoneNumberDelegate(QStyledItemDelegate):
    def _format_phone(self, digits: str) -> str:
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] in ("7", "8"):
            prefix = "+7" if digits[0] == "7" else "8"
            return f"{prefix} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]} {digits[9:]}"
        return digits

    def displayText(self, value: str, locale: Any) -> str:
        try:
            digits = ''.join(filter(str.isdigit, value))
            return self._format_phone(digits)
        except Exception as e:
            logger.error(f"Ошибка при обработке номера телефона: {str(e)}")
            return value

    def setModelData(self, editor, model, index):
        value = editor.text()
        digits = ''.join(filter(str.isdigit, value))
        model.setData(index, digits)


class EntriesTableWidget(CRUDTableWidget):
    def __init__(self):
        self.table = entries_table
        super().__init__(self.table.columns_info)
        
        self._setup_ui()
        self.load_data()
        self._init_delegates()

    def _setup_ui(self) -> None:
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)

    def generate_entries_in_database(self, count: int):
        entries = generate_entries(count)
        names = [{"name": entry["name"]} for entry in entries]
        surnames = [{"surname": entry["surname"]} for entry in entries]
        patronymics = [{"patronymic": entry["patronymic"]} for entry in entries]
        streets = [{"street": entry["street"]} for entry in entries]
        name_ids = [value["name_id"] for value in names_table.create(names)]
        surname_ids = [value["surname_id"] for value in surnames_table.create(surnames)]
        patronymic_ids = [value["patronymic_id"] for value in patronymics_table.create(patronymics)]
        street_ids = [value["street_id"] for value in streets_table.create(streets)]
        for i, entry in enumerate(entries):
            entry["name_id"] = name_ids[i]
            entry["surname_id"] = surname_ids[i]
            entry["patronymic_id"] = patronymic_ids[i]
            entry["street_id"] = street_ids[i]
            entry.pop("name")
            entry.pop("surname")
            entry.pop("patronymic")
            entry.pop("street")
        entries_table.create(entries)
        self.load_data()

    def _init_delegates(self) -> None:
        phone_column = self.get_column_by_db_name("phone")
        if phone_column is not None:
            self.setItemDelegateForColumn(phone_column, PhoneNumberDelegate())
        else:
            logger.warning("Не найдена колонка для отображения телефонных номеров")

    def get_all_db(self) -> List[Dict[str, Any]]:
        return self.table.get_all()

    def create_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.table.create(data)

    def update_db(self, data: Dict[str, Any], target_id: str) -> Dict[str, Any]:
        return self.table.update(data, target_id)

    def delete_db(self, target_id: str) -> None:
        self.table.delete(target_id)

    def duplicate_db(self, item_id: str) -> Dict[str, Any]:
        return self.table.duplicate(item_id)

    def get_default_item_data(self) -> Dict[str, Any]:
        return self.table.get_default_entry_data()

    def update_related_cells(self, parent_table: str, action: str, changed_id: str, new_value: str) -> None:
        """Обработка изменений в родительской таблице"""
        self.load_data()


class ParentTableWidget(CRUDTableWidget):
    data_changed = pyqtSignal(str, str, str, str)

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.table = {
            "names": names_table,
            "surnames": surnames_table,
            "patronymics": patronymics_table,
            "streets": streets_table
        }[table_name]
        
        super().__init__(
            columns_info=self.table.columns_info,
            disabled_actions=["duplicate"]
        )
        self.load_data()

    def get_all_db(self) -> List[Dict[str, Any]]:
        return self.table.get_all()

    def create_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.table.create(data)
        self._emit_data_changed('create', result)
        return result

    def update_db(self, data: dict, target_id: str):
        result = self.table.update(data, target_id)
        if isinstance(result, tuple):
            result_dict = dict(zip(self.table.columns, result[0]))
        else:
            result_dict = result
        self._emit_data_changed('update', result_dict, target_id)
        return result_dict

    def delete_db(self, target_id: str) -> None:
        self.table.delete(target_id)
        self.data_changed.emit(self.table_name, 'delete', str(target_id), '')

    def get_default_item_data(self) -> Dict[str, Any]:
        return {self.columns[1]: "Значение"}

    def _emit_data_changed(self, action: str, data: List[dict], target_id: str = None):
        """Отправляет сигнал об изменении данных в родительской таблице"""
        pass

    def item_updated(self, item: QTableWidgetItem) -> None:
        db_id = self.item(item.row(), 0).text()
        new_value = item.text()
        super().item_updated(item)
        self.data_changed.emit(self.table_name, 'update', db_id, new_value)
