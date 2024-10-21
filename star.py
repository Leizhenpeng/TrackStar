import requests
from bs4 import BeautifulSoup
import os
import logging
import json
import csv
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import aiohttp
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_exponential
from baseopensdk import BaseClient, JSON
from baseopensdk.api.base.v1 import BatchCreateAppTableRecordRequest
from dotenv import load_dotenv, find_dotenv
import os
# 加载 .env 文件中的环境变量
load_dotenv(find_dotenv())

# 配置日志
logging.basicConfig(level=logging.INFO)

# 从环境变量获取仓库信息
repo = os.getenv("TARGET_REPO")
access_token = os.getenv("ACCESS_TOKEN")
feishu_webhook_url = os.getenv("FEISHU_WEBHOOK")
personal_base_token = os.environ['PERSONAL_BASE_TOKEN']
feishu_bitable_url = os.getenv("FEISHU_BITABLE_URL")

# 修改这些常量
FIRST_RUN_MAX_PAGES = 4  # 首次运行时的最大页数
REGULAR_MAX_PAGES = 10   # 常规运行时的最大页数
SHOW_STAR_NUM = 5  # 显示的star数量

# 超时时间（秒）
timeout_seconds = 10

# 设置并发数和重试次数
CONCURRENCY = 10
MAX_RETRIES = 3



# 异步重试装饰器
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
async def fetch_with_retry(session, url):
    async with session.get(url, headers={'Authorization': f'token {access_token}'}) as response:
        response.raise_for_status()
        return await response.json()

# 异步获取用户详细信息
async def fetch_user_details_async(session, username):
    url = f'https://api.github.com/users/{username}'
    try:
        return await fetch_with_retry(session, url)
    except Exception as e:
        logging.error(f"获取用户 {username} 详细信息失败: {e}")
        return None

# 并发获取多个用户的详细信息
async def fetch_multiple_user_details(usernames):
    async with ClientSession() as session:
        tasks = [fetch_user_details_async(session, username) for username in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [result for result in results if result is not None and not isinstance(result, Exception)]

# 修改获取当前仓库信息的函数
def get_current_repo():
    # 首先检查是否在 GitHub Actions 环境中
    if 'GITHUB_REPOSITORY' in os.environ:
        return os.environ['GITHUB_REPOSITORY']
    else:
        # 如果不在 GitHub Actions 环境中，使用 TARGET_REPO 环境变量
        return os.getenv('TARGET_REPO')

# 新增函数：检查是否在 GitHub Actions 环境中运行
def is_github_actions():
    return 'GITHUB_ACTIONS' in os.environ

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
    
    # 根据是否有历史用户来决定使用哪个最页数
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

# 删除 FIELDNAMES，只保留中文字段名的字典
CHINESE_FIELDNAMES = {
    'login': '用户名',
    'name': '姓名',
    "html_url": "用户主页",
    'location': '位置',
    'bio': '简介',
    'public_repos': '公开仓库数',
    'public_gists': '公开Gist数',
    'followers': '关注者数',
    'following': '关注数',
    'created_at': '创建时间',
    'updated_at': '更新时间'
}

# 修改 save_stargazers_details_to_csv 函数
def save_stargazers_details_to_csv(stargazers_details, filename):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CHINESE_FIELDNAMES.values())
        writer.writeheader()
        
        for user in stargazers_details:
            filtered_user = {CHINESE_FIELDNAMES[key]: user[key] for key in CHINESE_FIELDNAMES if key in user}
            writer.writerow(filtered_user)

# 修改 update_total_csv 函数
def update_total_csv(new_stargazers_details, csv_filename):
    file_exists = os.path.isfile(csv_filename)
    
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CHINESE_FIELDNAMES.values())
        
        if not file_exists:
            writer.writeheader()
        
        for user in new_stargazers_details:
            filtered_user = {CHINESE_FIELDNAMES[key]: user[key] for key in CHINESE_FIELDNAMES if key in user}
            writer.writerow(filtered_user)

# 函数：获取最新的运行ID和artifact ID
def get_latest_artifact_info():
    current_repo = get_current_repo()
    if not current_repo:
        logging.error("无法获取当前仓库信息")
        return None, None

    url = f'https://api.github.com/repos/{current_repo}/actions/runs'
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
    current_repo = get_current_repo()
    
    artifact_message = ""
    if is_github_actions():
        latest_run_id, latest_artifact_id = get_latest_artifact_info()
        if current_repo and latest_run_id and latest_artifact_id:
            artifact_url = f"https://github.com/{current_repo}/actions/runs/{latest_run_id}/artifacts/{latest_artifact_id}"
            artifact_message = f"\n\n[点击此处查看当日star用户信息]({artifact_url})"
        else:
            logging.error("无法获取最新的artifact信息或仓库信息")
    

    stargazers_list = "\n".join([f"- [{user['login']}](https://github.com/{user['login']}) (关注{user['followers']}人, 被关注{user['following']}人, 公开了{user['public_repos']}个仓库)" for user in new_stargazers[:SHOW_STAR_NUM]])
    
    max_pages_warning = "\n\n**注意：** 已达到最大页数限制，可能还有更多新的 stargazers。" if reached_max_pages else ""
    
    repo_link = f"https://github.com/{repo}/stargazers" if current_repo else "#"
    
    today_date = datetime.now().strftime("%Y年%m月%d日")
    
    feishu_bitable_message = ""
    if "base/" in feishu_bitable_url:
        # 从 API URL 提取实际的多维表格 URL
        feishu_bitable_message = f"\n\n[点击此处查看完整的 Stargazers 数据]({feishu_bitable_url})"
    else:
        feishu_bitable_message = "\n\n\n飞书多维表格未配置正确!"

    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"**日期：{today_date}**\n"
                               f"**仓库：[{repo}]({repo_link})**\n"
                               f"**今日新增 Star 数：{len(new_stargazers)}**\n\n"
                               f"**新增 Star 用户详情：**\n\n{stargazers_list}{artifact_message}{max_pages_warning}{feishu_bitable_message}"
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





