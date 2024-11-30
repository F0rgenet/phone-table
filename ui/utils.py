from PyQt5.QtWidgets import QTableWidget


class SafeTableInserter:
    """
    Контекстный менеджер для безопасного добавления данных в QTableWidget.

    :param table: Объект QTableWidget, в который добавляются данные.
    """
    def __init__(self, table: QTableWidget):
        if not isinstance(table, QTableWidget):
            raise TypeError("SafeTableInserter работает только с QTableWidget.")
        self.table = table
        self.sorting_enabled = table.isSortingEnabled()
        self.updates_blocked = table.signalsBlocked()
        self.edit_triggers = table.editTriggers()

    def __enter__(self):
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        return self.table

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.table.setSortingEnabled(self.sorting_enabled)
        self.table.blockSignals(self.updates_blocked)
        self.table.setEditTriggers(self.edit_triggers)
        if exc_type is not None:
            print(f"Ошибка при добавлении данных: {exc_type}, {exc_val}")