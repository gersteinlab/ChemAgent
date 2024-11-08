import openpyxl
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_averages(xlsx_file):
    # 读取 Excel 工作簿
    wb = openpyxl.load_workbook(xlsx_file)
    ws = wb.active

    correct_means = []
    wrong_means = []
    high_cor = 0
    high_wr = 0
    low_cor =0
    low_wr = 0

    # 从第二行开始遍历（跳过标题行和标记行）
    for row in ws.iter_rows(min_row=4, max_row=300, values_only=True):
        mean_value = row[3]  # psolve average Mean 列
        if row[4] == "correct":  # if correct 列
            if mean_value is not None and mean_value != 0:
                correct_means.append(mean_value)
        elif row[4] == "wrong":
            if mean_value is not None and mean_value != 0:
                wrong_means.append(mean_value)
        if row[4] == "correct" or row[4] == "wrong":
            if mean_value is not None and mean_value >= 0.805:
                if row[4] == "correct": high_cor += 1
                elif row[4] == "wrong": high_wr += 1
            elif mean_value is not None and mean_value < 0.805:
                if row[4] == "correct": low_cor += 1
                elif row[4] == "wrong": low_wr += 1

    # 计算平均值
    correct_avg = sum(correct_means) / len(correct_means) if correct_means else 0
    wrong_avg = sum(wrong_means) / len(wrong_means) if wrong_means else 0

    # 输出结果
    print(f"Average psolve average Mean for correct: {correct_avg}")
    print(f"Average psolve average Mean for wrong: {wrong_avg}")
    print(high_cor, high_wr, low_cor, low_wr)

    return correct_means, wrong_means


def visualize(a, b):
    # Adjusted KDE plot without incompatible features
    plt.figure(figsize=(8,5))

    # Plot KDE for list a
    sns.kdeplot(a, label="Correct Tasks' Similarity Distribution", color='blue', bw_adjust=0.3)

    # Plot KDE for list b
    sns.kdeplot(b, label="Failed Tasks' Similarity Distribution", color='red', bw_adjust=0.3)

    # Add labels and title
    plt.xlabel('Similarity Value')
    plt.ylabel('Density')
    plt.title('KDE of Similarity Distributions')
    plt.legend()

    # Show the plot
    plt.show()




cor_m, wr_m = analyze_averages("output.xlsx")

cm = []
wm =[]
for i in range(len(cor_m)):
    if cor_m[i] >= 0.71 and cor_m[i]<=0.925: cm.append(cor_m[i])
for i in range(len(wr_m)):
    if wr_m[i] >= 0.71 and wr_m[i]<=0.925: wm.append(wr_m[i])


visualize(cm, wm)