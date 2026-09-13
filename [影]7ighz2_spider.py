#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱电影 (m.7ighz2.com) 爬虫 - TVBox & OK影视 兼容
站点: https://m.7ighz2.com

仅使用Python标准库(urllib)，无需安装requests等第三方依赖。
"""

import hashlib
import json
import time
import uuid
import re
import ssl
import urllib.request
import urllib.parse
import urllib.error

# ===================== 配置 =====================
SITE_NAME = "爱电影"
SITE_URL = "https://www.7ighz2.com"
SIGN_KEY = "cb808529bae6b6be45ecfab29a4889bc"
DEVICE_ID = str(uuid.uuid4())
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

# SSL上下文(忽略证书验证，兼容老版本Python)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# 分类配置
CATEGORIES = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "电视剧"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "动漫"},
    {"type_id": "88", "type_name": "短剧"},
]

# 筛选项配置
FILTER_CONFIG = {
    "1": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""}, {"n": "喜剧", "v": "喜剧"}, {"n": "动作", "v": "动作"},
            {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"}, {"n": "悬疑", "v": "悬疑"},
            {"n": "奇幻", "v": "奇幻"}, {"n": "恐怖", "v": "恐怖"}, {"n": "剧情", "v": "剧情"},
            {"n": "犯罪", "v": "犯罪"}, {"n": "动画", "v": "动画"}, {"n": "惊悚", "v": "惊悚"},
            {"n": "战争", "v": "战争"}, {"n": "冒险", "v": "冒险"}, {"n": "灾难", "v": "灾难"},
            {"n": "伦理", "v": "伦理"}, {"n": "其他", "v": "其他"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"},
            {"n": "中国台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
            {"n": "韩国", "v": "韩国"}, {"n": "印度", "v": "印度"}, {"n": "泰国", "v": "泰国"},
            {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
            {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
            {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"},
            {"n": "2016-2010", "v": "2010~2016"}, {"n": "2009-2000", "v": "2000~2009"},
        ]},
        {"key": "lang", "name": "语言", "value": [
            {"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"},
            {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"},
            {"n": "其他", "v": "其他"},
        ]},
    ],
    "2": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""}, {"n": "剧情", "v": "剧情"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "动作", "v": "动作"}, {"n": "爱情", "v": "爱情"}, {"n": "悬疑", "v": "悬疑"},
            {"n": "科幻", "v": "科幻"}, {"n": "奇幻", "v": "奇幻"}, {"n": "古装", "v": "古装"},
            {"n": "武侠", "v": "武侠"}, {"n": "家庭", "v": "家庭"}, {"n": "历史", "v": "历史"},
            {"n": "战争", "v": "战争"}, {"n": "犯罪", "v": "犯罪"}, {"n": "恐怖", "v": "恐怖"},
            {"n": "惊悚", "v": "惊悚"}, {"n": "其他", "v": "其他"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"},
            {"n": "中国台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
            {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
            {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
            {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"},
            {"n": "2016-2010", "v": "2010~2016"},
        ]},
        {"key": "lang", "name": "语言", "value": [
            {"n": "全部", "v": ""}, {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"},
            {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"},
            {"n": "其他", "v": "其他"},
        ]},
    ],
    "3": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""}, {"n": "真人秀", "v": "真人秀"}, {"n": "脱口秀", "v": "脱口秀"},
            {"n": "音乐", "v": "音乐"}, {"n": "舞蹈", "v": "舞蹈"}, {"n": "美食", "v": "美食"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"},
            {"n": "中国台湾", "v": "中国台湾"}, {"n": "韩国", "v": "韩国"}, {"n": "美国", "v": "美国"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
        ]},
    ],
    "4": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""}, {"n": "热血", "v": "热血"}, {"n": "冒险", "v": "冒险"},
            {"n": "励志", "v": "励志"}, {"n": "搞笑", "v": "搞笑"}, {"n": "治愈", "v": "治愈"},
            {"n": "运动", "v": "运动"}, {"n": "其他", "v": "其他"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "日本", "v": "日本"},
            {"n": "韩国", "v": "韩国"}, {"n": "美国", "v": "美国"}, {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
        ]},
    ],
    "88": [
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""}, {"n": "都市", "v": "都市"}, {"n": "甜宠", "v": "甜宠"},
            {"n": "穿越", "v": "穿越"}, {"n": "重生", "v": "重生"}, {"n": "复仇", "v": "复仇"},
            {"n": "其他", "v": "其他"},
        ]},
    ],
}


# ===================== HTTP 工具(纯标准库) =====================
def _http_get(url, headers=None, timeout=15):
    """使用urllib发送GET请求"""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        data = resp.read()
        # 尝试UTF-8解码
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data.decode('gbk', errors='replace')


def _make_sign(params, method="GET"):
    """生成API请求签名: SHA1(MD5(base_string))"""
    t = str(int(time.time() * 1000))
    clean = {}
    for k, v in params.items():
        if v is not None and str(v) != "":
            clean[k] = str(v)

    if method.upper() == "GET":
        sorted_params = "&".join(f"{k}={clean[k]}" for k in sorted(clean.keys()))
    else:
        sorted_params = json.dumps(clean, separators=(',', ':'), ensure_ascii=False) if clean else ""

    base = (sorted_params + "&" if sorted_params else "") + f"key={SIGN_KEY}&t={t}"
    md5_hash = hashlib.md5(base.encode('utf-8')).hexdigest()
    sign = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()
    return sign, t


def _api_get(path, params=None):
    """发送GET API请求并返回JSON"""
    params = params or {}
    # 确保所有参数值转为字符串
    str_params = {k: str(v) for k, v in params.items() if v is not None and str(v) != ""}
    sign, t = _make_sign(str_params, "GET")

    headers = {
        "User-Agent": UA,
        "sign": sign,
        "t": t,
        "deviceId": DEVICE_ID,
        "authorization": "",
        "Referer": SITE_URL + "/",
        "Origin": SITE_URL,
    }

    # 构建URL
    query = urllib.parse.urlencode(str_params)
    url = f"{SITE_URL}/api{path}?{query}"

    try:
        text = _http_get(url, headers)
        return json.loads(text)
    except Exception as e:
        return {"code": -1, "msg": str(e)}


# ===================== 数据转换工具 =====================
def _fix_pic(url):
    """修复图片URL，确保是完整URL"""
    if not url:
        return ""
    url = str(url)
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return SITE_URL + url
    return url


def _build_vod_item(item):
    """将API返回的视频数据转换为TVBox/OK影视格式"""
    pic = _fix_pic(item.get("vodPic", ""))
    remarks = item.get("vodRemarks", "") or item.get("vodVersion", "") or ""
    score = item.get("vodScore", "") or item.get("vodDoubanScore", "") or ""

    return {
        "vod_id": str(item.get("vodId", "")),
        "vod_name": item.get("vodName", ""),
        "vod_pic": pic,
        "vod_remarks": str(remarks),
    }


def _build_vod_detail(data):
    """将详情API数据转换为TVBox/OK影视详情格式"""
    episode_list = data.get("episodeList", [])
    if episode_list:
        episodes = []
        for ep in sorted(episode_list, key=lambda x: x.get("sort", 0)):
            ep_name = ep.get("name", "")
            # 如果name是纯数字，加上"第"和"集"
            if ep_name and ep_name.isdigit():
                ep_name = "第" + ep_name + "集"
            elif not ep_name:
                ep_name = "正片"
            ep_id = str(data.get("vodId", "")) + "_" + str(ep.get("nid", ""))
            episodes.append(ep_name + "$" + ep_id)
        play_url = "#".join(episodes)
    else:
        play_url = "正片$" + str(data.get("vodId", "")) + "_0"

    pic = _fix_pic(data.get("vodPic", ""))
    content = data.get("vodContent", "") or data.get("vodBlurb", "") or ""
    content = re.sub(r'<[^>]+>', '', content).strip()

    return {
        "vod_id": str(data.get("vodId", "")),
        "vod_name": data.get("vodName", ""),
        "vod_pic": pic,
        "vod_year": str(data.get("vodYear", "") or ""),
        "vod_area": data.get("vodArea", "") or "",
        "vod_lang": data.get("vodLang", "") or "",
        "vod_remarks": str(data.get("vodRemarks", "") or data.get("vodVersion", "") or ""),
        "vod_score": str(data.get("vodScore", "") or ""),
        "vod_actor": data.get("vodActor", "") or "",
        "vod_director": data.get("vodDirector", "") or "",
        "vod_content": content,
        "vod_play_from": SITE_NAME,
        "vod_play_url": play_url,
    }


# ===================== 参数类型兼容工具 =====================
def _to_int(val, default=0):
    """安全转换为int"""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _to_str(val, default=""):
    """安全转换为str"""
    if val is None:
        return default
    return str(val)


def _parse_extend(extend):
    """解析extend参数，兼容dict和JSON字符串"""
    if not extend:
        return {}
    if isinstance(extend, dict):
        return extend
    if isinstance(extend, str):
        try:
            return json.loads(extend)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


# ===================== Spider 主类 =====================
class Spider:
    """TVBox & OK影视 兼容爬虫 (纯标准库实现)"""

    def init(self, extend=""):
        self.extend = extend if extend else ""

    def getName(self):
        return SITE_NAME

    def isVideoFormat(self, url):
        url = str(url) if url else ""
        return ".m3u8" in url or ".mp4" in url

    def manualFuc(self, url):
        return str(url) if url else ""

    # ---------- 首页 ----------
    def homeContent(self, filter):
        """获取首页分类和筛选项

        Args:
            filter: 0或1 (int/str/bool)，是否返回筛选项
        Returns:
            {"class": [...], "filters": {...}}
        """
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in CATEGORIES]
        result = {"class": classes}

        # filter参数兼容各种类型
        f = _to_int(filter) if not isinstance(filter, bool) else (1 if filter else 0)
        if f:
            result["filters"] = FILTER_CONFIG

        return result

    def homeVideoContent(self):
        """获取首页推荐视频
        Returns:
            {"list": [...]}
        """
        result = {"list": []}
        for cat in CATEGORIES[:3]:
            try:
                data = _api_get("/mw-movie/anonymous/video/list", {
                    "type1": cat["type_id"],
                    "pageNum": "1",
                    "pageSize": "6",
                    "clientType": "1",
                })
                if data.get("code") == 200:
                    for item in data.get("data", {}).get("list", []):
                        result["list"].append(_build_vod_item(item))
            except Exception:
                pass
        return result

    # ---------- 分类列表 ----------
    def categoryContent(self, tidy, pg, filter, extend):
        """获取分类视频列表

        Args:
            tidy: 分类ID (str/int)
            pg: 页码 (str/int)
            filter: 是否筛选 (0/1)
            extend: 筛选参数 (JSON string 或 dict)
        Returns:
            {"list": [...], "page": int, "pagecount": int, "limit": int, "total": int}
        """
        tid = _to_str(tidy)
        page = _to_int(pg, 1)
        if page < 1:
            page = 1
        ext = _parse_extend(extend)

        params = {
            "type1": tid,
            "pageNum": str(page),
            "pageSize": "20",
            "clientType": "1",
        }

        # 筛选参数
        if ext.get("class"):
            params["v_class"] = str(ext["class"])
        if ext.get("area"):
            params["area"] = str(ext["area"])
        if ext.get("year"):
            params["year"] = str(ext["year"])
        if ext.get("lang"):
            params["lang"] = str(ext["lang"])

        result = {
            "list": [],
            "page": page,
            "pagecount": 1,
            "limit": 20,
            "total": 0,
        }

        try:
            data = _api_get("/mw-movie/anonymous/video/list", params)
            if data.get("code") == 200:
                d = data.get("data", {})
                result["pagecount"] = _to_int(d.get("totalPage", 1), 1)
                result["total"] = _to_int(d.get("totalCount", 0), 0)
                for item in d.get("list", []):
                    result["list"].append(_build_vod_item(item))
        except Exception:
            pass

        return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        """获取视频详情(含剧集列表)

        Args:
            ids: [vodId] 列表 (list)
        Returns:
            {"list": [vod_detail]}
        """
        if not ids:
            return {"list": []}

        vod_id = _to_str(ids[0])
        result = {"list": []}

        try:
            data = _api_get("/mw-movie/anonymous/video/detail", {"id": vod_id})
            if data.get("code") == 200:
                vod = _build_vod_detail(data.get("data", {}))
                result["list"].append(vod)
        except Exception:
            pass

        return result

    # ---------- 搜索 ----------
    def searchContent(self, key, quick):
        """搜索视频

        Args:
            key: 搜索关键词 (str)
            quick: 是否快速搜索 (0/1/bool)
        Returns:
            {"list": [...]}
        """
        keyword = _to_str(key)
        if not keyword:
            return {"list": []}

        # quick兼容各种类型
        q = _to_int(quick) if not isinstance(quick, bool) else (1 if quick else 0)
        page_size = "5" if q else "20"

        result = {"list": []}

        try:
            data = _api_get("/mw-movie/anonymous/video/searchByWord", {
                "keyword": keyword,
                "pageNum": "1",
                "pageSize": page_size,
                "clientType": "1",
            })
            if data.get("code") == 200:
                search_data = data.get("data", {})
                # 搜索结果优先取 result.list
                items = []
                if isinstance(search_data.get("result"), dict):
                    items = search_data["result"].get("list", [])
                # 如果没有，取 typeResult.list
                if not items and isinstance(search_data.get("typeResult"), dict):
                    items = search_data["typeResult"].get("list", [])

                for item in items:
                    result["list"].append(_build_vod_item(item))
        except Exception:
            pass

        return result

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        """获取播放地址

        Args:
            flag: 播放源标识 (str)
            id: 播放ID (str)，格式: vodId_nid 或 vodId_0
            vipFlags: VIP标识 (list)
        Returns:
            {"parse": 0, "url": "...", "header": {...}}
        """
        result = {"parse": 0, "url": "", "header": {"User-Agent": UA}}

        play_id = _to_str(id)
        if not play_id:
            return result

        # 解析播放ID: vodId_nid
        parts = play_id.split("_")
        vod_id = parts[0]
        nid = parts[1] if len(parts) > 1 else "0"

        try:
            if nid == "0" or not nid:
                # 单集电影: 先获取详情拿第一集nid
                detail = _api_get("/mw-movie/anonymous/video/detail", {"id": vod_id})
                if detail.get("code") == 200:
                    episodes = detail.get("data", {}).get("episodeList", [])
                    if episodes:
                        nid = str(episodes[0].get("nid", ""))
                    else:
                        return result
                else:
                    return result

            data = _api_get("/mw-movie/anonymous/v2/video/episode/url", {
                "clientType": "1",
                "id": vod_id,
                "nid": nid,
            })

            if data.get("code") == 200:
                url_list = data.get("data", {}).get("list", [])
                # 优先选择不需要登录的播放地址
                play_url = ""
                for item in url_list:
                    if not item.get("needLogin", True):
                        play_url = item.get("url", "")
                        break
                # 如果没有免登录地址，取第一个
                if not play_url and url_list:
                    play_url = url_list[0].get("url", "")

                if play_url:
                    result["url"] = play_url
                    result["header"] = {
                        "User-Agent": UA,
                        "Referer": SITE_URL + "/",
                    }
        except Exception:
            pass

        return result


# ===================== 入口(本地测试) =====================
if __name__ == "__main__":
    spider = Spider()
    spider.init()

    print("=" * 60)
    print("  爱电影 爬虫测试 (纯标准库版)")
    print("=" * 60)

    # 测试首页
    print("\n[1] 首页分类:")
    home = spider.homeContent(1)
    print("  分类数:", len(home.get("class", [])))
    for c in home.get("class", []):
        print("    -", c["type_name"], "(ID:", c["type_id"] + ")")
    print("  筛选项数:", len(home.get("filters", {})))

    # 测试首页推荐
    print("\n[1.5] 首页推荐:")
    hv = spider.homeVideoContent()
    print("  推荐数:", len(hv.get("list", [])))
    for item in hv.get("list", [])[:3]:
        print("    -", item["vod_name"], "|", item["vod_pic"][:50], "|", item["vod_remarks"])

    # 测试分类列表
    print("\n[2] 分类列表 (电影 第1页):")
    cat = spider.categoryContent("1", "1", 0, {})
    print("  总数:", cat.get("total"), "总页:", cat.get("pagecount"))
    print("  返回:", len(cat.get("list", [])), "条")
    for item in cat.get("list", [])[:3]:
        print("    -", item["vod_name"], "|", item["vod_pic"][:60], "|", item["vod_remarks"])

    # 测试分类筛选
    print("\n[2.5] 分类筛选 (电影-喜剧):")
    cat2 = spider.categoryContent("1", "1", 0, '{"class": "喜剧"}')
    print("  总数:", cat2.get("total"), "返回:", len(cat2.get("list", [])), "条")
    for item in cat2.get("list", [])[:3]:
        print("    -", item["vod_name"], "|", item["vod_remarks"])

    # 测试详情
    print("\n[3] 视频详情 (id=146415):")
    detail = spider.detailContent(["146415"])
    if detail.get("list"):
        vod = detail["list"][0]
        print("  名称:", vod["vod_name"])
        print("  封面:", vod["vod_pic"])
        print("  演员:", vod["vod_actor"])
        print("  播放源:", vod["vod_play_from"])
        print("  播放地址:", vod["vod_play_url"][:80] + "...")

    # 测试搜索
    print("\n[4] 搜索 (关键词=绿灯):")
    search = spider.searchContent("绿灯", 0)
    print("  结果:", len(search.get("list", [])), "条")
    for item in search.get("list", [])[:3]:
        print("    -", item["vod_name"], "| ID:", item["vod_id"], "| 封面:", item["vod_pic"][:50])

    # 测试播放
    print("\n[5] 播放地址 (id=146415, nid=1311316):")
    player = spider.playerContent(SITE_NAME, "146415_1311316", [])
    if player.get("url"):
        print("  播放地址:", player["url"][:80] + "...")
        print("  解析方式:", "直接播放" if player.get("parse") == 0 else "需要解析")
    else:
        print("  未获取到播放地址")

    print("\n" + "=" * 60)
    print("  测试完成!")
    print("=" * 60)
