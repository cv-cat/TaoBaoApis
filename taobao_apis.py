'''
Description: 
Date: 2026-04-04 15:32:48
LastEditTime: 2026-04-06 19:10:56
FilePath: \TaobaoApis\taobao_apis.py
'''
import json
import os
import re
import time

import requests

from utils.taobao_utils import generate_sign, trans_cookies, generate_device_id


class TaobaoApis:
    def __init__(self, cookies, device_id):
        self.login_url = 'https://h5api.m.taobao.com/h5/mtop.taobao.login.token.get.h5/2.0/'
        self.upload_media_url = 'https://stream-upload.taobao.com/api/upload.api'
        self.refresh_token_url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.loginuser.get/1.0/'
        self.item_detail_url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/'
        self.reset_login_info_url = 'https://passport.goofish.com/newlogin/hasLogin.do'
        self.session = requests.Session()
        self.session.cookies.update(cookies)
        self.device_id = device_id
        self.cookies = {}

    def get_token(self):
        headers = {
            "accept": "*/*",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,ja;q=0.6",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://market.m.taobao.com/",
            "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        }
        params = {
            "jsv": "2.7.0",
            "appKey": "12574478",
            "t": int(time.time()) * 1000,
            "sign": "43e3268d639f0f8b275569b25d9089e8",
            "api": "mtop.taobao.login.token.get.h5",
            "v": "2.0",
            "preventFallback": "true",
            "type": "jsonp",
            "dataType": "jsonp",
            "callback": "mtopjsonp3",
        }
        data_val = '{"domain":"cntaobao","deviceId":"' + self.device_id + '","locale":"zh_CN","imAppKey":"3ce2dacdc7c0c43ad7bc7f9bc7d7a1b8"}'
        params["data"] = data_val
        token = self.session.cookies['_m_h5_tk'].split('_')[0]
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        response = self.session.get(self.login_url, params=params, headers=headers)
        for response_cookie_key in response.cookies.get_dict().keys():
            if response_cookie_key in self.session.cookies.get_dict().keys():
                for key in self.session.cookies:
                    if key.name == response_cookie_key and key.domain == '' and key.path == '/':
                        self.session.cookies.clear(domain=key.domain, path=key.path, name=key.name)
                        break
        res_text = response.text
        res_text = re.findall(r' mtopjsonp3\((.*)\)', res_text)[0]
        res_json = json.loads(res_text)
        if 'ret' in res_json and '令牌过期' in res_json['ret'][0]:
            return self.get_token()
        return res_json

    # 类似于 https://detail.tmall.com/item.htm?id=806319949537&mi_id=0000vtiP2t7OiKuXSFJ6Os3CycYK4LfNyLsSkxffiJKUvKY&pvid=e2456346-6c21-490b-8792-abbcafc52e3a&scm=1007.40986.467924.0&skuId=5652727063890&spm=a21bo.jianhua%2Fa.201876.d12.78632a89Xn5WRG&utparam=%7B%22item_ctr%22%3A0.05020460486412048%2C%22x_object_type%22%3A%22item%22%2C%22matchType%22%3A%22nann_base%22%2C%22item_price%22%3A%222.5%22%2C%22item_cvr%22%3A0.043365806341171265%2C%22umpCalled%22%3Atrue%2C%22pc_ctr%22%3A0.009324726648628712%2C%22pc_scene%22%3A%2220001%22%2C%22userId%22%3A3888777108%2C%22ab_info%22%3A%2230986%23467924%230_30986%23528214%2358507_30986%23527806%2358418_30986%23537217%2360408_30986%23521582%2357267_30986%23543870%2358189_30986%23533297%2359487_30986%23528945%2357910_30986%23530923%2359037_30986%23532805%2359017_30986%23528109%2358485_30986%23537488%2360469_30986%23537987%2360586_30986%23538037%2360595%22%2C%22tpp_buckets%22%3A%2230986%23467924%230_30986%23528214%2358507_30986%23527806%2358418_30986%23537217%2360408_30986%23521582%2357267_30986%23543870%2358189_30986%23533297%2359487_30986%23528945%2357910_30986%23530923%2359037_30986%23532805%2359017_30986%23528109%2358485_30986%23537488%2360469_30986%23537987%2360586_30986%23538037%2360595%22%2C%22aplus_abtest%22%3A%2215c0e693256f7b7c9626be50c2718cbe%22%2C%22isLogin%22%3Atrue%2C%22abid%22%3A%22528214_527806_537217_521582_543870_533297_528945_530923_532805_528109_537488_537987_538037%22%2C%22pc_pvid%22%3A%22e2456346-6c21-490b-8792-abbcafc52e3a%22%2C%22isWeekLogin%22%3Afalse%2C%22pc_alg_score%22%3A0.0932632202314%2C%22rn%22%3A11%2C%22item_ecpm%22%3A0%2C%22ump_price%22%3A%222.5%22%2C%22isXClose%22%3Afalse%2C%22x_object_id%22%3A806319949537%7D&xxc=home_recommend
    def get_goods_uid_encrypt_uid(self, goods_url):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "referer": "https://www.taobao.com/",
            "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        }
        response = self.session.get(goods_url, headers=headers)
        res_text = response.text
        uid = re.findall(r'"userId":"(.*?)"', res_text)[0]
        encrypt_uid = re.findall(r'data-encryptuid="(.*?)"', res_text)[0]
        return {
            'uid': uid,
            'encrypt_uid': encrypt_uid
        }

    def upload_media(self, media_path):
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,zh-TW;q=0.7,ja;q=0.6",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Origin": "https://market.m.taobao.com",
            "Pragma": "no-cache",
            "Referer": "https://market.m.taobao.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        params = {
            "appkey": "ampmedia",
            "folderId": "0",
            "_input_charset": "utf-8",
            "useGtrSessionFilter": "false"
        }
        with open(media_path, 'rb') as f:
            media_name = os.path.basename(media_path)
            files = {
                "name": (None, media_name, None),
                "ua": (None, headers['User-Agent'], None),
                "file": (media_name, f, "image/png")
            }
            response = self.session.post(self.upload_media_url, headers=headers, params=params, files=files)
            res_json = response.json()
            return res_json

