import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from notion_client import Client
import os
# Notion 및 기본 설정
notion = Client(auth=os.environ["NOTION_AUTH_TOKEN"])
# notion = Client(auth="secret_6iWa3mdFpN435mqTGA2yMwmj41QVQ7CujFHXLDeM98h")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
}
kst = pytz.timezone('Asia/Seoul')

# URL 설정
SEARCH_URL = "https://www.seti.go.kr/common/bbs/management/selectCmmnBBSMgmtList.do?menuId=1000002747&bbsId=BBSMSTR_000000001070&pageIndex=1"
RSS_URL = "https://rss.blog.naver.com/cgs2020.xml"
DATABASE_ID = "e6b4a0208d45466ab2cd50f95115a5e5"

# Notion에 페이지 추가
def add_notion_page(title, link, date, creation_date, tag):
    new_page = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "URL": {"url": link},
            "Person": {"people": [{"object": "user", "id": "49e9d9a7-dcb1-4ab3-88aa-6996e26700db"}]},
            "Date": {"date": {"start": date}}},
            "CreationDate": {"rich_text": [{"text": {"content": creation_date}}]},
            "Tag": {"multi_select": [{"name": tag}]}
        
    }
    notion.pages.create(**new_page)

# Notion에서 중복 확인
def is_post_in_notion(title):
    response = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"property": "Name", "title": {"equals": title}}
    )
    return len(response.get("results", [])) > 0

# 웹사이트 파싱
def parse_website():
    response = requests.get(SEARCH_URL, headers=headers)
    if response.status_code != 200:
        print(f"Website fetch error: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.select('tbody tr')[:5]
    items = []
    for row in rows:
        title = row.select_one('td.title a').get_text(strip=True)
        link = "https://www.seti.go.kr" + row.select_one('td.title a')['href']
        date = row.select_one('td.date').get_text(strip=True)
        items.append({"title": title, "link": link, "date": date, "tag": "study"})
    return items

# RSS 파싱 (최근 5개 "이벤트" 게시물)
def parse_rss():
    response = requests.get(RSS_URL, headers=headers)
    if response.status_code != 200:
        print(f"RSS fetch error: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'lxml-xml')  # 'xml' 대신 'lxml-xml' 사용
    items = soup.find_all('item')
    event_items = []
    for item in items:
        category = item.find('category')
        if category and category.text.strip() == '이벤트':
            title = item.find('title').get_text(strip=True)
            link = item.find('link').get_text(strip=True)
            date = item.find('pubDate').get_text(strip=True)
            event_items.append({"title": title, "link": link, "date": date, "tag": "Theater"})
            if len(event_items) == 5:  # 5개까지만 수집
                break
    return event_items

# 메인 파싱 및 Notion 업데이트 함수
def update_notion_with_new_posts():
    current_time = datetime.now(kst).isoformat()
    
    # 모든 소스에서 데이터 수집
    sources = [
        ("Website", parse_website),
        ("RSS", parse_rss)
    ]
    
    for source_name, parse_func in sources:
        print(f"Checking {source_name}...")
        items = parse_func()
        for item in items:
            if not is_post_in_notion(item["title"]):
                print(f"New post found in {source_name}: {item['title']}")
                add_notion_page(item["title"], item["link"], current_time, item["date"], item["tag"])
            else:
                print(f"Post '{item['title']}' already exists in Notion from {source_name}. Skipping.")

if __name__ == "__main__":
    update_notion_with_new_posts()