import aiohttp
import asyncio
from tqdm import tqdm
import os


'''
https://blog.csdn.net/weixin_34384681/article/details/89567190
'''
async def fetch(session, url, dst, pbar=None, headers=None):
    if headers:
        async with session.get(url, headers=headers) as req:
            with(open(dst, 'ab')) as f:
                while True:
                    chunk = await req.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    pbar.update(1024)
            pbar.close()
    else:
        async with session.get(url) as req:
            return req


async def async_download_from_url(url, dst):
    '''异步'''

    async with aiohttp.ClientSession() as session:
        req = await fetch(session, url, dst)

        file_size = int(req.headers['content-length'])
        print(f"获取视频总长度:{file_size}")
        if os.path.exists(dst):
            first_byte = os.path.getsize(dst)
        else:
            first_byte = 0
        if first_byte >= file_size:
            return file_size
        header = {"Range": f"bytes={first_byte}-{file_size}"}
        pbar = tqdm(
            total=file_size,
            initial=first_byte,
            unit='B',
            unit_scale=True,
            desc=dst)
        await fetch(session, url, dst, pbar=pbar, headers=header)


if __name__ == '__main__':
    url = "https://media.mbalib.com/ketang/1/13/139f488aee1d432c052a854d238d718c.mp3?auth_key=1604818302-0-0-a7551c54eedf6ec0cdd1a1a96da0819f"

    task = [asyncio.ensure_future(async_download_from_url(url, f"{1}.mp3"))]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(task))
    loop.close()