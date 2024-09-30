import requests
from bs4 import BeautifulSoup
import os
import logging
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)

# 从环境变量获取仓库信息
owner = os.getenv("REPO_OWNER")
repo = os.getenv("REPO_NAME")
access_token = os.getenv("ACCESS_TOKEN")
feishu_webhook_url = os.getenv("FEISHU_WEBHOOK")

# 定义要抓取的总页数
total_pages = 2

# 超时时间（秒）
timeout_seconds = 10

# 函数：发送HTTP请求并处理响应
def send_request(url):
    try:
        response = requests.get(url, headers={'Authorization': f'token {access_token}'}, timeout=timeout_seconds)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"请求 {url} 时发生错误: {e}")
        return None

# 函数：获取当前的stargazers列表
def fetch_stargazers():
    stargazers = []
    for page in range(1, total_pages + 1):
        url = f'https://github.com/{owner}/{repo}/stargazers?page={page}'
        response = send_request(url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            ol = soup.find('ol', class_='d-block d-md-flex flex-wrap gutter list-style-none')
            if ol:
                lis = ol.find_all('li', class_='col-md-4 mb-3')
                for li in lis:
                    a_tag = li.find('h2', class_='h4 mb-1').find('a')
                    if a_tag:
                        login = a_tag.text.strip()
                        stargazers.append(login)
                        logging.info(f"第 {page} 页: {login}")
            else:
                logging.warning(f"第 {page} 页没有找到有效的内容")
    return stargazers

# 函数：从文件获取之前保存的stargazers列表
def read_previous_stargazers(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        logging.warning(f"文件 {filename} 不存在，返回空列表")
        return []

# 函数：保存stargazers列表到文件
def save_stargazers_to_file(stargazers, filename):
    # 只保存最后三个stargazers
    # The line `# stargazers = stargazers[-3:]` is a commented-out line in the code. It is currently
    # not active and does not affect the program's functionality.
    # stargazers = stargazers[-3:]
    with open(filename, 'w') as f:
        json.dump(stargazers, f)
    logging.info(f"Stargazers 已保存到文件 {filename}")

# 函数：对比新旧stargazers，找出新增的stargazers
def find_new_stargazers(old_stargazers, new_stargazers):
    return list(set(new_stargazers) - set(old_stargazers))

# 函数：发送消息到Feishu
def send_message_to_feishu(new_stargazers):
    headers = {
        "Content-Type": "application/json"
    }
    artifact_url = f" https://api.github.com/repos/Leizhenpeng/TrackStar/actions/artifacts/1993683007"
    data = {
        "msg_type": "text",
        "content": {
            "text": f"今天有{len(new_stargazers)}个人点赞了仓库,\n" + "\n".join([f"https://github.com/{user}" for user in new_stargazers]) + f"\n\n点击 {artifact_url} 查看当日star用户信息"
        }
    }
    try:
        response = requests.post(feishu_webhook_url, headers=headers, json=data, timeout=timeout_seconds)
        response.raise_for_status()
        logging.info("消息已发送到Feishu")
    except requests.RequestException as e:
        logging.error(f"发送消息到Feishu时发生错误: {e}")

# 主函数：获取和对比stargazers
def track_stargazers():
    logging.info("开始获取stargazers...")
    
    # 获取当前stargazers列表
    current_stargazers = fetch_stargazers()
    
    # 读取之前保存的stargazers列表
    previous_stargazers = read_previous_stargazers('stargazers.json')
    logging.info(f"previous_stargazers: {previous_stargazers}")

    # 找出新增的stargazers
    new_stargazers = find_new_stargazers(previous_stargazers, current_stargazers)
    logging.info(f"new_stargazers: {new_stargazers}")
    # 保存最新的stargazers列表到文件
    save_stargazers_to_file(current_stargazers, 'stargazers.json')

    if new_stargazers:
        # 如果有新增的stargazers，打印并发送消息到Feishu
        logging.info(f"新增的stargazers: {new_stargazers}")
        send_message_to_feishu(new_stargazers)
    else:
        logging.info("没有新的stargazers")

# 立即执行一次
track_stargazers()