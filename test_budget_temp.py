def calculate_budget(anomalies, avg_tool_wear):
    base = 5000
    anomaly_cost = anomalies * 200
    wear_cost = avg_tool_wear * 15
    return int(base + anomaly_cost + wear_cost)

# 測試案例 1: 典型數據 (與原先 $12,500 接近)
case1 = calculate_budget(30, 100)
print(f"Case 1 (30 anomalies, 100 wear): ${case1}")

# 測試案例 2: 高風險數據
case2 = calculate_budget(80, 250)
print(f"Case 2 (80 anomalies, 250 wear): ${case2}")

# 測試案例 3: 低風險數據
case3 = calculate_budget(5, 20)
print(f"Case 3 (5 anomalies, 20 wear): ${case3}")

assert case1 == 12500
assert case2 == 24750
assert case3 == 6300
print("All tests passed!")
