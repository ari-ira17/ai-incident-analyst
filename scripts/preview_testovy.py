import pandas as pd

df = pd.read_excel('data/raw/testovy_fayl.xlsx')
print('Shape:', df.shape)
print('Columns:', list(df.columns))
print()

# Print first 3 rows with all columns
for i in range(min(3, len(df))):
    print(f'--- Row {i} ---')
    for col in df.columns:
        val = str(df.iloc[i][col])
        # Clean emoji and non-ASCII for display
        clean_val = val.encode('utf-8', errors='ignore').decode('utf-8')[:200]
        print(f'  {col}: {clean_val}')
    print()