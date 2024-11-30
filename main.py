import sys

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QRect
from PyQt5.QtGui import QKeySequence, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QMenu, QStackedWidget, QMessageBox, \
    QAction, QInputDialog, QLabel, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy
from loguru import logger
from pyqtexcept_forgenet.main import create_exceptions_hook

from modules.reset import reset_database
from ui.table import EntriesTableWidget, ParentTableWidget


class SearchWidget(QWidget):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.setFixedWidth(200)
        self.search_line_edit = QLineEdit()
        self.search_line_edit.setPlaceholderText("Поиск...")
        self.search_line_edit.textEdited.connect(self.search)
        layout = QHBoxLayout(self)
        layout.addWidget(self.search_line_edit)

    def search(self):
        self.table.set_filter(self.search_line_edit.text())


class ParentControlWidget(QWidget):
    def __init__(self, table_name: str):
        super().__init__()
        self.table = ParentTableWidget(table_name)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)


def get_action_button(action: QAction) -> QPushButton:
    def checkout_properties():
        logger.debug(f"Проверка состояния кнопки для действия {action.text()}")
        button.setVisible(action.isVisible())
        button.setEnabled(action.isEnabled())
        button.setText(action.text())
    button = QPushButton(action.text())
    button.pressed.connect(action.trigger)
    action.changed.connect(checkout_properties)
    return button


class EntryControlWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.table = EntriesTableWidget()
        layout = QVBoxLayout(self)

        control_panel_layout = QHBoxLayout()
        search_widget = SearchWidget(self.table)
        control_panel_layout.addWidget(search_widget)

        create_button = get_action_button(self.table.create_action)
        control_panel_layout.addWidget(create_button)

        delete_button = get_action_button(self.table.delete_action)
        control_panel_layout.addWidget(delete_button)
        delete_button.setEnabled(False)

        duplicate_button = get_action_button(self.table.duplicate_action)
        control_panel_layout.addWidget(duplicate_button)
        duplicate_button.setEnabled(False)

        layout.addLayout(control_panel_layout)
        layout.addWidget(self.table)


class ParentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(400)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.close_action = QAction("Закрыть", self)
        self.close_action.triggered.connect(self.close)
        self.close_action.setShortcut(QKeySequence(Qt.Key_Escape))
        self.addAction(self.close_action)

        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu("&Файл")
        self.file_menu.addAction(self.close_action)


    def add_widget(self, widget: QWidget, name: str):
        self.stacked_widget.addWidget(widget)
        self.stacked_widget.setCurrentWidget(widget)
        self.setWindowTitle(name)

    def switch_widget(self, widget: QWidget, name: str):
        self.stacked_widget.setCurrentWidget(widget)
        self.setWindowTitle(name)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Телефонный справочник")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.entries_widget = EntryControlWidget()
        layout.addWidget(self.entries_widget)

        self.parent_window = ParentWindow()
        self.parent_widgets = {}

        menu_bar = self.menuBar()
        tables_menu = QMenu("&Таблицы", self)
        tables_menu.addAction("&Имена", lambda: self.open_parent_widget("names", "Имена"))
        tables_menu.addAction("&Фамилии", lambda: self.open_parent_widget("surnames", "Фамилии"))
        tables_menu.addAction("&Отчества", lambda: self.open_parent_widget("patronymics", "Отчества"))
        tables_menu.addAction("&Улицы", lambda: self.open_parent_widget("streets", "Улицы"))
        menu_bar.addMenu(tables_menu)

        settings_menu = QMenu("&Утилиты", self)
        settings_menu.addAction("&Заполнить базу данных", self.fill_database_dialog)
        settings_menu.addAction("&Сброс базы данных", self.reset_database_dialog)
        menu_bar.addMenu(settings_menu)

    def fill_database_dialog(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Заполнить базу данных")
        dialog.setLabelText("База данных будет заполнена случайно сгенерированными данными.\n\nКоличество записей:")
        dialog.setInputMode(QInputDialog.IntInput)
        dialog.setIntRange(0, int(1e6))
        dialog.setIntValue(0)

        label = dialog.findChild(QLabel)
        if label:
            label.setWordWrap(True)

        dialog.setOkButtonText("Заполнить")
        dialog.setCancelButtonText("Отмена")

        if dialog.exec_():
            count = dialog.intValue()
            logger.info(f"Заполнение базы данных начато. Количество записей: {count}")
            self.entries_widget.table.generate_entries_in_database(count)

    def reset_database_dialog(self):
        approval = QMessageBox(QMessageBox.Warning, "Вы уверены?", "Сброс базы данных", QMessageBox.Yes | QMessageBox.No)
        approval.setDefaultButton(QMessageBox.No)
        approval.button(QMessageBox.Yes).setText("Да")
        approval.button(QMessageBox.No).setText("Нет")

        chosen_variant = approval.exec()
        if chosen_variant == QMessageBox.Yes:
            reset_database()
            self.entries_widget.table.load_data()

    def open_parent_widget(self, table_name: str, title: str):
        if table_name not in self.parent_widgets:
            widget = ParentControlWidget(table_name)
            widget.table.data_changed.connect(self.on_parent_data_changed)
            self.parent_widgets[table_name] = widget
            self.parent_window.add_widget(widget, title)
        else:
            widget = self.parent_widgets[table_name]
            self.parent_window.switch_widget(widget, title)

        widget.table.load_data()

        self.parent_window.show()
        self.parent_window.activateWindow()

    def on_parent_data_changed(self, table_name: str, action: str, changed_id: str, new_value: str) -> None:
        self.entries_widget.table.update_related_cells(
            parent_table=table_name,
            action=action,
            changed_id=changed_id,
            new_value=new_value
        )


def main():
    app = QApplication(sys.argv)
    window = App()
    sys.excepthook = create_exceptions_hook(window, True)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()