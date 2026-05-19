import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import PieChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from datetime import datetime

print("=" * 50)
print("正在生成经营看板...")
print("=" * 50)

# ========== 读取数据 ==========
df = pd.read_csv('pet_hospital_data.csv', encoding='utf-8-sig')
df['日期'] = pd.to_datetime(df['日期'])

# ========== 基础指标 ==========
today = datetime(2026, 5, 19)
total_customers = df['宠主ID'].nunique()
total_orders = len(df)
total_revenue = df['消费金额'].sum()
avg_ticket = total_revenue / total_orders

print(f"总客户数：{total_customers:,}人")
print(f"总订单数：{total_orders:,}笔")
print(f"总营收：{total_revenue:,.0f}元 ({total_revenue / 10000:.1f}万)")

# ========== 计算每个客户指标 ==========
last_visit = df.groupby('宠主ID')['日期'].max().reset_index()
last_visit['R'] = last_visit['日期'].apply(lambda x: (today - x).days)

freq = df.groupby('宠主ID').size().reset_index(name='F')
amount = df.groupby('宠主ID')['消费金额'].sum().reset_index(name='M')

customer_data = last_visit.merge(freq, on='宠主ID').merge(amount, on='宠主ID')
customer_data = customer_data.merge(df[['宠主ID', '宠主姓名']].drop_duplicates(), on='宠主ID')

# 获取每个客户最近一次的消费金额
last_amount = df.loc[df.groupby('宠主ID')['日期'].idxmax(), ['宠主ID', '消费金额']]
customer_data = customer_data.merge(last_amount, on='宠主ID')
customer_data = customer_data.rename(columns={'消费金额': '最近消费金额'})


# 分层规则
def classify_customer(row):
    R = row['R']
    if R <= 30:
        return '高价值客户'
    elif R <= 90:
        return '活跃客户'
    elif R <= 180:
        return '沉睡客户'
    else:
        return '流失客户'


customer_data['分层'] = customer_data.apply(classify_customer, axis=1)

# ========== 流失客户（关键修复点）==========
# 确保流失客户正确筛选
lost_customers = customer_data[customer_data['R'] > 180].copy()
lost_rate = len(lost_customers) / total_customers

print(f"\n流失客户数：{len(lost_customers)}人")
print(f"流失率：{lost_rate * 100:.1f}%")

# 验证流失客户是否有数据
if len(lost_customers) == 0:
    print("⚠️ 警告：流失客户数为0，请检查数据！")
else:
    print(f"✓ 流失客户列表已生成，共{len(lost_customers)}人")

# 服务项目分析
service_stats = df.groupby('服务项目').agg({
    '消费金额': ['sum', 'mean'],
    '宠主ID': 'count'
}).round(2)
service_stats.columns = ['总金额', '客单价', '订单数']
service_stats = service_stats.sort_values('总金额', ascending=False)
service_stats['金额占比'] = (service_stats['总金额'] / service_stats['总金额'].sum() * 100).round(1)

# 医生绩效
doctor_stats = df.groupby('医生').agg({
    '宠主ID': 'count',
    '消费金额': ['sum', 'mean']
}).round(2)
doctor_stats.columns = ['接诊量', '总业绩', '客单价']
doctor_stats = doctor_stats.sort_values('接诊量', ascending=False)

# ========== 创建Excel ==========
wb = Workbook()
wb.remove(wb.active)

# ----- 1. Dashboard 看板 -----
ws1 = wb.create_sheet('Dashboard')

# 标题
ws1['A1'] = '宠物医院经营分析看板'
ws1['A1'].font = Font(size=18, bold=True)
ws1.merge_cells('A1:I1')

# 副标题
ws1['A2'] = f'数据周期：2025-01-01 至 2025-12-31 | 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}'
ws1.merge_cells('A2:I2')
ws1['A2'].font = Font(size=10, color='666666')

# KPI卡片区域
kpi_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
kpi_font = Font(color='FFFFFF', bold=True, size=11)

