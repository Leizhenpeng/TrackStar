import requests
from bs4 import BeautifulSoup
import os
import csv

# 从环境变量获取仓库信息
owner = os.getenv("GITHUB_OWNER")
repo = os.getenv("GITHUB_REPO")

# 定义要抓取的总页数
total_pages = 5

# CSV 文件名
csv_file = 'stargazers.csv'

# 函数：获取当前的stargazers列表
def fetch_stargazers():
    stargazers = []
    for page in range(1, total_pages + 1):
        url = f'https://github.com/{owner}/{repo}/stargazers?page={page}'
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            ol = soup.find('ol', class_='d-block d-md-flex flex-wrap gutter list-style-none')

            if ol:
                lis = ol.find_all('li', class_='col-md-4 mb-3')

                for li in lis:
                    a_tag = li.find('h2', class_='h4 mb-1').find('a')
                    if a_tag:
                        login = a_tag.text.strip()
                        stargazers.append(login)
            else:
                print(f"第 {page} 页没有找到有效的内容")
        else:
            print(f"获取第 {page} 页失败，状态码: {response.status_code}")
    return stargazers

# 函数：读取之前保存的stargazers列表
def read_previous_stargazers():
    if not os.path.exists(csv_file):
        return []
    
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        return [row[0] for row in reader]

# 函数：保存stargazers列表到CSV文件
def save_stargazers_to_csv(stargazers):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for stargazer in stargazers:
            writer.writerow([stargazer])
    print("Stargazers 已保存到 CSV 文件")

# 函数：对比新旧stargazers，找出新增的stargazers
def find_new_stargazers(old_stargazers, new_stargazers):
    return list(set(new_stargazers) - set(old_stargazers))

# 主函数：获取和对比stargazers
def track_stargazers():
    print("开始获取stargazers...")
    
    # 获取当前stargazers列表
    current_stargazers = fetch_stargazers()
    
    # 读取之前保存的stargazers列表
    previous_stargazers = read_previous_stargazers()
    
    # 找出新增的stargazers
    new_stargazers = find_new_stargazers(previous_stargazers, current_stargazers)

    # 保存最新的stargazers列表到CSV文件（覆盖保存全部数据）
    save_stargazers_to_csv(current_stargazers)

    if new_stargazers:
        # 如果有新增的stargazers，打印新增的stargazers
        print(f"新增的stargazers: {new_stargazers}")
    else:
        print("没有新的stargazers")

# 立即执行一次
track_stargazers()
