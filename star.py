import requests
from bs4 import BeautifulSoup
import os
import logging
import json
import csv
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)

# 从环境变量获取仓库信息
repo = os.getenv("TARGET_REPO")
access_token = os.getenv("ACCESS_TOKEN")
feishu_webhook_url = os.getenv("FEISHU_WEBHOOK")

# 修改这些常量
FIRST_RUN_MAX_PAGES = 2  # 首次运行时的最大页数
REGULAR_MAX_PAGES = 10   # 常规运行时的最大页数

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

# 新增函数：获取历史 stargazers 中的最后几个用户
def get_last_stargazers(stargazers, count=3):
    return stargazers[-count:] if len(stargazers) >= count else stargazers

# 修改 fetch_stargazers 函数
def fetch_stargazers(previous_stargazers):
    stargazers = []
    last_known_stargazers = get_last_stargazers(previous_stargazers)
    reached_known_stargazers = False
    page = 1
    
    # 根据是否有历史用户来决定使用哪个最大页数
    max_pages = FIRST_RUN_MAX_PAGES if not previous_stargazers else REGULAR_MAX_PAGES

    while page <= max_pages and not reached_known_stargazers:
        url = f'https://github.com/{repo}/stargazers?page={page}'
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
                        if login in last_known_stargazers:
                            reached_known_stargazers = True
                            break
            else:
                logging.warning(f"第 {page} 页没有找到有效的内容")
                break
        else:
            break
        page += 1

    if page > max_pages:
        logging.warning(f"已达到最大页数限制 ({max_pages} 页)，可能还有更多 stargazers")
    
    return stargazers, page > max_pages

