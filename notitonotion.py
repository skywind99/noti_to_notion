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
Science_URL = "https://www.sciencecenter.go.kr/scipia/introduce/notice"

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

def is_post_in_notion(title, url=None):
    """
    Notion DB에 동일한 게시물이 있는지 확인
    - httpx로 직접 API 호출
    """
    import httpx
    
    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_AUTH_TOKEN']}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        # URL로 먼저 검색
        if url:
            payload = {
                "filter": {
                    "property": "URL",
                    "url": {
                        "equals": url
                    }
                }
            }
            response = httpx.post(
                f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if len(data.get("results", [])) > 0:
                    return True
        
        # 제목으로 검색
        payload = {
            "filter": {
                "property": "Name",
                "title": {
                    "equals": title
                }
            }
        }
        response = httpx.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return len(data.get("results", [])) > 0
        else:
            print(f"Notion API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error checking Notion: {e}")
        return False
        

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

SCIENCE_BASE = "https://www.sciencecenter.go.kr"

def parse_science_notices(limit=10):
    """
    국립과천과학관 공지/공고 목록 파싱
    """
    try:
        response = session.get(Science_URL, headers=headers, timeout=15)
    except Exception as e:
        print(f"Website fetch error: {e}")
        return []

    if response.status_code != 200:
        print(f"Website fetch error: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    rows = soup.select('#BoardTable tbody tr')
    if not rows:
        print("No rows found in #BoardTable tbody")
        return []

    items = []
    for row in rows:
        try:
            a = row.select_one('td.left.title a')
            if not a or not a.get('href'):
                continue

            title = a.get_text(strip=True)
            href = a['href']
            from urllib.parse import urljoin
            link = urljoin(SCIENCE_BASE, href)

            date_str = None
            for td in row.select('td'):
                txt = td.get_text(strip=True)
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}', txt):
                    date_str = txt
                    break

            if not date_str:
                continue

            items.append({
                "title": title,
                "link": link,
                "date": date_str,
                "tag": "science"
            })

            if len(items) >= limit:
                break
        except Exception:
            continue

    return items


def update_notion_with_new_posts():
    current_time = datetime.now(kst).isoformat()
    sources = [("Website", parse_website), ("RSS", parse_rss), ("Science", parse_science_notices)]
    
    total_new = 0
    total_skipped = 0
    
    for source_name, parse_func in sources:
        print(f"\n{'='*50}")
        print(f"Checking {source_name}...")
        print(f"{'='*50}")
        
        items = parse_func()
        print(f"Found {len(items)} items from {source_name}")
        
        for item in items:
            # URL과 제목으로 중복 체크
            if not is_post_in_notion(item["title"], item.get("link")):
                print(f"✅ NEW: {item['title']}")
                add_notion_page(item["title"], item["link"], current_time, item["date"], item["tag"])
                total_new += 1
            else:
                print(f"⏭️  SKIP: {item['title'][:50]}... (already exists)")
                total_skipped += 1
    
    print(f"\n{'='*50}")
    print(f"📊 Summary:")
    print(f"  - New posts added: {total_new}")
    print(f"  - Posts skipped (duplicates): {total_skipped}")
    print(f"{'='*50}")

if __name__ == "__main__":
    update_notion_with_new_posts()
