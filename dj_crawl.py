import requests
import json
import os
import time
from bs4 import BeautifulSoup
from hashlib import md5

# ===================== 配置区 =====================
CRAWL_SITES = [
    "https://kdj.one",
    "https://oupudj.cc",
    "https://duanjugou.top"
]
DETAIL_DIR = "detail"
PUBLIC_REPO_NAME = "drama-source-public"
GITHUB_USER = "jiutv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
}
# 每日全新空列表，不加载历史
today_drama_list = []

if not os.path.exists(DETAIL_DIR):
    os.makedirs(DETAIL_DIR)

def get_drama_md5_id(title):
    return md5(title.encode("utf-8")).hexdigest()[:8]

def get_page_html(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as err:
        print(f"页面访问失败 {url}：{str(err)}")
        return ""

def crawl_single_site(site_url):
    html = get_page_html(site_url)
    if not html:
        return
    soup = BeautifulSoup(html, "html.parser")
    item_cards = soup.select("div.drama-item")
    for card in item_cards:
        try:
            title = card.select_one("h3.title").get_text(strip=True)
            plot_tag = card.select_one("span.plot")
            plot_type = plot_tag.get_text(strip=True) if plot_tag else "未知"
            bg_tag = card.select_one("span.bg")
            bg_type = bg_tag.get_text(strip=True) if bg_tag else "未知"
            cover_img = card.select_one("img")["src"]
            hot_tag = card.select_one("span.hot")
            hot_num = hot_tag.get_text(strip=True) if hot_tag else "0万"
            detail_href = card.select_one("a")["href"]

            if not detail_href.startswith("http"):
                detail_href = site_url.rstrip("/") + detail_href

            drama_mid = get_drama_md5_id(title)
            detail_file_name = f"{DETAIL_DIR}/{drama_mid}.json"

            detail_html = get_page_html(detail_href)
            detail_soup = BeautifulSoup(detail_html, "html.parser")
            decrypt_script_tag = detail_soup.select_one("script#decrypt_script")
            decrypt_js = decrypt_script_tag.get_text(strip=True) if decrypt_script_tag else "function getPlayUrl(){return '';}"

            detail_info = {
                "code":200,
                "title":title,
                "totalEp":"未知集数",
                "decryptJs":decrypt_js,
                "videoLine":[]
            }
            with open(detail_file_name, "w", encoding="utf-8") as f:
                json.dump(detail_info, f, ensure_ascii=False, separators=(",", ":"))

            detail_raw_url = f"https://ghproxy.com/https://raw.githubusercontent.com/{GITHUB_USER}/{PUBLIC_REPO_NAME}/main/{detail_file_name}"
            drama_entity = {
                "title": title,
                "plotType": plot_type,
                "bgType": bg_type,
                "cover": cover_img,
                "hotNum": hot_num,
                "detailUrl": detail_raw_url
            }
            today_drama_list.append(drama_entity)
            print(f"采集剧集：{title}")
            time.sleep(0.8)
        except Exception as err:
            print(f"解析卡片失败：{str(err)}")
            continue

def export_full_drama_list():
    output_json = {
        "code":200,
        "list":today_drama_list,
        "total":len(today_drama_list)
    }
    with open("drama_list.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, separators=(",", ":"))
    print(f"今日短剧列表生成，共 {len(today_drama_list)} 部")

def export_source_config():
    source_root_raw = f"https://ghproxy.com/https://raw.githubusercontent.com/{GITHUB_USER}/{PUBLIC_REPO_NAME}/main/drama_list.json"
    source_config = {
        "sites":[
            {
                "key":"auto_dj_daily",
                "name":"每日更新短剧库",
                "type":3,
                "api":source_root_raw,
                "searchable":1,
                "quickSearch":1,
                "filterable":1,
                "searchUrl":source_root_raw + "?wd={wd}",
                "responseType":"json"
            }
        ],
        "parses":[
            {
                "name":"本地QuickJS解密",
                "type":1,
                "url":"js"
            }
        ],
        "flags":["全部剧情","逆袭","都市","情感生活","悬疑玄幻","家庭伦理","全部背景","古代","现代"]
    }
    with open("dj_source.json", "w", encoding="utf-8") as f:
        json.dump(source_config, f, ensure_ascii=False, separators=(",", ":"))
    print("APP订阅源 dj_source.json 生成完成")

if __name__ == "__main__":
    print("========== 每日全量更新爬虫启动 ==========")
    today_drama_list.clear()
    # 遍历所有站点全量爬取今日首页内容
    for site in CRAWL_SITES:
        print(f"\n正在爬取站点：{site}")
        crawl_single_site(site)
    # 输出当日全新列表，覆盖昨日全部数据
    export_full_drama_list()
    export_source_config()
    print("\n========== 当日更新完成，次日将全部重新爬取覆盖 ==========")