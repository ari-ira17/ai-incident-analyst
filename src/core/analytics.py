# import polars as pl

# class IncidentAnalytics:
#     def __init__(self, df: pl.DataFrame):
#         self.df = df

#     def get_top_regions(self, limit: int = 10) -> pl.DataFrame:
#         """Возвращает датафрейм с топ-N регионами по количеству инцидентов"""
#         return (
#             self.df.group_by("Муниципалитет")
#             .agg(pl.len().alias("count"))
#             .sort("count", descending=True)
#             .head(limit)
#         )

#     def get_region_distribution(self, region: str) -> pl.DataFrame:
#         """Возвращает распределение проблем (в штуках и %) для конкретного региона"""
#         region_df = self.df.filter(pl.col("Муниципалитет") == region)
#         total_incidents = region_df.height
        
#         return (
#             region_df.group_by("Тема")
#             .agg(pl.len().alias("count"))
#             .with_columns(
#                 (pl.col("count") / total_incidents * 100).alias("percentage")
#             )
#             .sort("count", descending=True)
#         )

#     def get_top_problems_with_quotes(self, region: str, top_n: int = 3, quotes_per_problem: int = 2) -> list:
#         """Собирает топ-проблемы и по N цитат для формирования промпта в Ollama"""
#         dist_df = self.get_region_distribution(region).head(top_n)
        
#         result = []
#         # iter_rows() возвращает кортеж, поэтому обращаемся по индексам (0 - Тема, 1 - count, 2 - percentage)
#         for row in dist_df.iter_rows():
#             theme = row[0]
#             percentage = row[2]
            
#             # Извлекаем цитаты
#             quotes = (
#                 self.df.filter(
#                     (pl.col("Муниципалитет") == region) & 
#                     (pl.col("Тема") == theme) &
#                     (pl.col("Текст инцидента").is_not_null())
#                 )
#                 .select("Текст инцидента")
#                 .head(quotes_per_problem)
#                 .to_series()
#                 .to_list()
#             )
            
#             result.append({
#                 "theme": theme,
#                 "percentage": percentage,
#                 "quotes": quotes
#             })
            
#         return result
    

import polars as pl
import os
import json
import ollama