kpi_labels = ['总客户数', '总营收(万)', '流失率', '整体客单价', '总订单数']
kpi_values = [
    f"{total_customers:,}人",
    f"{total_revenue / 10000:.1f}万",
    f"{lost_rate * 100:.1f}%",
    f"{avg_ticket:.0f}元",
    f"{total_orders:,}笔"
]

for idx, (col, label, value) in enumerate(zip(['A', 'C', 'E', 'G', 'I'], kpi_labels, kpi_values)):
    # 标签
    cell = ws1[f'{col}4']
    cell.value = label
    cell.fill = kpi_fill
    cell.font = kpi_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                         bottom=Side(style='thin'))
    ws1.merge_cells(f'{col}4:{chr(ord(col) + 1)}4')

    # 数值
    cell2 = ws1[f'{col}5']
    cell2.value = value
    cell2.font = Font(size=14, bold=True)
    cell2.alignment = Alignment(horizontal='center', vertical='center')
    ws1.merge_cells(f'{col}5:{chr(ord(col) + 1)}5')

# 设置KPI行高
ws1.row_dimensions[4].height = 25
ws1.row_dimensions[5].height = 30

# 客户分层饼图
ws1['A8'] = '客户分层分析'
ws1['A8'].font = Font(size=12, bold=True)

layer_counts = customer_data['分层'].value_counts()
# 确保分层顺序固定
layer_order = ['高价值客户', '活跃客户', '沉睡客户', '流失客户']
for i, layer in enumerate(layer_order):
    count = layer_counts.get(layer, 0)
    pct = count / total_customers * 100
    ws1[f'A{10 + i}'] = layer
    ws1[f'B{10 + i}'] = count
    ws1[f'C{10 + i}'] = f'{pct:.1f}%'

# 添加标题行
ws1['A9'] = '分层'
ws1['B9'] = '人数'
ws1['C9'] = '占比'
for col in ['A9', 'B9', 'C9']:
    ws1[col].font = Font(bold=True)
    ws1[col].fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')

# 饼图
pie = PieChart()
pie.title = '客户分层占比'
pie.width = 10
pie.height = 7
data = Reference(ws1, min_col=2, min_row=9, max_row=9 + len(layer_order))
labels = Reference(ws1, min_col=1, min_row=10, max_row=9 + len(layer_order))
pie.add_data(data, titles_from_data=True)
pie.set_categories(labels)
ws1.add_chart(pie, 'E8')

# 服务项目分析表格
ws1['A18'] = '服务项目盈利分析'
ws1['A18'].font = Font(size=12, bold=True)

service_headers = ['服务项目', '总金额(元)', '订单数', '客单价(元)', '金额占比']
for col_idx, header in enumerate(service_headers):
    cell = ws1.cell(row=19, column=col_idx + 1, value=header)
    cell.fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
    cell.font = Font(color='FFFFFF', bold=True)

for i, (service, row_data) in enumerate(service_stats.iterrows()):
    ws1.cell(row=20 + i, column=1, value=service)
    ws1.cell(row=20 + i, column=2, value=f"{row_data['总金额']:,.0f}")
    ws1.cell(row=20 + i, column=3, value=row_data['订单数'])
    ws1.cell(row=20 + i, column=4, value=f"{row_data['客单价']:.0f}")
    ws1.cell(row=20 + i, column=5, value=f"{row_data['金额占比']}%")

# 医生绩效表格
ws1['F18'] = '医生绩效排名'
ws1['F18'].font = Font(size=12, bold=True)

doctor_headers = ['医生', '接诊量', '总业绩(万)', '客单价(元)']
for col_idx, header in enumerate(doctor_headers):
    cell = ws1.cell(row=19, column=6 + col_idx, value=header)
    cell.fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
    cell.font = Font(color='FFFFFF', bold=True)