# 函数：从文件获取之前保存的stargazers列表
def read_previous_stargazers(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    logging.warning(f"文件 {filename} 为空，返回空列表")
                    return []
        except json.JSONDecodeError:
            logging.warning(f"文件 {filename} 内容格式不正确，返回空列表")
            return []
    else:
        logging.warning(f"文件 {filename} 不存在，返回空列表")
        return []

# 函数：保存stargazers列表到文件
def save_stargazers_to_file(stargazers, filename):
    with open(filename, 'w') as f:
        json.dump(stargazers, f)
    logging.info(f"Stargazers 已保存到文件 {filename}")

# 函数：保存stargazers列表到CSV文件
def save_stargazers_to_csv(stargazers, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['username'])
        for user in stargazers:
            writer.writerow([user])
    logging.info(f"Stargazers 已保存到CSV文件 {filename}")

# 函数：对比新旧stargazers，找出新增的stargazers
def find_new_stargazers(old_stargazers, new_stargazers):
    return list(set(new_stargazers) - set(old_stargazers))

# 函数：获取用户详细信息
def fetch_user_details(username):
    url = f'https://api.github.com/users/{username}'
    response = send_request(url)
    if response:
        return response.json()
    else:
        return None


FIELDNAMES = [
    'login', 'id', 'node_id', 'avatar_url', 'url', 'html_url', 
    'followers_url', 'following_url', 'gists_url', 'starred_url', 
    'subscriptions_url', 'organizations_url', 'repos_url', 'events_url', 
    'received_events_url', 'type', 'site_admin', 'name', 'location', 
    'bio', 'public_repos', 'public_gists', 'followers', 'following', 
    'created_at', 'updated_at'
]

# 函数：保存stargazers详细信息到CSV文件
def save_stargazers_details_to_csv(stargazers_details, filename):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for user in stargazers_details:
            filtered_user = {key: user[key] for key in FIELDNAMES if key in user}
            writer.writerow(filtered_user)

# 函数：更新total.csv文件
def update_total_csv(new_stargazers_details, csv_filename):
    file_exists = os.path.isfile(csv_filename)
    
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        
        if not file_exists:
            writer.writeheader()
        
        for user in new_stargazers_details:
            filtered_user = {key: user[key] for key in FIELDNAMES if key in user}
            writer.writerow(filtered_user)

# 函数：获取最新的运行ID和artifact ID
def get_latest_artifact_info():
    url = f'https://api.github.com/repos/{repo}/actions/runs'
    response = send_request(url)
    if response:
        runs = response.json().get('workflow_runs', [])
        if runs:
            latest_run_id = runs[0]['id']
            artifacts_url = runs[0]['artifacts_url']
            artifacts_response = send_request(artifacts_url)
            if artifacts_response:
                artifacts = artifacts_response.json().get('artifacts', [])
                if artifacts:
                    latest_artifact_id = artifacts[0]['id']
                    return latest_run_id, latest_artifact_id
    return None, None

# 修改 send_message_to_feishu 函数
def send_message_to_feishu(new_stargazers, reached_max_pages):
    headers = {
        "Content-Type": "application/json"
    }
    latest_run_id, latest_artifact_id = get_latest_artifact_info()
    if latest_run_id and latest_artifact_id:
        artifact_url = f"https://github.com/{repo}/actions/runs/{latest_run_id}/artifacts/{latest_artifact_id}"
        artifact_message = f"\n\n[点击此处查看当日star用户信息]({artifact_url})"
    else:
        logging.error("无法获取最新的artifact信息")
        artifact_message = "\n\nartifact_url 获取失败"
    
    stargazers_list = "\n".join([f"- [{user['login']}](https://github.com/{user['login']}) (关注{user['followers']}人, 被关注{user['following']}人, 公开了{user['public_repos']}个仓库)" for user in new_stargazers])
    
    max_pages_warning = "\n\n**注意：** 已达到最大页数限制，可能还有更多新的 stargazers。" if reached_max_pages else ""
    
    repo_link = f"https://github.com/{repo}/stargazers"
    
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"今天有**{len(new_stargazers)}**个人点赞了[仓库]({repo_link})：\n\n{stargazers_list}{artifact_message}{max_pages_warning}"
                }
            ]
        }
    }
    try:
        response = requests.post(feishu_webhook_url, headers=headers, json=data, timeout=timeout_seconds)
        response.raise_for_status()
        logging.info("消息已发送到Feishu")
    except requests.RequestException as e:
        logging.error(f"发送消息到Feishu时发生错误: {e}")

# 修改主函数 track_stargazers
def track_stargazers():
    logging.info("开始获取stargazers...")
    
    # 读取之前保存的stargazers列表
    previous_stargazers = read_previous_stargazers('stargazers.json')
    logging.info(f"previous_stargazers: {previous_stargazers}")

    # 获取当前stargazers列表
    current_stargazers, reached_max_pages = fetch_stargazers(previous_stargazers)
    
    # 找出新增的stargazers
    new_stargazers_usernames = find_new_stargazers(previous_stargazers, current_stargazers)
    logging.info(f"new_stargazers_usernames: {new_stargazers_usernames}")

    # 获取新增stargazers的详细信息
    new_stargazers_details = []
    for username in new_stargazers_usernames:
        user_details = fetch_user_details(username)
        if user_details:
            new_stargazers_details.append(user_details)
    logging.info(f"new_stargazers_details: {new_stargazers_details}")

    # 保存最新的stargazers列表到文件
    save_stargazers_to_file(current_stargazers, 'stargazers.json')

    if new_stargazers_details:
        # 如果有新增的stargazers，打印并发送消息到Feishu
        logging.info(f"新增的stargazers: {new_stargazers_details}")
        send_message_to_feishu(new_stargazers_details, reached_max_pages)
        
        # 保存新增的stargazers到new.csv
        save_stargazers_details_to_csv(new_stargazers_details, 'new.csv')
        
        # 更新total.csv
        update_total_csv(new_stargazers_details, 'total.csv')
    else:
        logging.info("没有新的stargazers")

# 立即执行一次
track_stargazers()