class IncidentAnalytics:
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def get_top_regions(self, limit: int = 10) -> pl.DataFrame:
        """Возвращает датафрейм с топ-N регионами по сумме баллов severity"""
        return (
            self.df.group_by("Муниципалитет")
            .agg(pl.col("severity").sum().alias("Суммы баллов"))
            .sort("Суммы баллов", descending=True)
            .head(limit)
        )

    def get_region_distribution(self, region: str) -> pl.DataFrame:
        """Возвращает распределение проблем (в штуках и %) для конкретного региона"""
        region_df = self.df.filter(pl.col("Муниципалитет") == region)
        total_incidents = region_df.height
        
        if total_incidents == 0:
            return pl.DataFrame()
            
        return (
            region_df.group_by("Тема")
            .agg(pl.len().alias("count"))
            .with_columns(
                (pl.col("count") / total_incidents * 100).alias("percentage")
            )
            .sort("count", descending=True)
        )

    def get_top_problems_with_quotes(self, region: str, top_n: int = 3, quotes_per_problem: int = 2) -> list:
        """Собирает топ-проблемы и по N цитат для формирования промпта в Ollama"""
        dist_df = self.get_region_distribution(region).head(top_n)
        result = []
        
        if dist_df.is_empty():
            return result
            
        for row in dist_df.iter_rows():
            theme = row[0]
            percentage = row[2]
            
            # Извлекаем цитаты
            quotes = (
                self.df.filter(
                    (pl.col("Муниципалитет") == region) & 
                    (pl.col("Тема") == theme) &
                    (pl.col("Текст инцидента").is_not_null())
                )
                .select("Текст инцидента")
                .head(quotes_per_problem)
                .to_series()
                .to_list()
            )
            
            result.append({
                "theme": theme,
                "percentage": percentage,
                "quotes": quotes
            })
            
        return result

    def _prepare_excel_data(self, top_df: pl.DataFrame) -> pl.DataFrame:
        """Вспомогательный метод для формирования структуры листов Excel"""
        rows = []
        for idx, row in enumerate(top_df.iter_rows(named=True), 1):
            mun_name = row["Муниципалитет"]
            score = row["Суммы баллов"]
            
            # Получаем названия самых популярных тем для этого региона
            dist = self.get_region_distribution(mun_name).head(3)
            if not dist.is_empty():
                top_themes = dist["Тема"].to_list()
                themes_str = ", ".join(top_themes)
            else:
                themes_str = "Нет данных"
                
            rows.append({
                "Место": idx,
                "Муниципалитет": mun_name,
                "Суммы баллов": score,
                "Проблемы": themes_str
            })
        return pl.DataFrame(rows)

    def build_reports(self, txt_output_path: str, xlsx_output_path: str):
        """Основной метод генерации документов Excel и текстового отчета через Ollama"""
        # Получаем данные для топ-3 и топ-10
        top_3_raw = self.get_top_regions(3)
        top_10_raw = self.get_top_regions(10)
        
        df_excel_top3 = self._prepare_excel_data(top_3_raw)
        df_excel_top10 = self._prepare_excel_data(top_10_raw)
        
        # 1. Запись многостраничного Excel-файла
        os.makedirs(os.path.dirname(xlsx_output_path), exist_ok=True)
        with pl.ExcelWriter(xlsx_output_path, engine="xlsxwriter") as writer:
            df_excel_top3.write_excel(workbook=writer, sheet_name="Топ-3")
            df_excel_top10.write_excel(workbook=writer, sheet_name="Топ-10")
            
        # 2. Формирование структурированного контекста для Ollama
        ai_prompt_context = "АНАЛИТИЧЕСКИЕ ДАННЫЕ ДЛЯ АНАЛИЗА\n===================================\n\n"
        
        for idx, row in enumerate(top_10_raw.iter_rows(named=True), 1):
            mun_name = row["Муниципалитет"]
            score = row["Суммы баллов"]
            
            ai_prompt_context += f"{idx}. Муниципалитет: {mun_name} (Сумма баллов критичности: {score})\n"
            
            # Извлекаем топ-3 проблемы и по 2 цитаты к каждой
            problems_data = self.get_top_problems_with_quotes(mun_name, top_n=3, quotes_per_problem=2)
            
            for p in problems_data:
                ai_prompt_context += f"   - Проблема: '{p['theme']}' ({p['percentage']:.1f}% от всех инцидентов региона)\n"
                for q_idx, quote in enumerate(p["quotes"], 1):
                    clean_quote = str(quote).strip().replace('\n', ' ')
                    ai_prompt_context += f"     Цитата {q_idx}: \"{clean_quote}\"\n"
            ai_prompt_context += "\n"

        # 3. Запрос к локальной языковой модели
        system_instruction = (
            "Ты — ведущий аналитик государственного ситуационного центра. Твоя задача — изучить агрегированную "
            "статистику по инцидентам и цитаты граждан, после чего составить подробный текстовый аналитический отчет. "
            "Сфокусируйся на выявлении системных проблем в Топ-3 и Топ-10 регионах. Пиши строго в деловом стиле, "
            "избегай вводных фраз, приветствий и заключений."
        )
        
        print("Запрос к локальной модели Ollama...")
        try:
            response = ollama.generate(
                model="llama3", 
                system=system_instruction,
                prompt=f"Сформируй аналитический отчет по следующей информации:\n\n{ai_prompt_context}"
            )
            final_report_text = response["response"]
        except Exception as e:
            final_report_text = f"Ошибка выполнения запроса к Ollama: {str(e)}\n\nСгенерированные данные:\n{ai_prompt_context}"
            
        # 4. Сохранение текстового отчета
        os.makedirs(os.path.dirname(txt_output_path), exist_ok=True)
        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(final_report_text)
            
        return top_10_raw["Муниципалитет"].to_list()
    