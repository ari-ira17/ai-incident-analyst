import pandas as pd
import openpyxl

# Read original Russian column names from Excel
wb = openpyxl.load_workbook('data/raw/testovy_fayl.xlsx')
ws = wb.active
header = [cell.value for cell in ws[1]]
print('=== КОЛОНКИ (русские названия) ===')
for i, h in enumerate(header):
    print(f'  [{i}] {h}')

print()
print('=== Первые 2 строки (ключевые колонки) ===')
df = pd.read_excel('data/raw/testovy_fayl.xlsx')
for i in range(2):
    print(f'--- Row {i} ---')
    print(f'  [5] {header[5]}: {str(df.iloc[i,5])[:300]}')
    print(f'  [6] {header[6]}: {str(df.iloc[i,6])[:300]}')
    print(f'  [35] {header[35]}: {str(df.iloc[i,35])[:300]}')
    print(f'  [36] {header[36]}: {str(df.iloc[i,36])[:300]}')
    print(f'  [37] {header[37]}: {str(df.iloc[i,37])[:300]}')
    print()