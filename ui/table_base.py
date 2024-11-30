from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QTableWidget, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QMenu, QAction, QComboBox, QPushButton
)
from loguru import logger

from database.tables import tables
from schema.table import ColumnsInfo, ColumnInfo
from ui.utils import SafeTableInserter


class CRUDTableWidget(QTableWidget):
    def __init__(self, columns_info: ColumnsInfo, disabled_actions: List[str] = None):
        super().__init__()
        self.disabled_actions = disabled_actions or []

        self.headers = [column.ui_title for column in columns_info.columns]
        self.columns = [column.db_column for column in columns_info.columns]
        self.columns_info = columns_info

        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.mousePressEvent = self.handle_mouse_press

        self.create_action = QAction("Создать запись", self)
        self.create_action.triggered.connect(self.create_item)
        self.create_action.setShortcut(QKeySequence(Qt.Key_Insert))
        self.addAction(self.create_action)

        self.duplicate_action = QAction("Дублировать запись", self)
        self.duplicate_action.triggered.connect(lambda: self.duplicate_items(self.get_selected_rows()))
        self.duplicate_action.setShortcut(QKeySequence("CTRL+D"))
        self.addAction(self.duplicate_action)

        self.delete_action = QAction("Удалить запись", self)
        self.delete_action.triggered.connect(lambda: self.delete_items(self.get_selected_rows()))
        self.delete_action.setShortcut(QKeySequence(Qt.Key_Delete))
        self.addAction(self.delete_action)

        actions = {"create": self.create_action, "duplicate": self.duplicate_action, "delete": self.delete_action}
        for name, action in actions.items():
            if name in self.disabled_actions:
                action.setVisible(False)
            else:
                action.setVisible(True)

        self.previous_item_value = None
        self.itemChanged.connect(self.item_updated)
        self.itemPressed.connect(self.save_previous_value)
        self.itemSelectionChanged.connect(self.handle_selection_change)
        self.itemChanged.connect(self.handle_selection_change)

    def save_previous_value(self, item: QTableWidgetItem):
        self.previous_item_value = item.text()

    @staticmethod
    def create_column_combobox_data(column_info: ColumnInfo):
        if not column_info.parent_table:
            raise ValueError(f"Не задана родительская таблица для колонки {column_info.db_column}"
                             f", невозможно создать combobox")

        table = tables[column_info.parent_table.table_name]

        id_column = column_info.parent_table.id_column
        data_column = column_info.parent_table.data_column

        options = [(row[id_column], row[data_column]) for row in table.get_all()]

        combobox_data = {
            "options": options
        }
        return combobox_data

    @property
    def action_name(self):
        if len(self.get_selected_rows()) == 1:
            return "запись"
        return "записи"

    def get_selected_rows(self):
        return [
            row
            for range_ in self.selectedRanges()
            for row in range(range_.topRow(), range_.bottomRow() + 1)
        ]

    def handle_selection_change(self):
        is_enabled = bool(self.get_selected_rows())
        self.duplicate_action.setEnabled(is_enabled)
        self.delete_action.setEnabled(is_enabled)

    def handle_mouse_press(self, event):
        super().mousePressEvent(event)
        self.handle_selection_change()
        self.duplicate_action.setText(f"Дублировать {self.action_name}")
        self.delete_action.setText(f"Удалить {self.action_name}")

        if event.button() != Qt.RightButton:
            return

        menu = QMenu()
        menu.addAction(self.create_action)
        menu.addAction(self.duplicate_action)
        menu.addAction(self.delete_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def item_updated(self, item):
        try:
            row = item.row()
            col = item.column()

            update_data = item.text().strip()
            db_column = self.columns[col]
            db_id = self.item(row, 0).text()

            result = self.update_db({db_column: update_data}, db_id)

            if isinstance(result, dict):
                self.load_data()
        except Exception as e:
            logger.error(f"Ошибка при обновлении записи: {str(e)}")
            self.load_data()
            raise

    def item_selected(self, combobox: QComboBox, item: QTableWidgetItem):
        db_column = self.horizontalHeaderItem(item.column()).data(Qt.UserRole)["db_column"]
        db_id = self.item(item.row(), 0).text()
        update_data = combobox.currentData(Qt.UserRole)
        self.update_db({db_column: update_data}, db_id)

    def create_table_row_items(self, data: Dict[str, tuple | Any]) -> List[QTableWidgetItem | QComboBox]:
        items: List[Optional[QTableWidgetItem | QComboBox]] = [None] * self.columnCount()
        headers = [self.horizontalHeaderItem(i) for i in range(self.columnCount())]
        for db_column, db_value in data.items():
            column_info = next((column for column in self.columns_info.columns if column.db_column == db_column), None)
            header_index, target_header = next((i, header) for i, header in enumerate(headers) if header.data(Qt.UserRole)["db_column"] == db_column)
            header_combobox_data = target_header.data(Qt.UserRole).get("combobox_data")
            if header_combobox_data:
                combobox = QComboBox()
                options = header_combobox_data["options"]
                for option_id, option_value in sorted(options, key=lambda x: x[1]):
                    combobox.addItem(str(option_value), option_id)
                combobox.setCurrentIndex(combobox.findData(db_value))
                items[header_index] = combobox
            else:
                items[header_index] = QTableWidgetItem()
                items[header_index].setData(Qt.DisplayRole, db_value)
            if not column_info.editable:
                items[header_index].setFlags(items[header_index].flags() & ~Qt.ItemIsEditable)

        return items

    def set_filter(self, filter_text: str):
        filter_text = filter_text.strip().lower()
        
        for row in range(self.rowCount()):
            should_hide = True
            if filter_text:
                for col in range(self.columnCount()):
                    cell_widget = self.cellWidget(row, col)
                    if cell_widget and isinstance(cell_widget, QComboBox):
                        cell_text = cell_widget.currentText().lower()
                    else:
                        item = self.item(row, col)
                        cell_text = item.text().lower() if item else ""
                    
                    if filter_text in cell_text:
                        should_hide = False
                        break
            else:
                should_hide = False
            
            self.setRowHidden(row, should_hide)

    def _create_combobox_handler(self, combobox: QComboBox, item: QTableWidgetItem):
        return lambda: self.item_selected(combobox, item)

    def create_table_row(self, data: Dict[str, tuple | Any]) -> int:
        self.setRowCount(self.rowCount() + 1)
        row = self.rowCount() - 1

        with SafeTableInserter(self):
            for col, item in enumerate(self.create_table_row_items(data)):
                if isinstance(item, QComboBox):
                    self.setCellWidget(row, col, item)
                    self.setItem(row, col, QTableWidgetItem(item.currentText()))
                    item.currentIndexChanged.connect(self._create_combobox_handler(item, self.item(row, col)))
                else:
                    self.setItem(row, col, item)

        return row

    def load_headers(self):
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        for i, column_info in enumerate(self.columns_info.columns):
            header_item = self.horizontalHeaderItem(i)
            header_data = {
                "column_info": column_info.dict(),
                "db_column": column_info.db_column
            }
            if column_info.parent_table:
                header_data["combobox_data"] = self.create_column_combobox_data(column_info)
            header_item.setData(Qt.UserRole, header_data)
        logger.success("Загрузка данных заголовков завершена")

    def get_column_info(self, column_index: int) -> ColumnInfo:
        header_data = self.horizontalHeaderItem(column_index).data(Qt.UserRole)
        return ColumnInfo(**header_data["column_info"])

    def get_column_by_db_name(self, db_column: str) -> Optional[int]:
        for i in range(self.columnCount()):
            if self.horizontalHeaderItem(i).data(Qt.UserRole)["db_column"] == db_column:
                return i
        logger.warning(f"Не найдена колонка с именем {db_column} среди "
                       f"{[self.get_column_info(i).db_column for i in range(self.columnCount())]}")
        return None

    def load_data(self):
        logger.info("Загрузка данных...")
        self.clear()
        self.setRowCount(0)
        self.load_headers()

        data = self.get_all_db()
        for i, row in enumerate(data):
            logger.debug(f"Загрузка данных записей {i + 1}/{len(data)}")
            self.create_table_row(row)

    def create_item(self):
        try:
            item_data = self.create_db([self.get_default_item_data()])
        except ValueError as e:
            raise ValueError("Для начала необходимо создать запись в родительских таблицах") from e
        item_data = item_data[0]
        current_column = self.currentColumn()

        item_row = self.create_table_row(item_data)

        editor = self.indexWidget(self.currentIndex())
        if editor:
            self.commitData(editor)

            self.closePersistentEditor(self.currentItem())

            item = self.item(item_row, current_column)

            self.setCurrentItem(item)
            self.editItem(item)

    def delete_items(self, rows: List[int]):
        target_items = [self.item(row, 0).text() for row in rows]
        rows_to_remove = sorted(rows, reverse=True)
        with SafeTableInserter(self):
            for row in rows_to_remove:
                self.model().removeRow(row)

        self.delete_db(target_items)
        self.itemSelectionChanged.emit()
        self.clearSelection()

    def duplicate_items(self, rows: List[int]):
        item_ids = [self.item(row, 0).text() for row in rows]
        data = self.duplicate_db(item_ids)

        self.setUpdatesEnabled(False)
        try:
            with SafeTableInserter(self):
                for row in data:
                    self.create_table_row(row)
        finally:
            self.setUpdatesEnabled(True)
            self.viewport().update()

    def get_all_db(self):
        raise NotImplementedError

    def create_db(self, data: List[dict]):
        raise NotImplementedError

    def update_db(self, data: dict, target_id: str):
        raise NotImplementedError

    def delete_db(self, target_ids: List[str]):
        raise NotImplementedError

    def duplicate_db(self, item_id: List[str]):
        raise NotImplementedError

    def get_default_item_data(self) -> dict:
        raise NotImplementedError
