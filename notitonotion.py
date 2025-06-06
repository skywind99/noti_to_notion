import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from notion_client import Client
import os
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

# Notion 및 기본 설정
notion = Client(auth=os.environ["NOTION_AUTH_TOKEN"])
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
kst = pytz.timezone('Asia/Seoul')
SEARCH_URL = "https://www.seti.go.kr/common/bbs/management/selectCmmnBBSMgmtList.do?menuId=1000002747&bbsId=BBSMSTR_000000001070&pageIndex=1"
RSS_URL = "https://rss.blog.naver.com/cgs2020.xml"
DATABASE_ID = "e6b4a0208d45466ab2cd50f95115a5e5"
Science_URL = "https://smart.science.go.kr/exhibitions/list.action?menuCd=DOM_000000101003001000&contentsSid=47"

# 맞춤형 SSL Adapter 설정
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.set_ciphers('ALL')
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# requests 세션 설정
session = requests.Session()
session.mount('https://', SSLAdapter())

def add_notion_page(title, link, date, creation_date, tag):
    new_page = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "URL": {"url": link},
            "Person": {"people": [{"object": "user", "id": "49e9d9a7-dcb1-4ab3-88aa-6996e26700db"}]},
            "Date": {"date": {"start": date}},
            "CreationDate": {"date": {"start": creation_date}},
            "Tag": {"multi_select": [{"name": tag}]}
        }
    }
    try:
        notion.pages.create(**new_page)
        print(f"Added to Notion: {title}")
    except Exception as e:
        print(f"Error adding to Notion: {e}")

def is_post_in_notion(title):
    response = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"property": "Name", "title": {"equals": title}}
    )
    return len(response.get("results", [])) > 0

def parse_website():
    response = session.get(SEARCH_URL, headers=headers)
    if response.status_code != 200:
        print(f"Website fetch error: {response.status_code}")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.select('tbody tr')[:5]
    items = []
    for row in rows:
        title = row.select_one('td.title a').get_text(strip=True)
        front_link = "https://www.seti.go.kr/common/bbs/management/selectCmmnBBSMgmtView.do?menuId=1000002747&pageIndex=1&bbscttId="
        behind_link = "&bbsId=BBSMSTR_000000001070&searchKey=&searchWord=&etc=&searchKeyTxt=1&searchWordTxt=&perPage=10"
        main_link = row.select_one('td.title a')['href']
        number = re.search(r"\d+", main_link).group()
        link = front_link + number + behind_link
        date_str = row.select_one('td.date').get_text(strip=True)
        if len(date_str) == 8:
            parsed_date = datetime.strptime(date_str, "%y-%m-%d")
            iso_date = parsed_date.strftime("%Y-%m-%d")
        else:
            iso_date = date_str
        items.append({"title": title, "link": link, "date": iso_date, "tag": "study"})
    return items

def parse_rss():
    response = session.get(RSS_URL, headers=headers)
    if response.status_code != 200:
        print(f"RSS fetch error: {response.status_code}")
        return []
    soup = BeautifulSoup(response.content, 'lxml-xml')
    items = soup.find_all('item')
    event_items = []
    for item in items:
        category = item.find('category')
        if category and category.text.strip() == '이벤트':
            title = item.find('title').get_text(strip=True)
            link = item.find('link').get_text(strip=True)
            pub_date = item.find('pubDate').get_text(strip=True)
            parsed_date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            iso_date = parsed_date.isoformat()
            event_items.append({"title": title, "link": link, "date": iso_date, "tag": "Theater"})
            if len(event_items) == 5:
                break
    return event_items

def parse_science_exhibitions():
    response = session.get(Science_URL, headers=headers)
    if response.status_code != 200:
        print(f"Website fetch error: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    items = []
    
    # ul.bbsList 내의 li 태그들 선택
    list_items = soup.select('ul.bbsList li')
    
    if not list_items:
        print("No items found in ul.bbsList")
        return []
    
    print(f"Found {len(list_items)} items in Science exhibitions")
    
    for i, item in enumerate(list_items[:12]):  # 최대 5개만 처리
        try:
            # 제목 추출
            title_tag = item.select_one('.title.ellipsis.multiline')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            
            # 링크 추출
            link_tag = item.select_one('a')
            if link_tag and link_tag.get('href'):
                href = link_tag['href']
                link = "https://smart.science.go.kr" + href
            else:
                continue
            
            # 날짜 추출
            date_tag = item.select_one('.date')
            if date_tag:
                date_str = date_tag.get_text(strip=True)
                # "2025.05.31 ~ 2025.06.01" 형식에서 앞의 날짜만 추출
                if ' ~ ' in date_str:
                    start_date = date_str.split(' ~ ')[0].strip()
                else:
                    start_date = date_str
                
                # 날짜 형식 변환 (2025.05.31 -> 2025-05-31)
                try:
                    parsed_date = datetime.strptime(start_date, "%Y.%m.%d")
                    iso_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    iso_date = datetime.now().strftime("%Y-%m-%d")
            else:
                iso_date = datetime.now().strftime("%Y-%m-%d")
            
            print(f"Item {i+1}: Title='{title}', Date='{iso_date}'")
            
            items.append({
                "title": title, 
                "link": link, 
                "date": iso_date, 
                "tag": "exhibition"
            })
            
        except Exception as e:
            print(f"Error processing item {i+1}: {e}")
            continue
    
    print(f"Total items found: {len(items)}")
    return items

def update_notion_with_new_posts():
    current_time = datetime.now(kst).isoformat()
    sources = [("Website", parse_website), ("RSS", parse_rss), ("Science", parse_science_exhibitions)]
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
