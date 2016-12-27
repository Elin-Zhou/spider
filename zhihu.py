import uuid
from collections import deque
import os
from bs4 import BeautifulSoup
import requests
import re
import time


class Zhihu:
    def __init__(self, username, password, timeout=2, encoding="UTF-8"):

        self._timeout = timeout
        self._encoding = "UTF-8"
        self._creat_page_name_method = create_page_name_method = lambda: str(uuid.uuid4()) + ".htm"
        self._is_save_page = None
        self._page_save_path = None
        self._is_save_image = None
        self._image_save_path = None
        self._image_min_size = None
        self._visited_image = set()
        self._image_extends = ["png", "jpg", "bmp", "gif", "jpeg"]
        self.__soup_dict = {}
        self._visited = set()
        self._queue = deque()

        self._zhihu_url = "https://www.zhihu.com/"
        self._session = requests.session()
        data = self._session.get(self._zhihu_url, timeout=self._timeout).text

        xsrf = self.__getXSRF(self._zhihu_url, data)

        # 组装请求参数
        post_data = {
            "_xsrf": xsrf,
            "password": password,
            "remember_me": "true"
        }
        # 根据用户名判断是邮箱登录还是手机号登录
        if "@" in username:
            login_add = "login/email"
            post_data["email"] = username
        else:
            login_add = "login/phone_num"
            post_data["phone_num"] = username

        r = self._session.post(self._zhihu_url + login_add, data=post_data)
        if "\\u767b\\u9646\\u6210\\u529f" in r.text:
            self._is_login = True
        else:
            self._is_login = False

    def save_page(self, path, create_page_name_method=lambda: str(uuid.uuid4()) + ".htm"):
        self._creat_page_name_method = create_page_name_method
        self._is_save_page = True
        self._page_save_path = str(path)

    def not_save_page(self):
        self._is_save_page = False

    def __save_page_handle(self, url, data, path=None):
        if not path:
            path = self._page_save_path
        file = open(path + self._creat_page_name_method(), "w", encoding=self._encoding)
        file.write(data)
        file.close()

    def _get_question_title(self, url, data):
        if "question" in url:
            soup = self.__get_soup(url, data)
            tag = soup.find("div", id="zh-question-title").find("h2", class_="zm-item-title zm-editable-content")

            return str(tag.string).strip()

    def save_image(self, path, min_size=1000 * 50):
        self._image_min_size = min_size
        self._is_save_image = True
        self._image_save_path = str(path)

    def not_save_image(self):
        self._is_save_image = False

    def __save_image_handle(self, url, data):
        soup = self.__get_soup(url, data)
        # 获取问题的title
        question_title = self._get_question_title(url, data)

        if question_title == None:
            question_title = "other"
        question_image_save_path = self._image_save_path + question_title + "/"
        if not os.path.exists(question_image_save_path):
            os.mkdir(question_image_save_path)
        # 保存照片时把原问题也保存起来
        self.__save_page_handle(url, data, path=question_image_save_path)

        # 获取所有的问题
        question_divs = soup.find_all("div", class_="zm-item-answer  zm-item-expanded")
        # 所有问题的数量
        question_num = len(question_divs)
        index = 1
        for div in question_divs:
            # 获取问题的点赞数,有可能出现K或M
            agree_string = str(div.find("span", class_="count").string)
            try:
                agree = int(agree_string)
            except:
                if "K" in agree_string:
                    agree_string = agree_string.replace("K", "000")
                elif "M" in agree_string:
                    agree_string = agree_string.replace("M", "000000")
                agree = int(agree_string)
            # 获取所有问题的前30%或被点赞数超过100的问题的照片
            if index < question_num * 0.3 or agree > 100:
                # 获取其中照片的url
                question_images = div.find("div", class_="zm-editable-content clearfix").find_all(
                        lambda tag: tag.has_attr("src"))
                for tag in question_images:
                    src = tag.attrs["src"]
                    if str(src).startswith("/"):
                        continue
                    extend_name = str(src).split(".")[-1]
                    # 判断该url是否为照片的url,且判断是否被访问过
                    if extend_name not in self._image_extends or src in self._visited_image:
                        continue
                    else:
                        self._visited_image.add(src)
                    try:
                        print("正在下载图片<---- " + src)

                        image_path = question_image_save_path + str(src).split("/")[-1]
                        if os.path.exists(image_path):
                            continue
                        image_file = open(image_path, "wb")
                        image_file.write(self._session.get(src).content)
                        image_file.close()
                        # 判断图片的大小，如果小于设定值，则删除
                        image_size = os.path.getsize(image_path)
                        if image_size < self._image_min_size:
                            os.remove(image_path)
                            print("图片大小：" + str(image_size) + " 小于阈值")
                    except:
                        continue

            index += 1

    def __get_soup(self, url, data):
        '''
        通过url获取soup
        :param url:
        :param data:
        :return:
        '''
        if url in self.__soup_dict:
            return self.__soup_dict[url]
        soup = BeautifulSoup(data)
        self.__soup_dict[url] = soup
        return soup

    def __save_logs(self, url):
        try:
            log_path = self._image_save_path + "visited_question.log"
            file = open(log_path, "a+", encoding=self._encoding)
            file.write(url + "|" + str(time.time()) + "\n")
            file.close()
        except:
            pass

    def load_logs(self, path, delay=10):
        try:
            file = open(path, "r", encoding=self._encoding)
            for line in file:
                url, t_time = line.split("|")
                if float(time.time()) - float(t_time) > delay * 24 * 3600:
                    continue
                else:
                    last = url
                    self._visited.add(url)
            # 为防止页面解析到一半被关掉,所以重新解析最后一张页面(在单线程的情况下)
            self._visited.remove(last)
            file.close()
        except:
            return


    def __save_links(self, links):
        try:
            log_path = self._image_save_path + "links.log"
            file = open(log_path, "a+", encoding=self._encoding)
            for link in links:
                file.write(link + "\n")
            file.close()
        except:
            pass

    def load_links(self, path):
        try:
            file = open(path, "r", encoding=self._encoding)
        except:
            return
        for line in file:
            self._queue.append(str(line).replace("\n", ""))
        file.close()

    def __need_resolve(self, url, data):
        if "zhihu" not in url:
            return False
        if "question" in url:
            if int(self.__get_answer_num(url, data)) < 5:
                print("问题:" + self._get_question_title(url, data) + "回答数量过少,跳过解析")
                return False
            else:
                print("开始解析问题:" + self._get_question_title(url, data))
                return True
        elif "people" in url:
            if int(self._get_aggree_num_in_people(url, data)) < 100:
                print("用户:" + self.__get_people_name(url, data) + "被赞同数过少,跳过解析")
                return False
            else:
                print("开始解析用户:" + self.__get_people_name(url, data))
                return True
        return True

    def _get_aggree_num_in_people(self, url, data):
        if "people" not in url:
            return 0
        soup = self.__get_soup(url, data)
        try:
            aggress_num = soup.find("span", class_="zm-profile-header-user-agree").find("strong").string
        except:
            return 0
        return aggress_num

    def __get_people_name(self, url, data):
        if "people" not in url:
            return ""
        soup = self.__get_soup(url, data)
        try:
            name = soup.find("div", class_="title-section ellipsis").find("span", class_="name").string
        except:
            return ""
        return name;

    def __get_answer_num(self, url, data):
        if "question" not in url:
            return 0
        soup = self.__get_soup(url, data)
        question_divs = soup.find_all("div", class_="zm-item-answer  zm-item-expanded")
        # 所有问题的数量
        question_num = len(question_divs)
        return question_num

    def __getXSRF(self, url, data):
        '''
        获取登录必要参数
        :param data:
        :return:
        '''
        soup = self.__get_soup(url, data)
        return soup.find_all("input", attrs={"name": "_xsrf"})[0].attrs["value"]

    def start(self, first_handle_url=[], is_auto_reload=False):
        '''
        开始爬虫
        :return:
        '''
        if len(first_handle_url) == 0:
            first_handle_url.append(self._zhihu_url)

        if not self._is_login:
            print("登录失败")
            return

        self._queue.extendleft(first_handle_url)

        while queue:

            try:

                # 得到队头元素
                url = self._queue.popleft()
                if not str(url).endswith("/"):
                    url += "/"
                if url in self._visited:
                    continue
                # 把连接加入已访问set，防止重复爬
                self._visited.add(url)
                self.__save_logs(url)

                print('正在抓取 <---  ' + url)

                # 请求网站，得到内容
                try:
                    r = self._session.get(url, timeout=self._timeout)

                except:
                    print("连接：" + url + "超时")
                    if url in first_handle_url:
                        self._visited.remove(url)
                        self._queue.append(url)
                        # if is_auto_reload:
                        #     visited.remove(url)
                        #     queue.append(url)
                # 判断得到的连接类型是否为http，过滤css、js等内容
                if "html" not in r.headers.get("Content-Type"):
                    continue
                try:
                    data = r.text
                except:
                    print("read出错")

                if not self.__need_resolve(url, data):
                    continue
                # 判断是否保存页面
                if self._is_save_page:
                    try:
                        # 在页面开头做标记
                        data = "<!--[" + url + "]-->\n" + data
                        self.__save_page_handle(url, data)
                    except:
                        continue
                # 判断是否保存图片
                if self._is_save_image and "question" in url:
                    self.__save_image_handle(url, data)
                # 匹配连接的正则表达式
                linker = re.compile('href=\"(.+?)\"')

                temp_links = []
                # 匹配当前页面下的所有连接
                for x in linker.findall(data):
                    # 如果连接中含有http字符，而且没有被访问过，则加入队列
                    if "question" in x and "answer" in x:
                        # 表示该链接为某个问题下的回答,所以取出原问题链接
                        # https://www.zhihu.com/question/24715519/answer/83129179
                        index = x.index("answer")
                        x = x[0:index]
                    if not str(x).endswith("/"):
                        x += "/"
                    if x not in self._visited:
                        if "http" not in x and not x.startswith("/"):
                            continue
                        if x.startswith("/"):
                            x = self._zhihu_url + x.replace("/", "", 1)
                        # temp_link.append(x)
                        temp_links.append(x)
                self.__save_links(temp_links)
                self._queue.extend(temp_links)
            except:
                continue


