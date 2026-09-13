# -*- coding: utf-8 -*-
# sxymymy_spider.py - TVBox/OK影视(FongMi) 爬虫脚本 (修复版)
# 目标站点: http://www.sxymymy.com/ (八度影院)
# 适用平台: TVBox / OK影视 / 影视仓 / FongMi 等 Python Spider 环境
# 兼容 Python 2.7 / 3.x，仅用标准库

import sys
import json
import re

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass


class Spider(BaseSpider):
    siteUrl = 'http://www.sxymymy.com'

    def init(self, extend=""):
        if extend:
            try:
                ext = json.loads(extend)
                if 'host' in ext:
                    self.siteUrl = ext['host']
            except Exception:
                pass

    def getName(self):
        return "八度影院"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ========== 网络请求 ==========
    def _fetch(self, url, headers=None, timeout=15):
        try:
            import ssl
            if hasattr(ssl, '_create_unverified_context'):
                ssl_context = ssl._create_unverified_context()
            else:
                ssl_context = None
            if sys.version_info[0] == 3:
                from urllib import request as urllib2
                from urllib.parse import quote, unquote
            else:
                import urllib2
                from urllib import quote, unquote
            if not headers:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                    'Referer': self.siteUrl + '/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                }
            req = urllib2.Request(url, headers=headers)
            if ssl_context:
                resp = urllib2.urlopen(req, timeout=timeout, context=ssl_context)
            else:
                resp = urllib2.urlopen(req, timeout=timeout)
            html = resp.read()
            if sys.version_info[0] == 3 and isinstance(html, bytes):
                html = html.decode('utf-8', errors='ignore')
            return html
        except Exception:
            return ''

    # ========== 通用 HTML 解析辅助 ==========

    @staticmethod
    def _attr(tag, attr):
        """从标签字符串中提取指定属性值"""
        m = re.search(r'%s=["\']([^"\']*)["\']' % attr, tag, re.S)
        return m.group(1) if m else ''

    def _extract_vodlist(self, html):
        """从 HTML 中提取影片列表——新版更健壮，不依赖属性顺序"""
        result = []
        if not html:
            return result
        try:
            # 方式1: 提取完整的 <a class="myui-vodlist__thumb ..."> ... </a> 标签块
            # 找到开标签，然后向后匹配到 </a>（非贪婪但避免嵌套 a）
            thumbs = re.findall(
                r'(<a[^>]*class=["\']myui-vodlist__thumb[^"\']*["\'][^>]*>.*?</a>)',
                html, re.S | re.I
            )
            for block in thumbs:
                # 从开标签提取属性
                m_tag = re.match(r'<a[^>]*>', block, re.S)
                if not m_tag:
                    continue
                open_tag = m_tag.group(0)
                href = self._attr(open_tag, 'href')
                title = self._attr(open_tag, 'title')
                pic = self._attr(open_tag, 'data-original')
                if not href:
                    continue
                vid_match = re.search(r'/mym/(\d+)\.html', href)
                if not vid_match:
                    continue
                vod_id = vid_match.group(1)
                if pic and not pic.startswith('http'):
                    pic = self.siteUrl + ('' if pic.startswith('/') else '/') + pic
                # 从 block 中提取 pic-text
                pt = re.search(r'<span[^>]*class=["\']pic-text[^"\']*["\'][^>]*>(.*?)</span>', block, re.S)
                remarks = re.sub(r'<[^>]+>', '', pt.group(1)).strip() if pt else ''
                result.append({
                    'vod_id': vod_id,
                    'vod_name': title.strip(),
                    'vod_pic': pic,
                    'vod_remarks': remarks,
                    'vod_score': ''
                })
            # 如果没有匹配到，尝试方式2: 用 li 级别正则（更宽松）
            if not result:
                lis = re.findall(r'<li[^>]*>(.*?)</li>', html, re.S)
                for li in lis:
                    a_tag = re.search(r'<a[^>]*class=["\']myui-vodlist__thumb[^"\']*["\'][^>]*>', li, re.S)
                    if not a_tag:
                        continue
                    tag = a_tag.group(0)
                    href = self._attr(tag, 'href')
                    title = self._attr(tag, 'title')
                    pic = self._attr(tag, 'data-original')
                    if not href:
                        continue
                    vid_match = re.search(r'/mym/(\d+)\.html', href)
                    if not vid_match:
                        continue
                    vod_id = vid_match.group(1)
                    if pic and not pic.startswith('http'):
                        pic = self.siteUrl + ('' if pic.startswith('/') else '/') + pic
                    # 提取 pic-text
                    pic_text = re.search(r'<span[^>]*class=["\']pic-text[^"\']*["\'][^>]*>(.*?)</span>', li, re.S)
                    remarks = re.sub(r'<[^>]+>', '', pic_text.group(1)).strip() if pic_text else ''
                    result.append({
                        'vod_id': vod_id,
                        'vod_name': title.strip(),
                        'vod_pic': pic,
                        'vod_remarks': remarks,
                        'vod_score': ''
                    })
        except Exception:
            pass
        return result

    def _extract_detail(self, html):
        """从详情页提取影片详情——修复字段匹配"""
        result = {}
        if not html:
            return result
        try:
            # 封面: data-original 或 src
            pic = self._attr_tag(html, 'img', 'data-original')
            if not pic:
                pic = self._attr_tag(html, 'img', 'src')
            result['vod_pic'] = pic
            if pic and not pic.startswith('http'):
                result['vod_pic'] = self.siteUrl + ('' if pic.startswith('/') else '/') + pic

            # 标题: h1
            h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            result['vod_name'] = re.sub(r'<[^>]+>', '', h1.group(1)).strip() if h1 else ''

            # 分类、地区、年份、主演、导演、简介 —— 统一提取逻辑
            def _text_after_label(label):
                # 查找 <span class="text-muted...">分类：</span> 后的第一个 <a> 文本
                # 或紧跟的文本
                pat = r'<span[^>]*class=["\']text-muted[^"\']*["\'][^>]*>%s</span>\s*(.*?)(?:</p>|</div>|<br|<span)' % re.escape(label)
                m = re.search(pat, html, re.S)
                if not m:
                    return ''
                text = m.group(1)
                # 提取所有 <a> 标签内的文本，或纯文本
                links = re.findall(r'>([^<]+)</a>', text)
                if links:
                    return ','.join([x.strip() for x in links if x.strip()])
                return re.sub(r'<[^>]+>', '', text).strip()

            result['vod_type'] = _text_after_label('分类：')
            result['vod_area'] = _text_after_label('地区：')
            result['vod_year'] = _text_after_label('年份：')
            result['vod_actor'] = _text_after_label('主演：')
            result['vod_director'] = _text_after_label('导演：')

            # 简介
            desc = _text_after_label('简介：')
            result['vod_content'] = desc

            # 播放源解析
            vod_play_from = []
            vod_play_url = []

            # 提取所有播放源标签
            source_tabs = re.findall(r'<a[^>]*href=["\']#playlist(\d+)["\'][^>]*>(.*?)</a>', html, re.S)
            source_map = {}
            for sid, sname in source_tabs:
                sname = re.sub(r'<[^>]+>', '', sname).strip()
                if sname:
                    source_map[int(sid)] = sname

            for sid in sorted(source_map.keys()):
                sname = source_map[sid]
                vod_play_from.append(sname)
                # 提取对应 playlist 块内的剧集
                # 先找到 <div id="playlistN">...</div>（到 </div>，但要限制在下一个 playlist 或 myui-panel 之前）
                block_pat = r'<div[^>]*id=["\']playlist%s["\'][^>]*>(.*?)</ul>' % sid
                block_m = re.search(block_pat, html, re.S)
                episodes = []
                if block_m:
                    block = block_m.group(1)
                    ep_matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', block, re.S)
                    for ep_url, ep_name in ep_matches:
                        ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                        if ep_name:
                            episodes.append(ep_name + '$' + ep_url)
                vod_play_url.append('#'.join(episodes))

            result['vod_play_from'] = '$$$'.join(vod_play_from) if vod_play_from else ''
            result['vod_play_url'] = '$$$'.join(vod_play_url) if vod_play_url else ''

        except Exception:
            pass
        return result

    @staticmethod
    def _attr_tag(html, tag, attr):
        """从 html 中第一个匹配 tag 提取属性"""
        m = re.search(r'<%s[^>]*%s=["\']([^"\']*)["\'][^>]*>' % (tag, attr), html, re.S | re.I)
        return m.group(1) if m else ''

    def _extract_categories(self, html):
        """提取分类导航"""
        categories = []
        try:
            # 匹配主导航 /syv/数字.html
            items = re.findall(r'<a[^>]*href=["\']/syv/(\d+)\.html["\'][^>]*>([^<]+)</a>', html, re.S)
            seen = set()
            for cid, cname in items:
                cname = cname.strip()
                if cname and cid not in seen:
                    seen.add(cid)
                    categories.append({'type_id': cid, 'type_name': cname})
        except Exception:
            pass
        if not categories:
            categories = [
                {'type_id': '1', 'type_name': '电影'},
                {'type_id': '2', 'type_name': '电视剧'},
                {'type_id': '3', 'type_name': '综艺'},
                {'type_id': '4', 'type_name': '动漫'},
                {'type_id': '36', 'type_name': '短剧'},
            ]
        return categories

    # ========== 接口方法 ==========

    def homeContent(self, filter):
        result = {}
        try:
            html = self._fetch(self.siteUrl + '/')
            result['class'] = self._extract_categories(html)

            # 首页推荐: 从所有 myui-vodlist__thumb 中提取
            vods = self._extract_vodlist(html)
            # 去重
            seen = set()
            unique = []
            for vod in vods:
                if vod['vod_id'] not in seen:
                    seen.add(vod['vod_id'])
                    unique.append(vod)
            result['list'] = unique
        except Exception:
            result['class'] = self._extract_categories('')
            result['list'] = []
        return result

    def homeVideoContent(self):
        result = {}
        try:
            html = self._fetch(self.siteUrl + '/')
            vods = self._extract_vodlist(html)
            seen = set()
            unique = []
            for vod in vods:
                if vod['vod_id'] not in seen:
                    seen.add(vod['vod_id'])
                    unique.append(vod)
            result['list'] = unique
        except Exception:
            result['list'] = []
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        try:
            # 统一转字符串
            tid = str(tid)
            pg = str(pg) if pg else '1'
            # URL: /show/{tid}-----------.html (第一页)
            #      /show/{tid}--------{pg}---.html (其他页)
            if pg == '1' or not pg:
                url = self.siteUrl + '/show/' + tid + '-----------.html'
            else:
                url = self.siteUrl + '/show/' + tid + '--------' + pg + '---.html'

            html = self._fetch(url)
            if not html:
                result['list'] = []
                result['page'] = int(pg)
                result['pagecount'] = 1
                result['limit'] = 12
                result['total'] = 0
                return result

            vods = self._extract_vodlist(html)
            result['list'] = vods

            # 分页提取
            pagecount = 1
            # 尾页链接
            last_m = re.search(r'/show/' + re.escape(tid) + r'--------(\d+)---\.html[^"\']*["\'][^>]*>尾页', html)
            if last_m:
                pagecount = int(last_m.group(1))
            else:
                # 页码文本 "1/979"
                nums = re.search(r'>(\d+)/(\d+)<', html)
                if nums:
                    pagecount = int(nums.group(2))
                else:
                    # 从所有分页链接找最大页码
                    pages = re.findall(r'/show/' + re.escape(tid) + r'--------(\d+)---\.html', html)
                    if pages:
                        pagecount = max([int(p) for p in pages])
                    elif len(vods) > 0 and int(pg) > 1:
                        pagecount = int(pg)

            result['page'] = int(pg)
            result['pagecount'] = pagecount
            result['limit'] = 12
            result['total'] = pagecount * 12
        except Exception:
            result['list'] = []
            result['page'] = int(pg) if pg else 1
            result['pagecount'] = 1
            result['limit'] = 12
            result['total'] = 0
        return result

    def detailContent(self, ids):
        result = {}
        try:
            vid = str(ids[0])
            url = self.siteUrl + '/mym/' + vid + '.html'
            html = self._fetch(url)
            if not html:
                result['list'] = []
                return result

            detail = self._extract_detail(html)
            if not detail.get('vod_name'):
                result['list'] = []
                return result

            detail['vod_id'] = vid
            detail['vod_score'] = ''

            # 确保播放 URL 是完整路径
            if detail.get('vod_play_url'):
                parts = detail['vod_play_url'].split('$$$')
                fixed_parts = []
                for part in parts:
                    eps = part.split('#')
                    fixed_eps = []
                    for ep in eps:
                        if '$' in ep:
                            name, u = ep.split('$', 1)
                            if u and not u.startswith('http'):
                                u = self.siteUrl + ('' if u.startswith('/') else '/') + u
                            fixed_eps.append(name + '$' + u)
                        else:
                            fixed_eps.append(ep)
                    fixed_parts.append('#'.join(fixed_eps))
                detail['vod_play_url'] = '$$$'.join(fixed_parts)

            result['list'] = [detail]
        except Exception:
            result['list'] = []
        return result

    def searchContent(self, key, quick):
        return self.searchContentPage(key, quick, '1')

    def searchContentPage(self, key, quick, pg):
        result = {}
        try:
            if sys.version_info[0] == 3:
                from urllib.parse import quote
            else:
                from urllib import quote
            encoded_key = quote(key.encode('utf-8'))
            url = self.siteUrl + '/search/' + encoded_key + '-------------.html'
            html = self._fetch(url)
            if not html:
                result['list'] = []
                result['page'] = int(pg)
                result['pagecount'] = 0
                result['limit'] = 12
                result['total'] = 0
                return result

            vods = self._extract_vodlist(html)
            result['list'] = vods
            result['page'] = int(pg)
            result['pagecount'] = 1
            result['limit'] = 12
            result['total'] = len(vods)
        except Exception:
            result['list'] = []
            result['page'] = int(pg)
            result['pagecount'] = 0
            result['limit'] = 12
            result['total'] = 0
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            url = id
            if not url.startswith('http'):
                url = self.siteUrl + ('' if url.startswith('/') else '/') + url

            html = self._fetch(url)
            if not html:
                result['parse'] = 0
                result['playUrl'] = ''
                result['url'] = ''
                return result

            # 提取 player_aaaa JSON
            player_match = re.search(r'player_aaaa\s*=\s*(\{[^<]+\})', html)
            if player_match:
                try:
                    player_data = json.loads(player_match.group(1))
                    play_url = player_data.get('url', '')
                    if play_url:
                        result['parse'] = 0
                        result['playUrl'] = ''
                        result['url'] = play_url
                        result['header'] = json.dumps({
                            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                            'Referer': self.siteUrl + '/'
                        })
                        return result
                except Exception:
                    pass

            # 备选: 直接提取 m3u8/mp4
            for pat in [r'(https?://[^\s\'"<>]+\.m3u8)', r'(https?://[^\s\'"<>]+\.mp4)']:
                m = re.search(pat, html)
                if m:
                    result['parse'] = 0
                    result['playUrl'] = ''
                    result['url'] = m.group(1)
                    result['header'] = json.dumps({
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                        'Referer': self.siteUrl + '/'
                    })
                    return result

            result['parse'] = 0
            result['playUrl'] = ''
            result['url'] = ''
        except Exception:
            result['parse'] = 0
            result['playUrl'] = ''
            result['url'] = ''
        return result

    def localProxy(self, param):
        return [200, "video/MP2T", "", ""]