if __name__ == '__main__':
    cookies_str = r''
    cookies = trans_cookies(cookies_str)
    taobao = TaobaoApis(cookies, generate_device_id(cookies['unb']))

    # res = taobao.get_token()
    # print(json.dumps(res, indent=4, ensure_ascii=False))

    # goods_url = r'https://detail.tmall.com/item.htm?id=806319949537&mi_id=0000vtiP2t7OiKuXSFJ6Os3CycYK4LfNyLsSkxffiJKUvKY&pvid=e2456346-6c21-490b-8792-abbcafc52e3a&scm=1007.40986.467924.0&skuId=5652727063890&spm=a21bo.jianhua%2Fa.201876.d12.78632a89Xn5WRG&utparam=%7B%22item_ctr%22%3A0.05020460486412048%2C%22x_object_type%22%3A%22item%22%2C%22matchType%22%3A%22nann_base%22%2C%22item_price%22%3A%222.5%22%2C%22item_cvr%22%3A0.043365806341171265%2C%22umpCalled%22%3Atrue%2C%22pc_ctr%22%3A0.009324726648628712%2C%22pc_scene%22%3A%2220001%22%2C%22userId%22%3A3888777108%2C%22ab_info%22%3A%2230986%23467924%230_30986%23528214%2358507_30986%23527806%2358418_30986%23537217%2360408_30986%23521582%2357267_30986%23543870%2358189_30986%23533297%2359487_30986%23528945%2357910_30986%23530923%2359037_30986%23532805%2359017_30986%23528109%2358485_30986%23537488%2360469_30986%23537987%2360586_30986%23538037%2360595%22%2C%22tpp_buckets%22%3A%2230986%23467924%230_30986%23528214%2358507_30986%23527806%2358418_30986%23537217%2360408_30986%23521582%2357267_30986%23543870%2358189_30986%23533297%2359487_30986%23528945%2357910_30986%23530923%2359037_30986%23532805%2359017_30986%23528109%2358485_30986%23537488%2360469_30986%23537987%2360586_30986%23538037%2360595%22%2C%22aplus_abtest%22%3A%2215c0e693256f7b7c9626be50c2718cbe%22%2C%22isLogin%22%3Atrue%2C%22abid%22%3A%22528214_527806_537217_521582_543870_533297_528945_530923_532805_528109_537488_537987_538037%22%2C%22pc_pvid%22%3A%22e2456346-6c21-490b-8792-abbcafc52e3a%22%2C%22isWeekLogin%22%3Afalse%2C%22pc_alg_score%22%3A0.0932632202314%2C%22rn%22%3A11%2C%22item_ecpm%22%3A0%2C%22ump_price%22%3A%222.5%22%2C%22isXClose%22%3Afalse%2C%22x_object_id%22%3A806319949537%7D&xxc=home_recommend'
    # uid = taobao.get_goods_uid_encrypt_uid(goods_url)
    # print(uid)

    res = taobao.upload_media(r"D:\Desktop\1.png")
    print(json.dumps(res, indent=4, ensure_ascii=False))