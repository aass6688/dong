# -*- coding: utf-8 -*-
"""
皮狗DJ站 —— TVBox / 影视仓 / OK影视 兼容 Spider（Drpy / CatVodSpider Python）
站点: https://www.pgdjz.com   内核: CSCMS

用法：放进壳的 spider/py 目录，接口配置为本地 py 路径。
      影视仓 / OK影视 / TVBox(带 Drpy 引擎) 均按 CatVodSpider 标准接口调用。

========================================================================
接口逆向记录（2026-07 实测，全部经实站验证）

【列表容器】只看主列表，侧栏推荐位是纯文字无图，必须跳过：
    分类页/搜索页: <div class="zyvodlist layui-form"> ... <div class="pagebox">
    首页         : <ul class="vodlist">  (多个)
    侧栏(不要)   : <ul class="list">  纯文字，无 img

【两套条目 DOM】
    A 首页/搜索: <li><a href><div class="vodimg"><img src>...<div class="click">播放：2.7万
    B 分类页   : <li><div class="imgbox"><a href><div class="img"><img src>...<div class="tags">播放时长：

【分页】不是 lists/12-2.html！真实格式：
    分类: /video/lists/{tid}/{page}.html          每页 7 条
    排序: /video/lists/{sort}/{tid}/{page}.html
    搜索: /video/search.html?key=xxx&page=N       每页 9 条
    页码模板直接读页面里的：
      <div id="pages" data-uri="/video/lists/12/[page].html" data-nums="8505" data-size="7">
      data-nums=总数  data-size=每页条数  -> pagecount = ceil(nums/size)

【搜索】参数是 key，不是 wd/keyword/q：
    /video/search.html?key=玫瑰          -> 有效
    /video/search.html?wd=玫瑰           -> 空页面

【排序/筛选】/video/lists/{sort}/{tid}.html，sort 取值：
    空=最新  reco=最新推荐  day=今日热门  week=本周热门
    month=本月热门  hits=试听排行  fav=收藏排行  down=下载排行

【封面】图床 tp.pgdjz.fun 校验 Referer：无 Referer -> 404，带 -> 200（UA 无关）
    路径含双斜杠 teheyi//video，CDN 认，不要合并
    页面第一张图是占位图 teheyi/st.png，必须过滤

【播放】地址不在 HTML 里，由 /packs/pc/js/index.js 调接口：
    POST /ajax/videoplay  body: id=<vid>&ids=
    -> {"code":1,"playurl":"https://st.pgdjz.fun/%2Fzwmtv%2F...mp4","pic":"..."}
    playurl 是 URL 编码形式（路径 %2F），原样直出即可播放，不要 unquote
    播放源 st.pgdjz.fun 不校验 Referer，支持 Range（实测 206）
========================================================================
"""

import sys
import re
import json
import base64
import math
from urllib.parse import quote, urljoin

