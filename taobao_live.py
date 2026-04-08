import base64
import json
import asyncio
import threading
import time
from pprint import pprint

from loguru import logger
import websockets
from taobao_apis import TaobaoApis

from utils.taobao_utils import generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt, \
    get_session_cookies_str
from message import Message, make_text, make_image


class taobaoLive:
    def __init__(self, cookies_str):
        self.base_url = 'wss://wss-cntaobao.dingtalk.com/'
        self.cookies_str = cookies_str
        self.cookies = trans_cookies(cookies_str)
        self.myid = self.cookies['unb']
        self.nk = self.cookies['_nk_']
        self.device_id = generate_device_id(self.myid)
        self.taobao = TaobaoApis(self.cookies, self.device_id)
        self.ws = None

    async def list_all_conversations(self, cid):
        headers = {
            "Cookie": get_session_cookies_str(self.taobao.session),
            "Host": "wss-cntaobao.dingtalk.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Origin": "https://www.cntaobao.com",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        async with websockets.connect(self.base_url, extra_headers=headers) as websocket:
            asyncio.create_task(self.init(websocket))
            send_mid = generate_mid()
            msg = {
                "lwp": "/r/MessageManager/listUserMessages",
                "headers": {
                    "mid": send_mid
                },
                "body": [
                    f"{cid}@cntaobao",
                    False,
                    9007199254740991,
                    20,
                    False
                ]
            }
            user_message_models = []
            async for message in websocket:
                print(message)
                try:
                    message = json.loads(message)
                    ack = {
                        "code": 200,
                        "headers": {
                            "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                            "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                        }
                    }
                    if 'app-key' in message["headers"]:
                        ack["headers"]["app-key"] = message["headers"]["app-key"]
                    if 'ua' in message["headers"]:
                        ack["headers"]["ua"] = message["headers"]["ua"]
                    if 'dt' in message["headers"]:
                        ack["headers"]["dt"] = message["headers"]["dt"]
                    await websocket.send(json.dumps(ack))
                except Exception as e:
                    pass
                try:
                    if 'lwp' in message and message['lwp'] == "/s/vulcan":
                        await websocket.send(json.dumps(msg))
                    recv_mid = message["headers"]["mid"] if "mid" in message["headers"] else ''
                    if recv_mid == send_mid:
                        logger.info(f"user history message: {message}")
                        has_more = message["body"]["hasMore"] == 1
                        next_cursor = message["body"]["nextCursor"]
                        for user_message in message["body"]["userMessageModels"]:
                            send_user_name = user_message["message"]["extension"]["sender_nick"]
                            send_user_id = user_message["message"]["sender"]["uid"]
                            send_message = None
                            if user_message["message"]["content"]["contentType"] == 1:
                                send_message = user_message["message"]["content"]
                            elif user_message["message"]["content"]["contentType"] == 101:
                                send_message = user_message["message"]["content"]["custom"]["data"]
                                send_message = base64.b64decode(send_message)
                            user_message_models.insert(0, {
                                "send_user_id": send_user_id,
                                "send_user_name": send_user_name,
                                "message": send_message
                            })
                        if has_more:
                            logger.info(f"has more history messages, next cursor: {next_cursor}")
                            send_mid = generate_mid()
                            msg["headers"]["mid"] = send_mid
                            msg["body"][2] = next_cursor
                            await websocket.send(json.dumps(msg))
                        else:
                            return user_message_models
                except Exception as e:
                    return user_message_models

    async def create_chat(self, ws, encrypt_uid):
        msg = {
            "lwp": "/r/SingleChatConversation/create",
            "headers": {
                "mid": generate_mid()
            },
            "body": [
                {
                    "pairFirst": f"{self.myid}@cntaobao",
                    "bizType": "11001",
                    "ctx": {
                        "createConversationCtx": '{"encryptUid":"' + encrypt_uid + '"}',
                        "selfBizDomain": "taobao"
                    }
                }
            ]
        }
        print(json.dumps(msg, indent=4, ensure_ascii=False))
        await ws.send(json.dumps(msg))

    async def send_msg(self, ws, cid, toid, sender_nick, message: Message):
        msg_type = message["type"]
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {
                "mid": generate_mid()
            },
            "body": [
                {
                    "cid": cid,
                    "uuid": generate_uuid(),
                    "conversationType": 1,
                    "redPointPolicy": 0,
                    "extension": {
                        "senderBizDomain": "taobao",
                        "receiverBizDomain": "taobao",
                        "sender_nick": sender_nick
                    },
                    "content": {
                        "contentType": None,
                    },
                    "ctx": {
                        "senderBizDomain": "taobao",
                        "receiverBizDomain": "taobao"
                    }
                },
                {
                    "actualReceivers": [
                        f"{self.myid}@cntaobao",
                        f"{toid}@cntaobao",
                    ]
                }
            ]
        }
        if msg_type == "text":
            msg["body"][0]["content"]["contentType"] = 1
            msg["body"][0]["content"]["text"] = {
                "extension": {
                    "sender_nick": sender_nick
                },
                "content": message["text"]
            }
        elif msg_type == "image":
            del msg["body"][0]["extension"]["sender_nick"]
            data = {
                "fileId": message["file_id"],
                "size": message["size"],
                "url": message["image_url"],
                "width": message["width"],
                "height": message["height"],
                "isOriginal": 1,
                "suffix": "png"
            }
            msg["body"][0]["content"]["contentType"] = 101
            image_base64 = str(base64.b64encode(json.dumps(data).encode('utf-8')), 'utf-8')
            msg["body"][0]["content"]["custom"] = {}
            msg["body"][0]["content"]["custom"]["type"] = 7
            msg["body"][0]["content"]["custom"]["data"] = image_base64
        elif msg_type == "audio":
            # TODO: handle audio message
            logger.error(f"不支持的消息类型: {msg_type}")
            return
        else:
            logger.error(f"不支持的消息类型: {msg_type}")
            return
        print(json.dumps(msg, indent=4, ensure_ascii=False))
        await ws.send(json.dumps(msg))

    async def init(self, ws):
        data = self.taobao.get_token()
        token = data['data']['result']['accessToken'] if 'data' in data and 'result' in data['data'] and 'accessToken' in data['data']['result'] else ''
        if not token:
            logger.error('获取token失败')
            exit(0)
        msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "3ce2dacdc7c0c43ad7bc7f9bc7d7a1b8",
                "token": token,
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/146.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid()
            }
        }
        await ws.send(json.dumps(msg))
        current_time = int(time.time() * 1000)
        msg = {
            "lwp": "/r/SyncStatus/ackDiff",
            "headers": {"mid": generate_mid()},
            "body": [
                {
                    "pipeline": "sync",
                    "tooLong2Tag": "PNM,1",
                    "channel": "sync",
                    "topic": "sync",
                    "highPts": 0,
                    "pts": current_time * 1000,
                    "seq": 0,
                    "timestamp": current_time
                }
            ]
        }
        await ws.send(json.dumps(msg))
        logger.info('init')


    async def send_msg_once(self, goods_url, send_message: Message):
        headers = {
            "Cookie": get_session_cookies_str(self.taobao.session),
            "Host": "wss-cntaobao.dingtalk.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Origin": "https://www.cntaobao.com",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        async with websockets.connect(self.base_url, extra_headers=headers) as websocket:
            await self.init(websocket)
            user_info = self.taobao.get_goods_uid_encrypt_uid(goods_url)
            await self.create_chat(websocket, user_info["encrypt_uid"])
            async for message in websocket:
                try:
                    logger.info(f"message: {message}")
                    message = json.loads(message)
                    cid = message["body"]["singleChatConversation"]["cid"]
                    sender_nick = f"cntaobao{self.nk}"
                    await self.send_msg(websocket, cid, user_info["uid"], sender_nick, send_message)
                    logger.info('send message')
                    return
                except Exception as e:
                    pass

    async def heart_beat(self, ws):
        while True:
            msg = {
                "lwp": "/!",
                "headers": {
                    "mid": generate_mid()
                 }
            }
            await ws.send(json.dumps(msg))
            await asyncio.sleep(15)

    def user_alive(self):
        while True:
            time.sleep(600)
            # self.taobao.refresh_token()

    async def main(self):
        headers = {
            "Cookie": get_session_cookies_str(self.taobao.session),
            "Host": "wss-cntaobao.dingtalk.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Origin": "https://www.cntaobao.com",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        threading.Thread(target=self.user_alive).start()
        async with websockets.connect(self.base_url, extra_headers=headers) as websocket:
            asyncio.create_task(self.init(websocket))
            asyncio.create_task(self.heart_beat(websocket))
            async for message in websocket:
                # logger.info(f"message: {message}")
                message = json.loads(message)
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                        "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                    }
                }
                if 'app-key' in message["headers"]:
                    ack["headers"]["app-key"] = message["headers"]["app-key"]
                if 'ua' in message["headers"]:
                    ack["headers"]["ua"] = message["headers"]["ua"]
                if 'dt' in message["headers"]:
                    ack["headers"]["dt"] = message["headers"]["dt"]
                await websocket.send(json.dumps(ack))

                await self.handle_message(message, websocket)

    async def handle_message(self, message, websocket):
        try:
            data = message["body"]["syncPushPackage"]["data"][0]["data"]
            data = json.loads(data)
            logger.info(f"无需解密 message: {data}")
        except Exception as e:
            try:
                data = decrypt(data)
                message = json.loads(data)

                send_user_name = message["1"]["10"]["sender_nick"]
                send_user_id = message["1"]["1"]["1"].split('@')[0]
                send_message = message["1"]["6"]["2"]["1"]

                if send_user_name == f"cntaobao{self.nk}":
                    logger.info(f"这是自己发的消息，忽略 message: {message}")
                    return

                logger.info(f"user: {send_user_name}, 发送给我的信息 message: {send_message}")

                cid = message["1"]["2"]

                # 回复文字
                # reply = f'Hello, {send_user_name}! I am a robot. I am not available now. I will reply to you later.'
                reply = f'{send_user_name} 说了: {send_message}'

                await self.send_msg(websocket, cid, send_user_id, f"cntaobao{self.nk}",  make_text(reply))

                # 回复图片
                # res_json = self.taobao.upload_media(r"D:\Desktop\1.png")
                # image_object = res_json["object"]
                # width, height = map(int, image_object["pix"].split('x'))
                # await self.send_msg(websocket, cid, send_user_id, make_image(image_object["url"], width, height))
            except Exception as e:
                print(e)
                pass


if __name__ == '__main__':
    cookies_str = r''
    taobaoLive = taobaoLive(cookies_str)

    # 1 主动发送一次消息
    goods_url = r'https://detail.tmall.com/item.htm?ali_refid=a3_420860_1007%3A9955565344%3AH%3A9955565344_0_24706266476%3A0537034b9833330dbc6d6c6d672c0f6e&ali_trackid=319_0537034b9833330dbc6d6c6d672c0f6e&id=1028024721407&item_type=ad&mi_id=00000ScrWhEvDKasCklVJtX2reM4QjqBlOTsunXkqI0nLng&mm_sceneid=0_0_9955565344_0&spm=tbpc.pc_sem_alimama%2Fa.201876.d94'
    # choice 1
    # asyncio.run(taobaoLive.send_msg_once(goods_url, make_text('Hello, this is an active message!')))
    # choice 2
    # res_json = taobaoLive.taobao.upload_media(r"D:\Desktop\12345.jpg")
    # image_object = res_json["object"]
    # width, height = map(int, image_object["pix"].split('x'))
    # asyncio.run(taobaoLive.send_msg_once(goods_url, make_image(image_object["fileId"], image_object["url"], image_object["size"], width, height)))

    # 2 获取全部聊天记录
    # cid = '3888777108.1-2221755722770.1#11001'
    # all_messages = asyncio.run(taobaoLive.list_all_conversations(cid))
    # for message in all_messages:
    #     print(message)

    # 3 常驻进程 用于接收消息和自动回复
    asyncio.run(taobaoLive.main())
