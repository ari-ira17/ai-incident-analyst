import polars as pl
import os
import json
import ollama
import pandas as pd

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
        top_3_raw = self.get_top_regions(3)
        top_10_raw = self.get_top_regions(10)
        
        # 1. Формируем Excel
        df_excel_top3 = self._prepare_excel_data(top_3_raw)
        df_excel_top10 = self._prepare_excel_data(top_10_raw)
        
        os.makedirs(os.path.dirname(xlsx_output_path), exist_ok=True)
        with pd.ExcelWriter(xlsx_output_path, engine="xlsxwriter") as writer:
            df_excel_top3.to_pandas().to_excel(writer, sheet_name="Топ-3", index=False)
            df_excel_top10.to_pandas().to_excel(writer, sheet_name="Топ-10", index=False)

        system_instruction = (
            "Ты — строгий аналитик. Твоя задача — написать краткое резюме по ОДНОМУ муниципалитету на основе "
            "его проблем и одной цитаты. Никаких вступлений, таблиц или общих выводов. "
            "Используй строго этот шаблон и ничего больше:\n\n"
            "### Регион [Название муниципалитета]\n"
            "- **Проблема:** [Название темы] ([Процент]% от всех инцидентов)\n"
            "  - Стратегические цели:\n"
            "    - Цель для решения проблемы, опираясь на цитату]"
        )

        final_report_text = "**АНАЛИТИЧЕСКИЙ ОТЧЕТ**\n\n"
        print("Начинаем пошаговую генерацию отчета...")

        for idx, row in enumerate(top_10_raw.iter_rows(named=True), 1):
            mun_name = row["Муниципалитет"]
            print(f"[{idx}/10] Анализ региона: {mun_name}...")
            
            problems_data = self.get_top_problems_with_quotes(mun_name, top_n=3, quotes_per_problem=1)
            
            region_context = f"Муниципалитет: {mun_name}\n"
            for p in problems_data:
                region_context += f"Тема: {p['theme']} ({p['percentage']:.1f}%)\n"
                if p["quotes"]:
                    clean_quote = str(p["quotes"][0]).strip().replace('\n', ' ')
                    region_context += f"Цитата: {clean_quote}\n"
            
            try:
                response = ollama.generate(
                    model="qwen2.5:3b", 
                    system=system_instruction,
                    prompt=f"Данные для анализа:\n{region_context}\n\nВыведи блок отчета для этого региона.",
                    options=None
                )
                final_report_text += response["response"].strip() + "\n\n"
            except Exception as e:
                error_msg = f"Ошибка генерации для {mun_name}: {str(e)}"
                print(error_msg)
                final_report_text += f"### Регион {mun_name}\n{error_msg}\n\n"

        os.makedirs(os.path.dirname(txt_output_path), exist_ok=True)
        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(final_report_text)
            
        print("Отчет успешно сформирован!")
        return top_10_raw["Муниципалитет"].to_list()
    