import pandas as pd

df = pd.read_csv('pet_hospital_data.csv', encoding='utf-8-sig')
df['日期'] = pd.to_datetime(df['日期'])

today = pd.Timestamp('2026-05-19')

rfm = df.groupby('宠主ID').agg({
    '日期': lambda x: (today - x.max()).days,
    '宠主ID': 'count',
    '消费金额': 'sum'
}).rename(columns={'日期': 'R', '宠主ID': 'F', '消费金额': 'M'})

# 查看R值分布
print("R值（最近消费天数）分布：")
print(rfm['R'].value_counts().sort_index())
print(f"\nR > 180 的客户数：{(rfm['R'] > 180).sum()}")
print(f"R <= 180 的客户数：{(rfm['R'] <= 180).sum()}")

# 查看F值分布
print("\nF值（消费次数）分布：")
print(rfm['F'].value_counts().sort_index())

# 查看M值分布
print("\nM值（总消费金额）分布：")
print(rfm['M'].describe())