def  batch_add_records_to_bitable(fields):
    """
    新增多条数据到飞书多维表格

    :param fields: dict, 包含要插入的字段名和值
    :return: None
    """

    # app_token
    feishu_bitable_app_token = feishu_bitable_url.split('/')[4].split('?')[0]
    print(feishu_bitable_app_token)
    # table_id
    table_start_index = feishu_bitable_url.find('table=') + len('table=')
    base_end_index = feishu_bitable_url.find('&')
    feishu_bitable_table_id = feishu_bitable_url[table_start_index:base_end_index]
    print(feishu_bitable_table_id)


    records = []
    for user in fields:
        records.append({
            'fields': {
                '用户名': str(user['login']),
                '姓名': str(user.get('name', '')),
                "用户主页": str(user['html_url']),
                '位置': str(user.get('location', '')),
                '简介': str(user.get('bio', '')),
                '公开仓库数': str(user['public_repos']),
                '公开Gist数': str(user['public_gists']),
                '关注者数': str(user['followers']),
                '关注数': str(user['following']),
                '评分': str(user['grade']),
                '创建时间': int(datetime.strptime(user['created_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp() * 1000),
                '更新时间': int(datetime.strptime(user['updated_at'], "%Y-%m-%dT%H:%M:%SZ").timestamp() * 1000),
                '收集时间': int(datetime.now().timestamp() * 1000)  
            }
        })

     # 构建客户端
    client: BaseClient = BaseClient.builder() \
        .app_token(feishu_bitable_app_token) \
        .personal_base_token(personal_base_token) \
        .build()

    # 构造请求对象
    request = BatchCreateAppTableRecordRequest.builder() \
        .table_id(feishu_bitable_table_id) \
        .request_body({
            "records": records
        }) \
        .build()
    
    print(request)

    # 发起请求以新增记录
    response = client.base.v1.app_table_record.create(request)

    # 检查响应并打印结果
    if response.code == 0:
        print("记录新增成功！")
        print(JSON.marshal(response))
        return True
    else:
        print("新增记录失败")
        print(JSON.marshal(response))

# 修改主函数 track_stargazers
def track_stargazers():
    try:
        logging.info("开始获取stargazers...")
    
        previous_stargazers = read_previous_stargazers('stargazers.json')
        logging.info(f"previous_stargazers: {previous_stargazers}")

        current_stargazers, reached_max_pages = fetch_stargazers(previous_stargazers)
        new_stargazers_usernames = find_new_stargazers(previous_stargazers, current_stargazers)
        logging.info(f"new_stargazers_usernames: {new_stargazers_usernames}")


        # 使用异步方法获取新增stargazers的详细信息
        new_stargazers_details = asyncio.run(fetch_multiple_user_details(new_stargazers_usernames))
        # 根据分数进行排序 分数 = 关注者数 * 1 + 关注数 * 10 + 公开仓库数 * 2
        sorted_stargazers = sorted(
            [{**user, 'grade': user['followers'] * 1 + user['following'] * 10 + user['public_repos'] * 2} for user in new_stargazers_details],
            key=lambda user: user['grade'],
            reverse=True
        )
        logging.info(f"new_stargazers_details: {sorted_stargazers}")

        save_stargazers_to_file(current_stargazers, 'stargazers.json')

        if new_stargazers_details:
            logging.info(f"新增的stargazers: {sorted_stargazers}")
            
            # 批量添加到飞书多维表格
            success = batch_add_records_to_bitable(sorted_stargazers)
            if not success:
                logging.error("批量添加数据到飞书多维表格失败")
            
            # 发送飞书消息
            send_message_to_feishu(sorted_stargazers, reached_max_pages)
            
            save_stargazers_details_to_csv(new_stargazers_details, 'new.csv')
            update_total_csv(new_stargazers_details, 'total.csv')
        else:
            logging.info("没有新的stargazers")
    except Exception as e:
        logging.error(f"发生错误: {e}")

# 立即执行一次
if __name__ == "__main__":
    track_stargazers()