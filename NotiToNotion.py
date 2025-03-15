import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from notion_client import Client

# Notion API 설정
notion = Client(auth="secret_6iWa3mdFpN435mqTGA2yMwmj41QVQ7CujFHXLDeM98h")

# 검색할 사이트 URL
SEARCH_URL = "https://www.seti.go.kr/common/bbs/management/selectCmmnBBSMgmtList.do?menuId=1000002747&bbsId=BBSMSTR_000000001070&pageIndex=1"

# 사용자 에이전트 헤더 (크롤링 시 차단 회피용)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
}

# 한국 표준시 (KST) 설정
kst = pytz.timezone('Asia/Seoul')

# Notion에 새로운 페이지를 추가하는 함수
def add_notion_page(title, link, date, creation_date):
    new_page = {
        "parent": {"database_id": "e6b4a0208d45466ab2cd50f95115a5e5"},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "URL": {"url": link},
            "Person": {
                "people": [{"object": "user", "id": "49e9d9a7-dcb1-4ab3-88aa-6996e26700db"}]
            },
            "Date": {"date": {"start": date}},
            "CreationDate": {"rich_text": [{"text": {"content": creation_date}}]}
        }
    }
    notion.pages.create(**new_page)

# Notion 데이터베이스에서 제목으로 항목을 조회하는 함수
def is_post_in_notion(title):
    response = notion.databases.query(
        **{
            "database_id": "e6b4a0208d45466ab2cd50f95115a5e5",
            "filter": {
                "property": "Name",
                "title": {"equals": title}
            }
        }
    )
    return len(response.get("results", [])) > 0

# 웹사이트에서 최근 게시물 5개를 확인하는 함수
def check_new_blog_post():
    response = requests.get(SEARCH_URL, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching page: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.select('tbody tr')
    recent_items = rows[:5]

    for row in recent_items:
        post_title = row.select_one('td.title a').get_text(strip=True)
        post_link = "https://www.seti.go.kr" + row.select_one('td.title a')['href']
        post_date = row.select_one('td.date').get_text(strip=True)

        if not is_post_in_notion(post_title):
            print(f"New post found: {post_title}")
            current_time = datetime.now(kst).isoformat()
            add_notion_page(post_title, post_link, current_time, post_date)
        else:
            print(f"Post '{post_title}' already exists in Notion. Skipping upload.")

# 단일 실행
if __name__ == "__main__":
    check_new_blog_post()