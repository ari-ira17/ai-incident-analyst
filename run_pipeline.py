from src.ingestion.excel_reader import read_excel
from src.ingestion.csv_exporter import save_to_csv

INPUT_FILE = "data/raw/test_40.xlsx"

OUTPUT_FILE = "data/processed/test_40.csv"


def main():

    data = read_excel(INPUT_FILE)

    save_to_csv(data, OUTPUT_FILE)

    print(f"Файл сохранён: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()