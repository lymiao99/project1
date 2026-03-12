import csv
import random

def generate_mock_data(filename="test_data.csv", num_records=10000):
    header = [
        "UDI", "Product ID", "Type", "Air temperature [K]", "Process temperature [K]",
        "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]", 
        "Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF"
    ]

    types = ['L', 'M', 'H']
    # 產品 ID 的前綴對應 Type
    type_prefix = {'L': 'L47', 'M': 'M14', 'H': 'H29'}

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for i in range(1, num_records + 1):
            p_type = random.choice(types)
            p_id = f"{type_prefix[p_type]}{random.randint(10000, 99999)}"
            
            # 模擬合理的物理數值
            air_temp = round(random.uniform(295.0, 305.0), 1)
            process_temp = round(air_temp + random.uniform(10.0, 11.0), 1)
            
            # 轉速與扭力通常呈負相關
            rot_speed = random.randint(1300, 2800)
            torque = round(max(3.8, 100 - (rot_speed / 25) + random.uniform(-5, 5)), 1)
            
            tool_wear = random.randint(0, 250)
            
            # 故障模擬 (設定極低機率以符合現實)
            failure = 1 if random.random() < 0.03 else 0
            twf = hdf = pwf = osf = rnf = 0
            
            if failure:
                # 隨機分配一個故障原因
                reason = random.choice(['twf', 'hdf', 'pwf', 'osf', 'rnf'])
                if reason == 'twf': twf = 1
                elif reason == 'hdf': hdf = 1
                elif reason == 'pwf': pwf = 1
                elif reason == 'osf': osf = 1
                else: rnf = 1

            writer.writerow([
                i, p_id, p_type, air_temp, process_temp,
                rot_speed, torque, tool_wear,
                failure, twf, hdf, pwf, osf, rnf
            ])

    print(f"成功生成 {num_records} 筆資料並寫入至 {filename}")

if __name__ == "__main__":
    generate_mock_data()