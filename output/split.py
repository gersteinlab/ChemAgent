import re
import openpyxl
import ast  # 用于将字符串解析为列表

def extract_data(txt_file, xlsx_file):
    # 读取或创建 Excel 工作簿
    try:
        wb = openpyxl.load_workbook(xlsx_file)
        ws = wb.active
    except FileNotFoundError:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Extracted Data"
        ws.append(["Text Before First Semicolon", "Text After Second Semicolon", "psolve average", "psolve average Mean", "if correct"])

    # 在数据前插入一个标记行
    ws.append([])
    ws.append([f"File: {txt_file}"])
    ws.append([])

    correct_mode=False
    # 添加标题行
    ws.append(["Text Before First Semicolon", "Text After Second Semicolon", "psolve average", "psolve average Mean", "if correct"])

    # 用于存储所有记录和检查正确性的记录
    all_lines = []
    correct_lines = set()
    
    # 读取 txt 文件的内容
    with open(txt_file, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            
            # 检查是否进入 'Correct' 部分
            if line.startswith("Correct---------------------------------"):
                correct_mode = True
                continue

            if correct_mode:
                # 匹配分号前后的内容和 psolve average 列表
                match = re.search(r'(.*?);(.*?);.*psolve average\s*(\[[^\]]+\])', line)
                if match:
                    before_semicolon = match.group(1).strip()
                    after_semicolon = match.group(2).strip()
                    psolve_average = match.group(3).strip()

                    # 将正确的记录加入集合
                    correct_lines.add((before_semicolon, after_semicolon, psolve_average))
                    
                continue
            
            # 匹配分号前后的内容和 psolve average 列表
            match = re.search(r'(.*?);(.*?);.*psolve average\s*(\[[^\]]+\])', line)
            if match:
                before_semicolon = match.group(1).strip()
                after_semicolon = match.group(2).strip()
                psolve_average = match.group(3).strip()

                # 解析 psolve average 列表并计算平均值
                try:
                    psolve_list = ast.literal_eval(psolve_average)
                    if isinstance(psolve_list, list):
                        mean_value = sum(psolve_list) / len(psolve_list)
                    else:
                        mean_value = None
                except (ValueError, SyntaxError):
                    psolve_list = []
                    mean_value = None
                
                # 记录所有的行
                all_lines.append((before_semicolon, after_semicolon, psolve_average,mean_value))

    # 更新每行的正确性
    for line in all_lines:
        before_semicolon, after_semicolon, psolve_average, mean_value = line
        if (before_semicolon, after_semicolon, psolve_average) in correct_lines:
            correct_status = "correct"
        else:
            correct_status = "wrong"

        # 将提取的信息和正确性写入 Excel 表格
        ws.append([before_semicolon, after_semicolon, psolve_average, mean_value, correct_status])

    # 保存为 xlsx 文件
    wb.save(xlsx_file)
    print(f"Data has been extracted to {xlsx_file}")



# 使用示例
txt_files=["atkins_gpt4.txt","chemmc_gpt35.txt","matter_gpt4.txt","matter_gpt35.txt","quan_gpt4.txt"]

xlsx_file = "output.xlsx"   # 输出的 xlsx 文件路径

for txt_file in txt_files:
    extract_data(txt_file, xlsx_file)