# ========== 独立调试入口 ==========
if __name__ == '__main__':
    spider = Spider()
    spider.init(json.dumps({"host": "http://www.sxymymy.com"}))

    print("=== homeContent ===")
    res = spider.homeContent(True)
    print(json.dumps(res, ensure_ascii=False, indent=2))

    print("\n=== categoryContent (tid=2, pg=1) ===")
    res = spider.categoryContent('2', '1', False, '')
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("  列表数量:", len(res.get('list', [])))

    if res.get('list'):
        vid = res['list'][0]['vod_id']
        print("\n=== detailContent (id=%s) ===" % vid)
        res2 = spider.detailContent([vid])
        print(json.dumps(res2, ensure_ascii=False, indent=2))

        if res2.get('list') and res2['list'][0].get('vod_play_url'):
            play_url_parts = res2['list'][0]['vod_play_url'].split('$$$')
            if play_url_parts and play_url_parts[0]:
                first_ep = play_url_parts[0].split('#')[0]
                if '$' in first_ep:
                    ep_name, ep_url = first_ep.split('$', 1)
                    print("\n=== playerContent (url=%s) ===" % ep_url)
                    res3 = spider.playerContent('', ep_url, [])
                    print(json.dumps(res3, ensure_ascii=False, indent=2))

    print("\n=== searchContent (key=独行月球) ===")
    res4 = spider.searchContent('独行月球', False)
    print(json.dumps(res4, ensure_ascii=False, indent=2))
    print("  搜索结果数量:", len(res4.get('list', [])))
