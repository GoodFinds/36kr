import requests
import json
import time
import os
import re
from datetime import datetime, timedelta
import argparse

def get_36kr_news(days_ago=0, max_pages=5, page_size=100, save_dir="./data"):
    """
    获取36氪新闻数据
    
    参数:
    days_ago: 获取几天前的新闻，0表示今天，1表示昨天，以此类推
    max_pages: 最多获取几页
    page_size: 每页获取的新闻数量
    save_dir: 保存文件的目录
    
    返回:
    保存的文件路径
    """
    # API请求URL
    url = 'https://gateway.36kr.com/api/mis/nav/ifm/subNav/flow'

    # 请求头
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Origin': 'https://36kr.com',
        'Referer': 'https://36kr.com/'
    }

    # 获取目标日期范围
    target_date = datetime.now() - timedelta(days=days_ago)
    target_date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    target_date_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    target_timestamp_start = int(target_date_start.timestamp() * 1000)
    target_timestamp_end = int(target_date_end.timestamp() * 1000)
    
    date_str = target_date.strftime('%Y-%m-%d')

    # 保存所有指定日期的新闻
    target_news = []
    all_news = []

    # 当前页
    current_page = 0
    
    # 确保保存目录存在
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    print(f"获取{date_str}的新闻...")
    print(f"时间范围: {target_date_start} 到 {target_date_end}")

    # 第一页请求数据
    first_page_data = {
        "partner_id": "web",
        "timestamp": int(time.time() * 1000),
        "param": {
            "subnavType": 1,
            "subnavNick": "web_news",
            "pageSize": page_size,
            "pageEvent": 0,  # 第一页
            "siteId": 1,
            "platformId": 2
        }
    }

    def extract_url(news_item):
        """
        从新闻项中提取并构建正确的URL
        """
        route = news_item.get('route', '')
        
        # 从route中提取itemId
        if 'itemId=' in route:
            # 使用正则表达式提取itemId
            match = re.search(r'itemId=(\d+)', route)
            if match:
                item_id = match.group(1)
                return f"https://36kr.com/p/{item_id}"
        
        # 如果没有找到itemId，尝试其他可能的ID字段
        template_material = news_item.get('templateMaterial', {})
        if 'itemId' in template_material:
            return f"https://36kr.com/p/{template_material['itemId']}"
        
        # 如果都没有找到，返回原始URL（作为备选）
        return f"https://36kr.com/{route}" if route else ""

    try:
        response = requests.post(url, headers=headers, json=first_page_data)
        if response.status_code == 200:
            result = response.json()
            if result['code'] == 0 and 'data' in result and 'itemList' in result['data']:
                # 保存所有新闻
                all_news.extend(result['data']['itemList'])
                
                # 筛选目标日期的新闻
                for item in result['data']['itemList']:
                    item_timestamp = item['templateMaterial']['publishTime']
                    # 判断是否在目标日期范围内
                    if target_timestamp_start <= item_timestamp <= target_timestamp_end:
                        target_news.append(item)
                
                current_page += 1
                print(f"第{current_page}页: 找到{len(target_news)}条{date_str}的新闻")
                
                # 获取下一页的回调参数
                page_callback = result['data'].get('pageCallback')
                
                # 继续获取后续页面
                while page_callback and current_page < max_pages:
                    next_page_data = {
                        "partner_id": "web",
                        "timestamp": int(time.time() * 1000),
                        "param": {
                            "subnavType": 1,
                            "subnavNick": "web_news",
                            "pageSize": page_size,
                            "pageEvent": 1,  # 后续页
                            "pageCallback": page_callback,
                            "siteId": 1,
                            "platformId": 2
                        }
                    }
                    
                    # 添加延时避免请求过快
                    time.sleep(1)
                    
                    response = requests.post(url, headers=headers, json=next_page_data)
                    if response.status_code == 200:
                        result = response.json()
                        if result['code'] == 0 and 'data' in result and 'itemList' in result['data']:
                            # 保存所有新闻
                            all_news.extend(result['data']['itemList'])
                            
                            # 本页找到的目标日期新闻数
                            current_page_target_count = 0
                            
                            for item in result['data']['itemList']:
                                item_timestamp = item['templateMaterial']['publishTime']
                                # 判断是否在目标日期范围内
                                if target_timestamp_start <= item_timestamp <= target_timestamp_end:
                                    target_news.append(item)
                                    current_page_target_count += 1
                            
                            current_page += 1
                            print(f"第{current_page}页: 找到{current_page_target_count}条{date_str}的新闻")
                            
                            # 获取下一页回调
                            page_callback = result['data'].get('pageCallback')
                            
                            # 如果已经获取了足够多的页面，停止获取
                            if current_page >= max_pages:
                                print(f"已达到最大页数限制({max_pages}页)，停止获取")
                                break
                        else:
                            print("数据格式不正确")
                            break
                    else:
                        print(f"请求失败: {response.status_code}")
                        break
            else:
                print("第一页数据格式不正确")
        else:
            print(f"请求失败: {response.status_code}")
    except Exception as e:
        print(f"发生错误: {e}")

    # 如果没有找到目标日期的新闻，可以输出所有新闻的时间范围
    if len(target_news) == 0 and len(all_news) > 0:
        timestamps = [item['templateMaterial']['publishTime'] for item in all_news]
        earliest = min(timestamps)
        latest = max(timestamps)
        
        earliest_date = datetime.fromtimestamp(earliest/1000)
        latest_date = datetime.fromtimestamp(latest/1000)
        
        print(f"\n未找到{date_str}的新闻。已获取新闻的时间范围是:")
        print(f"最早: {earliest_date}")
        print(f"最新: {latest_date}")
        
        # 计算所有新闻的日期分布
        date_distribution = {}
        for item in all_news:
            timestamp = item['templateMaterial']['publishTime']
            item_date = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d')
            if item_date in date_distribution:
                date_distribution[item_date] += 1
            else:
                date_distribution[item_date] = 1
        
        print("\n获取到的新闻日期分布:")
        for date, count in sorted(date_distribution.items(), reverse=True):
            print(f"{date}: {count}条")
        
        # 提示用户尝试获取可用的日期
        if date_distribution:
            available_dates = list(date_distribution.keys())
            if available_dates:
                print(f"\n建议尝试获取这些日期的新闻: {', '.join(available_dates)}")

    # 按时间排序
    target_news.sort(key=lambda x: x['templateMaterial']['publishTime'], reverse=True)

    # 统计分类信息
    categories = {}
    for news in target_news:
        category = news['templateMaterial'].get('navName', '未分类')
        if category in categories:
            categories[category] += 1
        else:
            categories[category] = 1
    
    # 保存文件名
    filename = f"36kr_{date_str}_news.json"
    filepath = os.path.join(save_dir, filename)
    
    # 提取简化信息
    simplified_news = []
    for news in target_news:
        simplified_news.append({
            'title': news['templateMaterial'].get('widgetTitle', ''),
            'summary': news['templateMaterial'].get('summary', ''),
            'category': news['templateMaterial'].get('navName', '未分类'),
            'theme': news['templateMaterial'].get('themeName', ''),
            'publishTime': news['templateMaterial'].get('publishTime', 0),
            'author': news['templateMaterial'].get('authorName', ''),
            'image': news['templateMaterial'].get('widgetImage', ''),
            'url': extract_url(news)  # 使用新的URL提取函数
        })
    
    # 保存到文件
    save_data = {
        'date': date_str,
        'total': len(simplified_news),
        'categories': categories,
        'news': simplified_news
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    # 显示结果
    print(f"\n总共获取到{len(target_news)}条{date_str}的新闻，按分类统计:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"{category}: {count}条")
    
    print(f"\n前20条{date_str}新闻:")
    for i, news in enumerate(simplified_news[:20]):
        publish_time = datetime.fromtimestamp(news['publishTime']/1000).strftime('%H:%M:%S')
        print(f"{i+1}. [{publish_time}] [{news['category']}] {news['title']}")
        print(f"    URL: {news['url']}")
    
    print(f"\n所有{date_str}新闻已保存到 {filepath}")
    return filepath

if __name__ == "__main__":
    # 命令行参数
    parser = argparse.ArgumentParser(description='获取36氪新闻数据')
    parser.add_argument('--days', type=int, default=0, help='获取几天前的新闻，0表示今天，1表示昨天，以此类推')
    parser.add_argument('--pages', type=int, default=5, help='最多获取几页')
    parser.add_argument('--size', type=int, default=100, help='每页获取的新闻数量')
    parser.add_argument('--dir', type=str, default='./data', help='保存文件的目录')
    args = parser.parse_args()
    
    # 获取并保存新闻
    get_36kr_news(days_ago=args.days, max_pages=args.pages, page_size=args.size, save_dir=args.dir)
