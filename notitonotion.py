def parse_science_exhibitions():
    response = session.get(Science_URL, headers=headers)
    if response.status_code != 200:
        print(f"Website fetch error: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 'ul.bbslist' 내의 'li' 태그들 순차적으로 처리
    items = []
    bbslist = soup.select('ul.bbsList li')  # 'ul.bbsList' 내의 'li' 태그들
    
    if not bbslist:
        print("No items found in ul.bbsList")
    
    for item in bbslist:
        title_tag = item.select_one('.title.ellipsis.multiline')  # 제목 클래스가 'ellipsis multiline'인 태그
        date_tag = item.select_one('.date')  # 날짜 클래스에서 추출
        if title_tag and date_tag:
            title = title_tag.get_text(strip=True)
            link = "https://smart.science.go.kr" + item.select_one('a')['href']  # 링크는 a 태그에서 추출
            date_str = date_tag.get_text(strip=True)
            
            # 날짜 형식 변환 (yy-mm-dd → yyyy-mm-dd)
            if len(date_str) == 8:  # 예: 2025.06.22
                try:
                    parsed_date = datetime.strptime(date_str, "%Y.%m.%d")
                    iso_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    iso_date = date_str
            else:
                iso_date = date_str

            # 추출한 제목, 링크, 날짜 정보를 items 리스트에 추가
            items.append({"title": title, "link": link, "date": iso_date, "tag": "exhibition"})
        else:
            print("No title or date found for an item")
    
    # 파싱한 항목들 확인
    if items:
        print(f"Found {len(items)} items in Science section")
    else:
        print("No items to add to Notion from Science section")

    return items
