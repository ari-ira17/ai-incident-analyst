import polars as pl

class IncidentAnalytics:
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def get_top_regions(self, limit: int = 10) -> pl.DataFrame:
        """Возвращает датафрейм с топ-N регионами по количеству инцидентов"""
        return (
            self.df.group_by("Муниципалитет")
            .agg(pl.len().alias("count"))
            .sort("count", descending=True)
            .head(limit)
        )

    def get_region_distribution(self, region: str) -> pl.DataFrame:
        """Возвращает распределение проблем (в штуках и %) для конкретного региона"""
        region_df = self.df.filter(pl.col("Муниципалитет") == region)
        total_incidents = region_df.height
        
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
        # iter_rows() возвращает кортеж, поэтому обращаемся по индексам (0 - Тема, 1 - count, 2 - percentage)
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
    