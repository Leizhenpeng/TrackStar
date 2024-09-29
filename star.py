import requests
from bs4 import BeautifulSoup
import csv
import os
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

# 从环境变量获取仓库信息
owner = os.getenv("GITHUB_OWNER")
repo = os.getenv("GITHUB_REPO")

# 定义要抓取的总页数
total_pages = 5

# 定义CSV文件的表头
csv_headers = ['login']

# 文件名定义
all_stargazers_file = f"{repo}_star.csv"  # 保存全部的stargazers
new_stargazers_file = f"{repo}_new_star.csv"  # 保存新增的stargazers

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
                        print(f"第 {page} 页: {login}")
            else:
                print(f"第 {page} 页没有找到有效的内容")
        else:
            print(f"获取第 {page} 页失败，状态码: {response.status_code}")
    return stargazers

# 函数：读取上次保存的stargazers列表
def read_previous_stargazers():
    if os.path.exists(all_stargazers_file):
        with open(all_stargazers_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # 跳过表头
            return [row[0] for row in reader]
    return []

# 函数：保存stargazers列表到CSV
def save_stargazers(stargazers, filename):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)  # 写入表头
        for login in stargazers:
            writer.writerow([login])

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

    # 保存最新的stargazers列表（覆盖保存全部数据）
    save_stargazers(current_stargazers, all_stargazers_file)

    if new_stargazers:
        # 如果有新增的stargazers，覆盖保存至新stargazers文件
        print(f"新增的stargazers: {new_stargazers}")
        save_stargazers(new_stargazers, new_stargazers_file)
        print(f"新增stargazers已保存至 {new_stargazers_file}")
    else:
        print("没有新的stargazers")

# 立即执行一次
track_stargazers()
