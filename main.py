import copy
import datetime
import enum
import threading
import time
import traceback

import yaml
from pathlib import PurePath
import requests
import pandas as pd
import talib
import openpyxl
import logging
from enum import Enum


class Interval(Enum):
    hourly = 7
    daily = 30


class Config:
    """
    Класс предоставляет доступ к конфигурационному файлу.
    При помощи метода _load_config программа получает доступ
    к файлу и конвертирует его в словарь.
    """
    def __init__(self, path):
        self._logger = logging.getLogger('config')
        self.path = path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        with open(self.path) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
            self._logger.info('Config has loaded successfully')
            self._logger.debug(yaml.dump(config))
        return config


class Exchange:
    """
    Класс предоставляет возможность получение данных от биржи.
    Метод get_data является основным и возвращает словарь json-файлов,
    где ключ является валютой.
    _build_query - приватный метод необходимый для генерации запросов
    в зависимости от параметров.
    """
    def __init__(self, exchange_config):
        self._logger = logging.getLogger('exchange')
        self.exchange_config = exchange_config
        self.currencies = self.exchange_config['currencies']
        self.api_keys = self.exchange_config['api_keys']
        self._url = "https://marketdata.tradermade.com/api/v1/timeseries"

    def get_data(self, interval: Interval):
        raw_historical_data = dict()
        # test without copy
        currencies = copy.copy(self.currencies)
        for api_key in self.api_keys:
            try:
                while len(currencies) != 0:
                    currency = currencies.pop()
                    query = self._build_query(interval, currency, api_key)
                    response = requests.get(self._url, params=query)
                    self._logger.info(f'Response code for {interval}-{currency}: {response.status_code}')
                    self._logger.debug(f'{response.text}')
                    raw_historical_data[currency] = response.json()
            except Exception as ex:
                self._logger.error(traceback.print_tb(ex.__traceback__))
        return raw_historical_data

    def _build_query(self, interval: Interval, currency, api_key) -> dict:
        today = datetime.date.today()

        query = {
            "currency": currency,
            "api_key": api_key,
            "start_date": str(today - datetime.timedelta(days=interval.value)),
            "end_date": str(today),
            "format": "records",
            "interval": interval.name,
            "period": 1
        }
        self._logger.debug(f'{query=}')
        return query


class Analyzer:
    """
    Основной класс программы нужен для анализа полученных с биржи данных.
    В gen_results полученные сырые данные распаковываются и предаются в метод
    search_pattern в нем при помощи библиотеки TA-lib происходит поиск свечных паттернов.
    После нахождение паттернов для полученных данных выполняется функция clear_data, она
    как понятно из называния возыварщает ощиченные от пустых полей данные.
    """
    def __init__(self):
        self._logger = logging.getLogger('analyzer')
        self.bearish = "Нисходящий тренд"
        self.bullish = "Восходящий тренд"
        self.candle_names = talib.get_function_groups()['Pattern Recognition']

    def gen_results(self, row_historical_dict, interval: Interval):
        start_time = datetime.datetime.now().strftime("%d_%m_%Y--%H_%M_%S")
        for currency, data in row_historical_dict.items():
            # candlestick_pattern_search_results
            candle_patterns_sr = self.search_pattern(data)
            self._logger.info(f'Patterns for {interval}-{currency} has founded')
            self._logger.debug(f'{candle_patterns_sr}')
            cleaned_candle_patterns_sr = self.clear_data(candle_patterns_sr)
            self._logger.info(f'Patterns for {interval}-{currency} has cleaned')
            self._logger.debug(f'{cleaned_candle_patterns_sr}')
            cleaned_candle_patterns_sr.to_excel(PurePath(f'reports/{interval.name}_{currency}-{start_time}.xlsx'))
            self._logger.info(f'reports/{interval.name}_{currency}-{start_time}.xlsx has created')

    def search_pattern(self, row_historical_data):
        hd = pd.DataFrame(row_historical_data["quotes"],
                          columns=['date','close', 'high', 'low', 'open'],
                          )
        quotes = [hd['open'], hd['close'], hd['high'], hd['low']]

        candle_patterns_sr = copy.copy(hd)
        for candle in self.candle_names:
            candle_patterns_sr[candle] = getattr(talib, candle)(*quotes)

        return candle_patterns_sr

    def clear_data(self, candle_patterns_sr):
        candle_patterns_sr.drop('open', axis=1, inplace=True)
        candle_patterns_sr.drop('high', axis=1, inplace=True)
        candle_patterns_sr.drop('low', axis=1, inplace=True)
        candle_patterns_sr.drop('close', axis=1, inplace=True)

        for i in candle_patterns_sr.index:
            for candle_name in self.candle_names:
                if candle_patterns_sr.loc[i, candle_name] == -100:
                    candle_patterns_sr.loc[i, candle_name] = self.bearish
                if candle_patterns_sr.loc[i, candle_name] == 100:
                    candle_patterns_sr.loc[i, candle_name] = self.bullish

        for index in range(len(candle_patterns_sr) - 1, -1, -1):
            row = candle_patterns_sr.iloc[index].to_list()
            if self.bearish in row or self.bullish in row:
                continue
            else:
                candle_patterns_sr = candle_patterns_sr.drop(index)

        for name in self.candle_names:
            col = list(candle_patterns_sr[name])
            if self.bearish in col or self.bullish in col:
                continue
            else:
                candle_patterns_sr.pop(name)

        return candle_patterns_sr


if __name__ == '__main__':
    def run_parser(interval: Interval):
        """
        Функция объединяет в себе все классы и нужна для работы скрипта в многопоточном режиме.
        Так же с её помощью реализовано ожидание обновления.
        :param interval:
        :return:
        """
        config = Config(PurePath('./config.yaml')).config
        logging.basicConfig(level=config['log_level'])
        main_logger = logging.getLogger('runner')

        exchange = Exchange(config)
        analyzer = Analyzer()
        main_logger.info(f'Start {interval.name} loop')
        while True:
            raw_historical_data = exchange.get_data(interval)
            analyzer.gen_results(raw_historical_data, interval)
            time_now = datetime.datetime.utcnow()
            if interval == Interval.hourly:
                left_min_until_next_hour = 59 - time_now.minute
                left_sec_until_next_hour = 59 - time_now.second
                left = left_min_until_next_hour * 60 + left_sec_until_next_hour
                main_logger.info(f'Next {interval.name} report will be crated through {left} sec')
                time.sleep(left)
            elif interval == Interval.daily:
                left_hour_until_next_day = 23 - time_now.hour
                left_min_until_next_day = 59 - time_now.minute
                left_sec_until_next_day = 59 - time_now.second
                left = (left_hour_until_next_day * 3600) + (left_min_until_next_day * 60) + left_sec_until_next_day
                main_logger.info(f'Next {interval.name} report will be crated through {left} sec')
                time.sleep(left)
            else:
                raise f'{interval.name} - invalid interval'


    hourly_thread = threading.Thread(target=run_parser, args=[Interval.hourly])
    daily_thread = threading.Thread(target=run_parser, args=[Interval.daily])

    hourly_thread.start()
    daily_thread.start()

