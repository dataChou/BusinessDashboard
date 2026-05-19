import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

print("=" * 50)
print("正在生成模拟数据...")
print("=" * 50)

# ========== 目标分层（4000人）==========
target_layers = {
    '高价值客户': 600,  # 15%
    '活跃客户': 900,  # 22.5%
    '沉睡客户': 1200,  # 30%
    '流失客户': 1300  # 32.5%
}

# 生成客户列表
customer_ids = [f"C{i:05d}" for i in range(1, 4001)]
customer_names = [f"客户{i}" for i in range(1, 4001)]

# 分配分层
customer_layer = {}
idx = 0
for layer, count in target_layers.items():
    for i in range(count):
        customer_layer[customer_ids[idx]] = layer
        idx += 1

# 每个分层的R值范围（距今天数）
layer_r_range = {
    '高价值客户': (0, 30),
    '活跃客户': (31, 90),
    '沉睡客户': (91, 180),
    '流失客户': (181, 365)
}

# 每个分层的消费次数范围（修正：提高次数，让总订单接近8-10万）
layer_f_range = {
    '高价值客户': (15, 30),  # 高价值客户年均2-3次/月 → 15-30次
    '活跃客户': (8, 18),  # 活跃客户年均1-1.5次/月 → 8-18次
    '沉睡客户': (4, 10),  # 沉睡客户半年内没来，但之前有消费
    '流失客户': (2, 5)  # 流失客户消费次数少
}


def weighted_choice(options, weights):
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for option, weight in zip(options, weights):
        cumulative += weight
        if r < cumulative:
            return option
    return options[-1]


# 生成记录
records = []
today = datetime(2026, 5, 19)

for cust_id in customer_ids:
    layer = customer_layer[cust_id]
    cust_name = customer_names[customer_ids.index(cust_id)]

    # 确定R值（最后一次消费距今天数）
    R_min, R_max = layer_r_range[layer]
    R = random.randint(R_min, R_max)
    last_date = today - timedelta(days=R)

    # 确定F值（总消费次数）
    F_min, F_max = layer_f_range[layer]
    F = random.randint(F_min, F_max)

    # 生成F条消费记录
    dates = []
    for _ in range(F):
        # 消费时间分布在 [last_date - 180天, last_date] 之间
        days_before = random.randint(0, 180)
        record_date = last_date - timedelta(days=days_before)
        # 确保日期不早于2025-01-01
        if record_date < datetime(2025, 1, 1):
            record_date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 30))
        dates.append(record_date)
    dates.sort()

    for record_date in dates:
        # 服务项目（高价值客户看病/绝育比例更高）
        if layer == '高价值客户':
            service = weighted_choice(['疫苗', '绝育', '看病', '体检', '洗护'], [10, 30, 40, 12, 8])
        elif layer == '活跃客户':
            service = weighted_choice(['疫苗', '绝育', '看病', '体检', '洗护'], [25, 20, 25, 15, 15])
        elif layer == '沉睡客户':
            service = weighted_choice(['疫苗', '绝育', '看病', '体检', '洗护'], [40, 15, 15, 15, 15])
        else:  # 流失客户
            service = weighted_choice(['疫苗', '绝育', '看病', '体检', '洗护'], [50, 10, 15, 10, 15])

        # 消费金额
        if service == '疫苗':
            amount = random.randint(80, 150)
        elif service == '绝育':
            amount = random.randint(300, 600)
        elif service == '看病':
            amount = random.randint(200, 800)
        elif service == '体检':
            amount = random.randint(150, 350)
        else:  # 洗护
            amount = random.randint(100, 250)

        # 高价值客户消费金额上浮20%
        if layer == '高价值客户':
            amount = int(amount * random.uniform(1.1, 1.3))

        pet_type = weighted_choice(['猫', '狗', '其他'], [45, 45, 10])
        doctor = weighted_choice(['李医生', '王医生', '张医生', '刘医生', '陈医生'], [30, 25, 20, 15, 10])

        month = record_date.month
        new_ratio = max(0.2, 0.7 - (month - 1) * 0.045)
        source = '新客户' if random.random() < new_ratio else '老客户'

        records.append([
            record_date.strftime('%Y-%m-%d'),
            cust_id,
            cust_name,
            pet_type,
            service,
            amount,
            doctor,
            source
        ])

# 转DataFrame
df = pd.DataFrame(records,
                  columns=['日期', '宠主ID', '宠主姓名', '宠物类型', '服务项目', '消费金额', '医生', '客户来源'])
df = df.sort_values('日期').reset_index(drop=True)

# 保存
df.to_csv('pet_hospital_data.csv', index=False, encoding='utf-8-sig')

# ========== 验证结果 ==========
print("\n" + "=" * 50)
print("✅ 数据生成完成")
print("=" * 50)

df_check = pd.read_csv('pet_hospital_data.csv', encoding='utf-8-sig')
df_check['日期'] = pd.to_datetime(df_check['日期'])

total_customers = df_check['宠主ID'].nunique()
total_orders = len(df_check)
total_revenue = df_check['消费金额'].sum()
avg_ticket = total_revenue / total_orders

print(f"\n📊 整体数据：")
print(f"   - 总客户数：{total_customers:,}人")
print(f"   - 总订单数：{total_orders:,}笔")
print(f"   - 总营收：{total_revenue:,.0f}元 ({total_revenue / 10000:.1f}万)")
print(f"   - 整体客单价：{avg_ticket:.0f}元")

# 分层验证
last_visit = df_check.groupby('宠主ID')['日期'].max().reset_index()
last_visit['R'] = last_visit['日期'].apply(lambda x: (today - x).days)


def verify_layer(r):
    if r <= 30:
        return '高价值客户'
    elif r <= 90:
        return '活跃客户'
    elif r <= 180:
        return '沉睡客户'
    else:
        return '流失客户'


last_visit['计算分层'] = last_visit['R'].apply(verify_layer)
result = last_visit['计算分层'].value_counts()

print(f"\n📈 客户分层分布：")
for layer in ['高价值客户', '活跃客户', '沉睡客户', '流失客户']:
    count = result.get(layer, 0)
    pct = count / total_customers * 100
    print(f"   - {layer}：{count}人 ({pct:.1f}%)")

# 各分层人均消费次数
print(f"\n📊 各分层人均消费次数：")
for layer in ['高价值客户', '活跃客户', '沉睡客户', '流失客户']:
    layer_ids = last_visit[last_visit['计算分层'] == layer]['宠主ID'].tolist()
    if layer_ids:
        layer_orders = df_check[df_check['宠主ID'].isin(layer_ids)]
        avg_f = len(layer_orders) / len(layer_ids)
        print(f"   - {layer}：{avg_f:.1f}次/人")

print("\n" + "=" * 50)
print("📁 文件已保存：pet_hospital_data.csv")
print("👉 下一步：运行看板代码生成Excel")