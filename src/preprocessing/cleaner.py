import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class IncidentDataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def show_basic_stats(self):
        """Выводит базовую статистику (EDA) в консоль."""
        logging.info(f"Размер датасета: {self.df.shape[0]} строк, {self.df.shape[1]} колонок.")
        
        missing_stats = self.df.isnull().sum()
        missing_cols = missing_stats[missing_stats > 0]
        if not missing_cols.empty:
            logging.info(f"Количество пропусков по колонкам:\n{missing_cols}")
        else:
            logging.info("Пропусков в данных не найдено.")
            
        return self

    def remove_duplicates(self):
        """Удаляет полные дубликаты инцидентов."""
        initial_shape = self.df.shape[0]
        subset_cols = [
                "Отдел",
                "Исполнитель",
                "Время с начала создания инцидента до окончания",
                "Текущий шаг инцидента",
                "Группа тем",
                "Тема",
                "Муниципалитет",
                "Тип инцидента",
                "Итог",
                "Текст инцидента"
            ]
        existing_subset = [col for col in subset_cols if col in self.df.columns]
        
        self.df = self.df.drop_duplicates(subset=existing_subset)
        
        dropped = initial_shape - self.df.shape[0]
        if dropped > 0:
            logging.info(f"Удалено дубликатов: {dropped}")
            
        return self

    def filter_incident_types(self):
        """
        Оставляет в датасете только инциденты с типами 'Решаемый' и 'Не решаемый'.
        Игнорирует регистр и лишние пробелы при фильтрации.
        """
        if 'Тип инцидента' in self.df.columns:
            initial_rows = self.df.shape[0]
            
            clean_types = self.df['Тип инцидента'].astype(str).str.lower().str.strip()
            
            mask = clean_types.isin(['решаемый', 'не решаемый'])
            self.df = self.df[mask]
            
            dropped_rows = initial_rows - self.df.shape[0]
            if dropped_rows > 0:
                logging.info(f"Отфильтровано строк по 'Типу инцидента': удалено {dropped_rows} записей.")
        else:
            logging.warning("Колонка 'Тип инцидента' не найдена. Фильтрация не выполнена.")
            
        return self

    def convert_duration_column(self, col_name='Время с начала создания инцидента до окончания'):
        """
        Преобразует указанную колонку в формат timedelta.
        Строки вида '11 days 12:10:25.217000' -> Timedelta.
        """
        if col_name in self.df.columns:
            self.df[col_name] = pd.to_timedelta(self.df[col_name], errors='coerce')
        return self

    def handle_missing_values(self):
        """Обрабатывает пропущенные значения (NaN/NaT) с учётом типов данных."""
        if 'Текст инцидента' in self.df.columns:
            initial_rows = self.df.shape[0]
            self.df = self.df.dropna(subset=['Текст инцидента'])
            dropped_empty_texts = initial_rows - self.df.shape[0]
            if dropped_empty_texts > 0:
                logging.info(f"Удалено строк без текста инцидента: {dropped_empty_texts}")

        time_col = 'Время с начала создания инцидента до окончания'
        if time_col in self.df.columns and pd.api.types.is_timedelta64_dtype(self.df[time_col]):
            self.df[time_col] = self.df[time_col].fillna(pd.Timedelta(0))

        self.df = self.df.fillna("Не указано")
        return self

    def clean_text_formatting(self):
        """Очищает текст от лишних пробелов, табуляций и переносов."""
        if 'Текст инцидента' in self.df.columns:
            self.df['Текст инцидента'] = self.df['Текст инцидента'].astype(str).replace(r'\s+', ' ', regex=True).str.strip()
        return self

    def get_dataframe(self) -> pd.DataFrame:
        """Возвращает очищенный датафрейм."""
        return self.df
    