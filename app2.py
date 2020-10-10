import requests
from lxml import etree
import aiohttp
import asyncio
import os
import pickle
import psutil
from tqdm import tqdm

USERNAME = "13486489788"
PASSWORD = "hc123456"
SESSION = "./session.pkl"
FILEPATH = f"{os.path.dirname(__file__)}/data"
if not os.path.exists(FILEPATH):
    os.makedirs(FILEPATH)


class Application:

    def __init__(self):
        self.login()

    def loginCheck(self):
        if not os.path.exists(SESSION):
            return

        with open(SESSION, "rb")as file:
            sess = pickle.load(file)
        checkurl = "https://www.mbalib.com/"
        response = sess.get(checkurl)
        if "欢迎您" in response.text:
            self.sess = sess
            print("--登录成功--")
            return True
        else:
            print("--登录失败--")
            return

    def login(self):
        if self.loginCheck():
            return True

        self.sess = requests.Session()
        self.sess.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'
        }
        formData = {
            "type": "mobile",
            "username": USERNAME,
            "password": PASSWORD,
            "imgcode": "",
            "areaCode": "86"
        }
        loginUrl = "https://passport.mbalib.com/login/ajaxlogin"
        response = self.sess.post(loginUrl, data=formData)
        if response.json().get("state", "") == "success":
            with open("./session.pkl", "wb")as file:
                pickle.dump(self.sess, file)
            return True

        return False

    def getClassFile(self, link):
        response = self.sess.get(link)
        html = etree.HTML(response.text)
        fileUrlList = []
        className = html.xpath("//title/text()")[0].replace("- MBA智库 · 课堂", "").strip()
        for lab_a in html.xpath('//div[@class="landscape-none"]/div[1]/div/div/div[@class="ke-lay2"]/a'):
            videoUrl = lab_a.xpath("@data-url")[0]
            videoTitle = lab_a.xpath("@data-title")[0]
            pptImage = lab_a.xpath("@data-ware")
            if pptImage:
                pptList = [i["pic"] for i in eval(pptImage[0])]
            else:
                pptList = []
            fileUrlList.append((videoUrl, videoTitle, pptList))

        return fileUrlList, className

    async def downloadFile(self, semaphore, file_name, file_link, className, referer):
        filePath = f"{FILEPATH}/{className}"
        if not os.path.exists(filePath):
            os.makedirs(filePath)

        async with semaphore:
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': referer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'

            }
            async with aiohttp.ClientSession(headers=headers) as session:
                try:
                    print(f"{file_name}/正在下载")
                    if "mp4" in file_link:
                        file_path = f"{filePath}/{file_name}.mp4"
                    elif "mp3" in file_link:
                        file_path = f"{filePath}/{file_name}.mp3"
                    elif "jpg" in file_link or "png" in file_link:
                        file_path = f"{filePath}/{file_name}.jpg"

                    async with await session.get(file_link) as resp:

                        file_size = int(resp.headers['Content-Length'])
                        print(f"获取视频总长度:{file_size}")
                        if os.path.exists(file_path):
                            first_byte = os.path.getsize(file_path)
                        else:
                            first_byte = 0
                        if first_byte >= file_size:
                            return file_size
                        with open(file_path, 'wb') as f:
                            while True:
                                with tqdm(total=file_size, initial=first_byte,unit='B', unit_scale=True, desc=file_name)as t:
                                    chunk = await resp.content.read(1024)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                                    t.update(1024)
                        t.close()
                except:
                    pass

    async def taskManager(self, className, dataList, func, referer):
        tasks = []
        cpu_num = psutil.cpu_count()
        semaphore = asyncio.Semaphore(cpu_num)
        for data in dataList:
            file_name = data[1]
            file_link = data[0]
            task = asyncio.ensure_future(func(semaphore, file_name, file_link, className, referer))
            tasks.append(task)
            pptImage = data[-1]
            if pptImage:
                for index, img in enumerate(pptImage):
                    task = asyncio.ensure_future(func(semaphore, f"{file_name}-{index}", img, className, referer))
                    tasks.append(task)


    def start(self):
        while True:
            link = input("请输入课程链接：")
            fileList, className = self.getClassFile(link)
            print(f"--成功获取到【{className}】：{len(fileList)}节课程--")
            print("--进入下载任务,请耐心等待--")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.taskManager(className, fileList, self.downloadFile, link))

            loop.close()
            print("--下载完成--")


if __name__ == '__main__':
    # url = "https://ke.mbalib.com/column/play?id=287"
    url = "https://ke.mbalib.com/column/play?id=237&mid=10070"
    app = Application()
    app.start()
