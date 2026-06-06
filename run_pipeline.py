import pandas as pd
from src.ingestion.excel_reader import read_excel
from src.ingestion.csv_exporter import save_to_csv
from src.preprocessing.cleaner import IncidentDataCleaner

# INPUT_FILE = "data/raw/test_40.xlsx"
# OUTPUT_FILE = "data/processed/test_40_cleaned.csv"  

INPUT_FILE = "data/raw/тестовый файл.xlsx"
OUTPUT_FILE = "data/processed/тестовый_файл_cleaned.csv" 


def main():
    raw_data = read_excel(INPUT_FILE)

    df = pd.DataFrame(raw_data)
    
    cleaner = IncidentDataCleaner(df)
    cleaned_df = (
        cleaner
        .show_basic_stats()
        .remove_duplicates()
        .convert_duration_column()
        .handle_missing_values()
        .clean_text_formatting()
        .get_dataframe()
    )
    cleaned_data = cleaned_df.to_dict(orient='records')

    save_to_csv(cleaned_data, OUTPUT_FILE)

    print(f"Файл успешно очищен и сохранён: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    