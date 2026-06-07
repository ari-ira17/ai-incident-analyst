import pandas as pd
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class IncidentDataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def show_basic_stats(self):
        logging.info(f"Размер датасета: {self.df.shape[0]} строк, {self.df.shape[1]} колонок.")
        
        missing_stats = self.df.isnull().sum()
        missing_cols = missing_stats[missing_stats > 0]
        if not missing_cols.empty:
            logging.info(f"Количество пропусков по колонкам:\n{missing_cols}")
        else:
            logging.info("Пропусков в данных не найдено.")
            
        return self

    def remove_duplicates(self):
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

    def convert_duration_column(self, col_name='Время с начала создания инцидента до окончания'):
        if col_name in self.df.columns:
            self.df[col_name] = pd.to_timedelta(self.df[col_name], errors='coerce')
        return self

    def handle_missing_values(self):
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
        if 'Текст инцидента' in self.df.columns:
            self.df['Текст инцидента'] = self.df['Текст инцидента'].astype(str).replace(r'\s+', ' ', regex=True).str.strip()
        return self

    def optimize_text_for_llm(self):
        if 'Текст инцидента' not in self.df.columns:
            return self

        # Список мусорных слов, которые не несут смысла для классификации
        stop_words = {
            "здравствуйте", "добрый", "день", "вечер", "пожалуйста", "прошу", "вас", 
            "уважаемый", "меня", "мы", "наш", "мне", "свои", "который", "чтобы", 
            "очень", "уже", "администрация", "подскажите", "жалоба", "обращение"
        }

        def process_text(text):
            # Переводим в нижний регистр и оставляем только слова и цифры (убираем знаки препинания)
            words = re.findall(r'[а-яёa-z0-9]+', text.lower())
            # Фильтруем текст, удаляя слова из списка stop_words
            filtered_words = [w for w in words if w not in stop_words]
            return " ".join(filtered_words)

        logging.info("Запущена очистка текста от мусорных слов...")
        self.df['Текст инцидента'] = self.df['Текст инцидента'].astype(str).apply(process_text)
        return self

    def get_dataframe(self) -> pd.DataFrame:
        return self.df
