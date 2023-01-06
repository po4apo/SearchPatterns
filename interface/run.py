# -*- coding: utf-8 -*-
import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QCheckBox, QListWidgetItem

import main
from exchange_data import get_currency_pairs_names, get_candle_names
from main import Interval, run_for_ui
from py.main_window import Ui_MainWindow


class LogManger:
    def __init__(self, logsListWidget, log_level=20):
        self.logsListWidget = logsListWidget
        self.log_level = log_level

    def debug(self, msg):
        if self.log_level < 20:
            self.print_to_list_widget(msg)

    def info(self, msg):
        self.print_to_list_widget(msg)

    def print_to_list_widget(self, msg):
        time = datetime.datetime.now().time()
        self.logsListWidget.addItem(f"{time}--{msg}")


class MyWindow(QtWidgets.QWidget, Ui_MainWindow):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.MainWindow = QtWidgets.QMainWindow()
        self.yaml_config = main.Config('./../config.yaml').config
        self.setupUi(self.MainWindow)
        self._logger = LogManger(self.logsListWidget, log_level=self.yaml_config['log_level'])
        self.add_currencies()
        self.add_patterns()

        self.unselectedListWidget.doubleClicked.connect(self.move_to_selected)
        self.selectedListWidget.doubleClicked.connect(self.move_to_unselected)
        self.unselectAllSelectedPushButton.clicked.connect(self.all_selected_to_unselected_list)
        self.selectAllUnselectedPushButton.clicked.connect(self.all_unselected_to_selected_list)
        self.startPushButton.clicked.connect(self.start_search)
        self._logger.info("Программа готова к работе")

    def move_to_selected(self):
        item = self.unselectedListWidget.currentItem()
        list_item = QListWidgetItem(item)
        self.selectedListWidget.addItem(list_item)
        self.unselectedListWidget.takeItem(self.unselectedListWidget.currentRow())

    def move_to_unselected(self):
        item = self.selectedListWidget.currentItem()
        list_item = QListWidgetItem(item)
        self.unselectedListWidget.addItem(list_item)
        self.selectedListWidget.takeItem(self.selectedListWidget.currentRow())

    def all_unselected_to_selected_list(self):
        for item_index in range(0, self.unselectedListWidget.count(), 1):
            list_item = QListWidgetItem(self.unselectedListWidget.item(item_index))
            self.selectedListWidget.addItem(list_item)
        self.unselectedListWidget.clear()

    def all_selected_to_unselected_list(self):
        for item_index in range(0, self.selectedListWidget.count(), 1):
            list_item = QListWidgetItem(self.selectedListWidget.item(item_index))
            self.unselectedListWidget.addItem(list_item)
        self.selectedListWidget.clear()

    def start_search(self):
        self._logger.info('НАЧАЛО РАБОТЫ СКРИПТА.')
        currencies = [self.currencyListWidget.itemWidget(self.currencyListWidget.item(i)) for i in
                      range(0, self.currencyListWidget.count())]

        choose_currencies = []
        for cb in currencies:
            if cb.isChecked():
                choose_currencies.append(cb.text())

        choose_patterns_list = [self.selectedListWidget.item(i).data(1) for i in
                                range(0, self.selectedListWidget.count())]
        choose_patterns_dict = {pattern: get_candle_names().get(pattern) for pattern in choose_patterns_list}

        choose_interval = []
        if self.dailyCheckBox.checkState():
            choose_interval.append(Interval.daily)
        if self.hourlyCheckBox.checkState():
            choose_interval.append(Interval.hourly)

        print(choose_currencies)
        print(choose_patterns_dict)
        print(choose_interval)

        if len(choose_currencies) != 0 and len(choose_patterns_list) != 0 and len(choose_interval) != 0:
            self._logger.info('Процесс запущен. Ожидайте окончания...')
            config = {
                'currencies': choose_currencies,
                'api_keys': self.yaml_config['api_keys']
            }

            self._logger.info('Скрипт выполнен успешно!')
            run_for_ui(config, choose_interval, choose_patterns_dict, ui_logger=self._logger)
        elif len(choose_currencies) == 0:
            self._logger.info("Вылюты не выбраны")
        elif len(choose_patterns_list) == 0:
            self._logger.info("Паттерны не выбраны")
        elif len(choose_interval) == 0:
            self._logger.info("Интервалы не выбраны")
        else:
            self._logger.info("Не ожиданная ошибка ввода данных...")

        self._logger.info('КОНЕЦ РАБОТЫ СКРИПТА.')

    def add_currencies(self):
        currencies = get_currency_pairs_names()
        for currency in currencies:
            box = QCheckBox()  # Instantiate a QCheckBox, it passed into text
            item = QListWidgetItem()
            box.setText(currency)

            self.currencyListWidget.addItem(item)  # The QListWidgetItem join QListWidget
            self.currencyListWidget.setItemWidget(item, box)

    def add_patterns(self):
        patterns = get_candle_names()
        for pattern, names in patterns.items():
            list_item = QListWidgetItem()
            list_item.setText(names[1])
            list_item.setData(1, pattern)
            self.unselectedListWidget.addItem(list_item)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    ui = MyWindow()
    ui.MainWindow.show()
    sys.exit(app.exec_())