for i, (doctor, row_data) in enumerate(doctor_stats.iterrows()):
    ws1.cell(row=20 + i, column=6, value=doctor)
    ws1.cell(row=20 + i, column=7, value=row_data['接诊量'])
    ws1.cell(row=20 + i, column=8, value=f"{row_data['总业绩'] / 10000:.1f}")
    ws1.cell(row=20 + i, column=9, value=f"{row_data['客单价']:.0f}")

# 设置列宽
ws1.column_dimensions['A'].width = 12
ws1.column_dimensions['B'].width = 10
ws1.column_dimensions['C'].width = 10
ws1.column_dimensions['D'].width = 14
ws1.column_dimensions['E'].width = 12
ws1.column_dimensions['F'].width = 10
ws1.column_dimensions['G'].width = 10
ws1.column_dimensions['H'].width = 14
ws1.column_dimensions['I'].width = 12

# ----- 2. 流失客户列表（修复：确保数据写入）-----
ws2 = wb.create_sheet('流失客户列表')
ws2['A1'] = f'流失客户预警（超过6个月未消费）- 共{len(lost_customers)}人'
ws2['A1'].font = Font(size=12, bold=True)

lost_headers = ['宠主ID', '宠主姓名', '最近消费日期', '最近消费金额', '总消费次数', '总消费金额', '未登录天数']
for col_idx, header in enumerate(lost_headers):
    cell = ws2.cell(row=2, column=col_idx + 1, value=header)
    cell.fill = PatternFill(start_color='E74C3C', end_color='E74C3C', fill_type='solid')
    cell.font = Font(color='FFFFFF', bold=True)

# 关键修复：逐行写入流失客户数据
if len(lost_customers) > 0:
    for i, (idx, row) in enumerate(lost_customers.iterrows()):
        ws2.cell(row=3 + i, column=1, value=row['宠主ID'])
        ws2.cell(row=3 + i, column=2, value=row['宠主姓名'])
        ws2.cell(row=3 + i, column=3, value=row['日期'].strftime('%Y-%m-%d'))
        ws2.cell(row=3 + i, column=4, value=row['最近消费金额'])
        ws2.cell(row=3 + i, column=5, value=row['F'])
        ws2.cell(row=3 + i, column=6, value=row['M'])
        ws2.cell(row=3 + i, column=7, value=row['R'])

    print(f"✓ 已写入 {len(lost_customers)} 个流失客户到Excel")
else:
    ws2['A3'] = '无流失客户'
    print("⚠️ 流失客户列表为空")

# 自动调整列宽
for col in ws2.columns:
    max_length = 0
    col_letter = col[0].column_letter
    for cell in col:
        try:
            if cell.value and len(str(cell.value)) > max_length:
                max_length = len(str(cell.value))
        except:
            pass
    adjusted_width = min(max_length + 2, 20)
    ws2.column_dimensions[col_letter].width = adjusted_width

# ----- 3. 原始数据（抽样）-----
ws3 = wb.create_sheet('原始数据_抽样')
sample_df = df.sample(min(5000, len(df)), random_state=42).sort_values('日期')
for r in dataframe_to_rows(sample_df, index=False, header=True):
    ws3.append(r)
ws3['A1'] = f'原始数据抽样（共{len(df)}条，随机展示5000条）'
ws3.merge_cells('A1:H1')

# 保存
wb.save('宠物医院经营看板_最终版.xlsx')

print("\n" + "=" * 50)
print("✅ 看板生成成功：宠物医院经营看板_最终版.xlsx")
print("=" * 50)
print(f"\n📊 数据概览：")
print(f"   - 总客户数：{total_customers:,}人")
print(f"   - 总订单数：{total_orders:,}笔")
print(f"   - 总营收：{total_revenue / 10000:.1f}万")
print(f"   - 整体客单价：{avg_ticket:.0f}元")
print(f"   - 流失率：{lost_rate * 100:.1f}%（{len(lost_customers)}人）")
print(f"\n📈 客户分层分布：")
for layer in layer_order:
    count = layer_counts.get(layer, 0)
    print(f"   - {layer}：{count}人 ({count / total_customers * 100:.1f}%)")