import requests

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):

    # ============ 封面防盗链策略 ============
    # 0 = 原始 URL（壳端/网络层自带 Referer 时用）
    # 1 = 追加 @Referer=...（推荐：FongMi / 猫影视 / 影视仓 / 新版TVBox 支持）
    # 2 = base64 data URI（最通用但最重：单图约 64KB->85KB 字符串，列表慎用）
    #     -> 图裂时依次试 1 -> 0 -> 2
    PIC_MODE = 1

    # 排序筛选器（分类页 /video/lists/{sort}/{tid}.html）
    SORT_LIST = [
        {"n": "最新", "v": ""},
        {"n": "最新推荐", "v": "reco"},
        {"n": "今日热门", "v": "day"},
        {"n": "本周热门", "v": "week"},
        {"n": "本月热门", "v": "month"},
        {"n": "试听排行", "v": "hits"},
        {"n": "收藏排行", "v": "fav"},
        {"n": "下载排行", "v": "down"},
    ]

    # ================= 基础 =================
    def getName(self):
        return "皮狗DJ"

    def init(self, extend=""):
        self.host = "https://www.pgdjz.com"
        self.ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": self.ua,
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        # 站点占位图，命中即视为无效封面
        self.placeholder = ("st.png", "user_pic.png", "logo", "default.jpg")

        self.class_list = [
            {"type_id": "12",  "type_name": "超清MV"},
            {"type_id": "123", "type_name": "车载MV"},
            {"type_id": "112", "type_name": "跳舞MV"},
            {"type_id": "158", "type_name": "国内夜店"},
            {"type_id": "90",  "type_name": "派对MV"},
            {"type_id": "125", "type_name": "发烧MV"},
            {"type_id": "21",  "type_name": "国外夜店"},
            {"type_id": "20",  "type_name": "抒情MV"},
        ]

    # ================= 工具 =================
    def _get(self, url, timeout=15):
        try:
            r = self.sess.get(url, timeout=timeout)
            r.encoding = "utf-8"
            return r.text
        except Exception:
            return ""

    def _abs(self, href):
        """补全为绝对地址（不改动路径，保留双斜杠）"""
        href = (href or "").strip()
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("http"):
            return href
        return urljoin(self.host + "/", href.lstrip("/"))

    def _fix(self, url):
        """播放地址等：补全 + 合并多余斜杠"""
        url = self._abs(url)
        if "://" in url:
            proto, rest = url.split("://", 1)
            rest = re.sub(r"/{2,}", "/", rest)
            url = proto + "://" + rest
        return url

    def _fix_pic(self, url):
        """封面：只补全协议/域名，保留 teheyi//video 的双斜杠"""
        return self._abs(url) if url else ""

    def _is_bad_pic(self, url):
        if not url:
            return True
        low = url.lower()
        return any(p in low for p in self.placeholder)

    def _clean(self, s):
        s = re.sub(r"<[^>]+>", "", s or "")
        s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&quot;", '"').replace("&#39;", "'"))
        return re.sub(r"\s+", " ", s).strip()

    # ---------- 封面防盗链 ----------
    def _wrap_pic(self, pic_url):
        """实测图床只校验 Referer（UA 无关）。
        只追加 @Referer，不追 UA，避免 UA 里的空格破坏部分壳的 @ 分割解析。"""
        if not pic_url:
            return ""
        if self.PIC_MODE == 1:
            return "%s@Referer=%s" % (pic_url, self.host + "/")
        if self.PIC_MODE == 2:
            return self._fetch_pic_base64(pic_url)
        return pic_url

    def _fetch_pic_base64(self, pic_url):
        if not pic_url or pic_url.startswith("data:image"):
            return pic_url
        try:
            r = self.sess.get(pic_url, headers={
                "User-Agent": self.ua, "Referer": self.host + "/"}, timeout=10)
            if r.status_code == 200 and r.content:
                ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
                return "data:%s;base64,%s" % (
                    ct, base64.b64encode(r.content).decode("utf-8"))
        except Exception:
            pass
        return pic_url

    def _extract_vid(self, html_or_url):
        m = re.search(r'id="mse"[^>]*data-id="(\d+)"', html_or_url or "")
        if m:
            return m.group(1)
        m = re.search(r'data-id="(\d+)"', html_or_url or "")
        if m:
            return m.group(1)
        m = re.search(r"/(\d+)\.html", html_or_url or "")
        if m:
            return m.group(1)
        return ""

    # ---------- 分页元信息 ----------
    def _page_meta(self, html):
        """
        解析 <div id="pages" data-uri="..." data-nums="8505" data-page="1" data-size="7">
        返回 (uri模板, 总数, 每页条数, 当前页)
        """
        m = re.search(r'<div id="pages"[^>]*>', html)
        if not m:
            return "", 0, 0, 1
        tag = m.group(0)

        def attr(k, d=""):
            mm = re.search(k + r'="([^"]*)"', tag)
            return mm.group(1) if mm else d

        try:
            nums = int(attr("data-nums", "0") or 0)
        except Exception:
            nums = 0
        try:
            size = int(attr("data-size", "20") or 20)
        except Exception:
            size = 20
        try:
            cur = int(attr("data-page", "1") or 1)
        except Exception:
            cur = 1
        return attr("data-uri"), nums, (size or 20), cur

    # ---------- 播放接口（CSCMS ajax） ----------
    def _ajax_play(self, vid):
        """
        POST /ajax/videoplay  id=<vid>&ids=
        -> {"code":1,"playurl":"https://st.pgdjz.fun/%2Fzwmtv%2F...mp4","pic":"..."}
        返回 (playurl, pic)。playurl 保持 URL 编码原样，不要 unquote。
        """
        if not vid:
            return "", ""
        try:
            r = self.sess.post(
                self.host + "/ajax/videoplay",
                data={"id": vid, "ids": ""},
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer": self.host + "/",
                }, timeout=15)
            j = r.json()
            if str(j.get("code", "")) == "1" or j.get("playurl"):
                return (j.get("playurl") or ""), (j.get("pic") or "")
        except Exception:
            pass
        return "", ""

    def _scan_media_urls(self, text):
        """接口不可用时的回退：从 HTML 里扫直链"""
        if not text:
            return []
        out = []
        t = text.replace("\\/", "/")
        for pat in (r'<source[^>]+src=["\']([^"\']+)["\']',
                    r'<video[^>]+src=["\']([^"\']+)["\']'):
            out.extend(re.findall(pat, t, re.I))
        out.extend(re.findall(
            r'https?://[^\s"\'<>\\]+?\.(?:m3u8|mp4|flv|mkv)(?:\?[^\s"\'<>\\]*)?', t, re.I))
        res = []
        for u in out:
            u = self._fix(u.strip())
            if re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)", u, re.I) and u not in res:
                res.append(u)
        return res

    def _fetch_real_url(self, vid, detail_html=""):
        """优先官方接口，接口失败再回退 HTML 扫描"""
        pu, _ = self._ajax_play(vid)
        if pu:
            return [pu]
        return self._scan_media_urls(detail_html) if detail_html else []

    # ================= 列表解析 =================
    def _pick_title(self, inner):
        """从 name 块取正文标题 + 画质（去掉 <span>推</span> <span>超清</span>）"""
        spans = [self._clean(re.sub(r"<[^>]+>", "", s))
                 for s in re.findall(r"<span[^>]*>(.*?)</span>", inner, re.S)]
        quality = next((s for s in spans if s in ("超清", "高清", "标清", "蓝光")), "")
        title = self._clean(re.sub(r"<span[^>]*>.*?</span>", "", inner, flags=re.S))
        title = re.sub(r"(超清|高清|标清|蓝光)\s*$", "", title).strip()
        return title, quality

    def _parse_list(self, html):
        """统一按 <li> 块解析，兼容 A/B 两套 DOM；
        准入条件：块内 href 含 /(dance|video)/数字.html"""
        result, seen = [], set()
        if not html:
            return result

        for m in re.finditer(r"<li[^>]*>(.*?)</li>", html, re.S):
            block = m.group(1)

            lm = re.search(r'href="([^"]*/(?:dance|video)/\d+\.html)"', block)
            if not lm:
                continue
            url = self._abs(lm.group(1))
            if url in seen:
                continue
            seen.add(url)

            # 封面：块内第一张非占位图
            pic = ""
            for pm in re.finditer(r'<img[^>]+src="([^"]+)"', block, re.I):
                if not self._is_bad_pic(pm.group(1)):
                    pic = self._fix_pic(pm.group(1))
                    break

            # 标题：优先 class="name"，回退 img 的 title
            title, quality = "", ""
            nm = re.search(r'class="name"[^>]*>(.*?)</(?:a|div)>', block, re.S)
            if nm:
                title, quality = self._pick_title(nm.group(1))
            if not title:
                tm = re.search(r'<img[^>]+title="([^"]*)"', block, re.I)
                if tm:
                    title = self._clean(tm.group(1))
            if not title:
                continue

            # 备注：分类页取时长，首页取播放量
            remark = ""
            dm = re.search(r"播放时长：([^<]*)</div>", block)
            if dm:
                remark = self._clean(dm.group(1))
            if not remark:
                cm = re.search(r'<div class="click">(.*?)</div>', block, re.S)
                if cm:
                    remark = self._clean(cm.group(1))
            if quality:
                remark = (quality + " " + remark).strip()

            result.append({
                "vod_id": url,
                "vod_name": title,
                "vod_pic": self._wrap_pic(pic),
                "vod_remarks": remark,
            })
        return result

    def _parse_page(self, html):
        """
        只取主列表容器：
          1) 分类页/搜索页: <div class="zyvodlist"> ... <div class="pagebox">
          2) 首页          : <ul class="vodlist">（多个，合并）
        侧栏 <ul class="list"> 是纯文字推荐位、没有封面，必须排除，
        否则会混入无图条目导致海报墙空缺（同时保证主列表内容一条不丢）。
        """
        m = re.search(r'<div class="zyvodlist[^"]*">(.*?)<div class="pagebox"', html, re.S)
        if m:
            v = self._parse_list(m.group(1))
            if v:
                return v
        blocks = re.findall(r'<ul class="vodlist"[^>]*>(.*?)</ul>', html, re.S)
        if blocks:
            v = self._parse_list("".join(blocks))
            if v:
                return v
        return self._parse_list(html)

    # ================= CatVodSpider 标准接口 =================
    def homeContent(self, filter):
        """分类 + 筛选器（排序 8 选 1，对所有分类生效）"""
        sort_filter = [{"key": "sort", "name": "排序", "value": self.SORT_LIST}]
        filters = {}
        for c in self.class_list:
            filters[c["type_id"]] = sort_filter
        return {"class": self.class_list, "filters": filters}

    def homeVideoContent(self):
        return {"list": self._parse_page(self._get(self.host + "/video.html"))[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1

        # 筛选器选中的排序
        sort = ""
        try:
            if isinstance(extend, dict):
                sort = (extend.get("sort") or "").strip()
        except Exception:
            sort = ""

        # 分页格式：/video/lists/{sort}/{tid}/{page}.html（不是 tid-page！）
        mid = ("%s/%s" % (sort, tid)) if sort else str(tid)
        url = "%s/video/lists/%s/%d.html" % (self.host, mid, pg)

        html = self._get(url)
        vlist = self._parse_page(html)
        _, nums, size, cur = self._page_meta(html)

        # pagecount：优先用 data-nums / data-size 精确计算，让壳知道还能翻多少页
        if nums and size:
            pagecount = int(math.ceil(float(nums) / float(size)))
        else:
            pagecount = pg + 1 if vlist else pg
        if pagecount < 1:
            pagecount = 1

        return {
            "list": vlist,
            "page": cur or pg,
            "pagecount": pagecount,
            "limit": len(vlist) or size,
            "total": nums or 999999,
        }

    def detailContent(self, ids):
        url = self._abs(ids[0])
        html = self._get(url)
        vod = {"vod_id": url, "vod_name": "", "vod_pic": "", "vod_year": "",
               "vod_area": "", "vod_remarks": "", "vod_actor": "", "vod_director": "",
               "vod_content": "", "vod_play_from": "皮狗DJ", "vod_play_url": ""}

        vid = self._extract_vid(html) or self._extract_vid(url)
        if not html and not vid:
            vod["vod_name"] = url.split("/")[-1]
            return {"list": [vod]}

        # ---------- 标题 ----------
        # 站点 h1 里的标题被截断成 "...(跳舞D..." 且混入 <span>推</span>，
        # 因此优先用 vodinfo 主图的 title（完整标题），h1 仅作回退
        m = re.search(
            r'<div class="vodinfo">.*?<div class="img">\s*<img[^>]+title="([^"]*)"',
            html, re.S | re.I)
        if m and self._clean(m.group(1)):
            vod["vod_name"] = self._clean(m.group(1))
        if not vod["vod_name"]:
            m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
            if m:
                inner = re.sub(r"<(span|i|em|font|small)[^>]*>.*?</\1>", "",
                               m.group(1), flags=re.S)
                vod["vod_name"] = re.sub(
                    r"(超清|高清|标清|蓝光)\s*$", "", self._clean(inner)).strip()
        if not vod["vod_name"]:
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            if m:
                vod["vod_name"] = self._clean(m.group(1)).split("_")[0].split("-")[0].strip()

        # ---------- 封面（HTML 三级兜底 + 接口 pic）----------
        pic = ""
        m = re.search(
            r'<div class="vodinfo">.*?<div class="img">\s*<img[^>]+src="([^"]+)"',
            html, re.S | re.I)
        if m and not self._is_bad_pic(m.group(1)):
            pic = m.group(1)
        if not pic and vod["vod_name"]:
            key = re.escape(vod["vod_name"][:12])
            m = re.search(r'<img[^>]+src="([^"]+)"[^>]*title="[^"]*' + key, html, re.I)
            if m and not self._is_bad_pic(m.group(1)):
                pic = m.group(1)
        if not pic:
            for u in re.findall(
                    r'<img[^>]+src="(https?://tp\.pgdjz\.fun/[^"]+?\.(?:jpg|jpeg|png|webp))"',
                    html, re.I):
                if not self._is_bad_pic(u):
                    pic = u
                    break
        if not pic:
            m = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                html, re.I)
            if m and not self._is_bad_pic(m.group(1)):
                pic = m.group(1)

        # 播放地址（顺带拿到接口返回的 pic 作为封面最后兜底）
        real_urls = self._fetch_real_url(vid, html)
        if not pic:
            _, api_pic = self._ajax_play(vid)
            if api_pic and not self._is_bad_pic(api_pic):
                pic = api_pic
        vod["vod_pic"] = self._wrap_pic(self._fix_pic(pic))

        # ---------- 画质 / 年份（详情页补全）----------
        qm = re.search(r"<h1[^>]*>.*?<span[^>]*>(超清|高清|标清|蓝光)</span>", html, re.S)
        if qm:
            vod["vod_remarks"] = qm.group(1)
        if not vod["vod_remarks"]:
            qm = re.search(r"下载格式：<span>([^<]*)</span>", html)
            if qm:
                vod["vod_remarks"] = self._clean(qm.group(1))
        ym = re.search(r"更新时间：<span>(\d{4})", html)
        if ym:
            vod["vod_year"] = ym.group(1)
        am = re.search(r"所属分类：<a[^>]*>([^<]*)</a>", html)
        if am:
            vod["vod_area"] = self._clean(am.group(1))

        # ---------- 简介 ----------
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html, re.S)
        if m:
            vod["vod_content"] = self._clean(m.group(1))

        # ---------- 播放 ----------
        if real_urls:
            vod["vod_play_url"] = ("正片$" + real_urls[0]) if len(real_urls) == 1 else "#".join(
                "线路%d$%s" % (i + 1, u) for i, u in enumerate(real_urls))
        else:
            vod["vod_play_url"] = "正片$" + url

        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        """站点搜索参数是 key（不是 wd/keyword/q）；支持 &page=N 翻页"""
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1

        q = quote(key)
        url = "%s/video/search.html?key=%s&page=%d" % (self.host, q, pg)
        html = self._get(url)
        vlist = self._parse_page(html)
        _, nums, size, _cur = self._page_meta(html)

        # 越界保护：结果不足一页时仍传 page=N，站点会返回无关内容
        # （实测「DJ阿智」total=2，但 page=2 返回 15 条无关条目）
        if nums and size:
            pagecount = int(math.ceil(float(nums) / float(size)))
            if pg > pagecount:
                return {"list": [], "page": pg, "pagecount": pagecount,
                        "limit": size, "total": nums}
        else:
            pagecount = pg

        if not vlist and pg <= 1:
            # 兜底：不带 page 再试一次（个别壳传参异常）
            html = self._get("%s/video/search.html?key=%s" % (self.host, q))
            vlist = self._parse_page(html)
        if not vlist:
            return {"list": []}

        return {"list": vlist, "page": pg,
                "pagecount": max(pagecount, 1),
                "limit": len(vlist) or size, "total": nums or 999999}

    def playerContent(self, flag, id, vipFlags):
        header = json.dumps({"User-Agent": self.ua, "Referer": self.host + "/"},
                            ensure_ascii=False)
        # 已是直链（mp4/m3u8）直接播
        if re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)", id or "", re.I):
            return {"parse": 0, "playUrl": "", "url": id, "header": header}

        url = self._abs(id)
        html = self._get(url)
        vid = self._extract_vid(html) or self._extract_vid(url)
        real = self._fetch_real_url(vid, html)
        if real:
            return {"parse": 0, "playUrl": "", "url": real[0], "header": header}
        return {"parse": 1, "playUrl": "", "url": url, "header": header}

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            self.sess.close()
        except Exception:
            pass