if __name__ == "__main__":
    zhihu = Zhihu("", "", timeout=10)
    zhihu.save_image("/Users/ElinZhou/Documents/爬虫/zhihu/girls/")
    zhihu.load_logs("/Users/ElinZhou/Documents/爬虫/zhihu/girls/visited_question.log")
    zhihu.load_links("/Users/ElinZhou/Documents/爬虫/zhihu/girls/links.log")
    # zhihu.save_page("")
    queue = []


    queue.append("http://www.zhihu.com/collection/60771406")
    queue.append("http://www.zhihu.com/collection/30256531")
    queue.append("http://www.zhihu.com/collection/61623874")
    queue.append("http://www.zhihu.com/collection/61633672")
    queue.append("http://www.zhihu.com/collection/53719722")
    queue.append("http://www.zhihu.com/collection/36731404")
    queue.append("http://www.zhihu.com/collection/38624707")
    queue.append("http://www.zhihu.com/collection/26347524")
    queue.append("http://www.zhihu.com/collection/26815754")
    queue.append("http://www.zhihu.com/collection/26348030")
    queue.append("http://www.zhihu.com/collection/40246665")
    queue.append("http://www.zhihu.com/collection/25971719")
    queue.append("http://www.zhihu.com/collection/30822111")
    queue.append("https://www.zhihu.com/collection/60908509")
    queue.append("https://www.zhihu.com/collection/60771406")
    zhihu.start(first_handle_url=queue)