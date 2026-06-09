import polars as pl
import os
import json
import ollama
import pandas as pd

import docx
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

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

    def build_reports(self, docx_output_path: str, xlsx_output_path: str):
        """Основной метод генерации документов Excel и официального отчета Word по ГОСТ"""
        top_3_raw = self.get_top_regions(3)
        top_10_raw = self.get_top_regions(10)
        
        df_excel_top3 = self._prepare_excel_data(top_3_raw)
        df_excel_top10 = self._prepare_excel_data(top_10_raw)
        
        os.makedirs(os.path.dirname(xlsx_output_path), exist_ok=True)
        with pd.ExcelWriter(xlsx_output_path, engine="xlsxwriter") as writer:
            df_excel_top3.to_pandas().to_excel(writer, sheet_name="Топ-3", index=False)
            df_excel_top10.to_pandas().to_excel(writer, sheet_name="Топ-10", index=False)

        doc = Document()
        
        for section in doc.sections:
            section.top_margin = Cm(2.0)
            section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(3.0)
            section.right_margin = Cm(1.5)

        style_normal = doc.styles['Normal']
        font = style_normal.font
        font.name = 'Times New Roman'
        font.size = Pt(14)
        font.color.rgb = RGBColor(0, 0, 0)
        
        p_format = style_normal.paragraph_format
        p_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        p_format.space_after = Pt(0)
        p_format.space_before = Pt(0)

        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_after = Pt(18)
        run_title = p_title.add_run("АНАЛИТИЧЕСКИЙ ОТЧЕТ СИТУАЦИОННОГО ЦЕНТРА")
        run_title.bold = True
        run_title.font.size = Pt(16)

        system_instruction = (
            "Ты — строгий аналитик. Твоя задача — написать краткое резюме по ОДНОМУ муниципалитету на основе "
            "его проблем и одной цитаты. Никаких вступлений, таблиц или общих выводов. "
            "Используй строго этот шаблон и ничего больше:\n\n"
            "### Регион [Название муниципалитета]\n"
            "- **Проблема:** [Название темы] ([Процент]% от всех инцидентов)\n"
            "  - Стратегические цели:\n"
            "    - Цель для решения проблемы, опираясь на цитату]"
        )

        print("Начинаем генерацию отчета и запись в .docx по ГОСТу...")

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
                raw_text = response["response"].strip()
                
                for line in raw_text.split("\n"):
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                    
                    clean_line_text = clean_line.replace("**", "")
                    
                    if clean_line.startswith("###"):
                        region_title = clean_line_text.replace("###", "").strip()
                        p = doc.add_paragraph()
                        p.paragraph_format.space_before = Pt(12)
                        p.paragraph_format.space_after = Pt(6)
                        p.paragraph_format.keep_with_next = True
                        p.paragraph_format.first_line_indent = Cm(1.25)
                        
                        run = p.add_run(region_title)
                        run.bold = True
                        
                    elif clean_line.startswith("-"):
                        leading_spaces = len(line) - len(line.lstrip())
                        
                        if leading_spaces < 3:
                            p = doc.add_paragraph(style='List Bullet')
                            p.paragraph_format.space_after = Pt(2)
                            p.paragraph_format.left_indent = Cm(1.25)
                            p.add_run(clean_line_text.lstrip("- ").strip())
                        else:
                            p = doc.add_paragraph(style='List Bullet 2')
                            p.paragraph_format.space_after = Pt(2)
                            p.paragraph_format.left_indent = Cm(2.0)
                            p.add_run(clean_line_text.lstrip("- ").strip())
                    else:
                        p = doc.add_paragraph()
                        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        p.paragraph_format.first_line_indent = Cm(1.25)
                        p.paragraph_format.space_after = Pt(4)
                        p.add_run(clean_line_text)
                        
            except Exception as e:
                error_msg = f"Ошибка генерации для {mun_name}: {str(e)}"
                print(error_msg)
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Cm(1.25)
                run_err = p.add_run(f"Ошибка региона {mun_name}: {str(e)}")
                run_err.font.color.rgb = RGBColor(255, 0, 0)

        os.makedirs(os.path.dirname(docx_output_path), exist_ok=True)
        doc.save(docx_output_path)
            
        print("ГОСТ-отчет успешно сформирован и сохранен!")
        return top_10_raw["Муниципалитет"].to_list()
        