import urllib.request
import urllib
import re
import http.cookiejar
import uuid
from collections import deque
import os
import requests


class Weibo:
    def __init__(self, username, password, cookies, timeout=2, encoding="UTF-8"):
        self._cookies = {
            "Cookies": cookies
        }

        self._timeout = timeout
        self._encoding = "UTF-8"
        self._creat_page_name_method = None
        self._is_save_page = None
        self._page_save_path = None
        self._create_image_name_method = None
        self._is_save_image = None
        self._image_save_path = None
        self._image_min_size = None
        self._visited_image = set()

        self._weibo_url = "http://weibo.cn/"

        self._is_login = True

    def save_page(self, path, create_page_name_method=lambda: str(uuid.uuid4()) + ".htm"):
        self._creat_page_name_method = create_page_name_method
        self._is_save_page = True
        self._page_save_path = str(path)

    def not_save_page(self):
        self._is_save_page = False

    def __save_page_handle(self, data):
        file = open(self.page_save_path + self.create_page_name_method(), "w", encoding=self.encoding)
        file.write(data)
        file.close()

    def save_image(self, path, create_image_name_method=lambda: str(uuid.uuid4()), min_size=1000 * 10):
        self._image_min_size = min_size
        self._create_image_name_method = create_image_name_method
        self._is_save_image = True
        self._image_save_path = str(path)

    def not_save_image(self):
        self._is_save_image = False

    def __save_image_handle(self, data):
        reg = r'="([^\"]*?\.(png|jpg|bmp|gif|jpeg))"'
        imgre = re.compile(reg)
        imglist = re.findall(imgre, str(data))
        for img in imglist:
            imgurl, extend = img
            if imgurl in self._visited_image:
                continue;
            else:
                self._visited_image.add(imgurl)
            try:
                print("正在下载图片<---- " + imgurl)
                # image_path = self._image_save_path + str(imgurl).split("/")[-1]
                image_path = self._image_save_path + str(uuid.uuid4()) + "." + extend
                urllib.request.urlretrieve(imgurl, image_path)

                # 判断图片的大小，如果小于设定值，则删除
                image_size = os.path.getsize(image_path)
                if image_size < self._image_min_size:
                    os.remove(image_path)
                    print("图片大小：" + str(image_size) + " 小于阈值")
            except:
                continue

    def __makeMyOpener(self, head={
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko'
    }):
        '''
        获取请求
        :param head:
        :return:
        '''
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        header = []
        for key, value in head.items():
            elem = (key, value)
            header.append(elem)
            opener.addheaders = header
        return opener

    def start(self, first_handle_url=[], is_auto_reload=False):
        '''
        开始爬虫
        :return:
        '''
        if len(first_handle_url) == 0:
            first_handle_url.append(self._weibo_url)

        if not self._is_login:
            print("登录失败")
            return

        queue = deque()
        visited = set()

        queue.extend(first_handle_url)

        while queue:
            # 得到队头元素
            url = queue.popleft()
            if url in visited:
                continue
            # 把连接加入已访问set，防止重复爬
            visited.add(url)

            print('正在抓取 <---  ' + url)

            # 请求网站，得到内容
            try:
                data = requests.get(url, cookies=self._cookies).content
            except:
                print("连接：" + url + "超时")
                if url in first_handle_url:
                    visited.remove(url)
                    queue.append(url)

            # 判断是否保存页面
            if self._is_save_page:
                try:
                    # 在页面开头做标记
                    data = "<!--[" + url + "]-->\n" + data
                    self.__save_data_handle(data)
                except:
                    continue
            # 判断是否保存图片
            if self._is_save_image:
                self.__save_image_handle(data)
            # 匹配连接的正则表达式
            linker = re.compile('href=\"(.+?)\"')

            # 匹配当前页面下的所有连接
            for x in linker.findall(str(data)):
                # 如果连接中含有http字符，而且没有被访问过，则加入队列
                if x not in visited:
                    if "http" not in x and not x.startswith("/"):
                        continue
                    if x.startswith("/"):
                        x = self._weibo_url + x.replace("/", "", 1)
                    if "logout" in x:
                        continue
                    queue.append(x)
                    print("加入队列-----》" + x)


if __name__ == "__main__":
    Weibo = Weibo("", "",
                  cookies="SSOLoginState=1459488532; ALF=1462079720; SUB=_2A257-ndDDeRxGeRL4lsQ9CjMzjmIHXVZBRkLrDV6PUJbrdBeLW6ikW1LHetSvFyaB_NZFux8coMSrNTnlVLbHA..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WF7ry.y9bXPTG.BXwVuvz-_5JpX5o2p; SUHB=0IIkZQlyAstPkX; _T_WM=876034478fad398a40f646ad142e33ff; gsid_CTandWM=4uOGCpOz5UHGBlgwj9TWqaU9I0T; H5_INDEX=0_all; H5_INDEX_TITLE=%E5%A4%95%E4%B8%8B%E5%A5%95%E6%9E%97; M_WEIBOCN_PARAMS=uicode%3D20000061%26featurecode%3D20000180%26fid%3D3959441713315677%26oid%3D3959441713315677",
                  timeout=10)
    Weibo.save_image("D://spider/weibo/pictures/")
    queue = []

    queue.append("http://weibo.cn/2386199812/photo?tf=6_008")
    Weibo.start(first_handle_url=queue)