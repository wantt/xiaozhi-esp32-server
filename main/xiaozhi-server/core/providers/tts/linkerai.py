﻿import os
import uuid
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
import json
import os
from pydub import AudioSegment
import opuslib_next
import numpy as np
import aiohttp

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.provider_name ='linkerai'
        self.access_token = config.get("access_token")
        self.voice = config.get("voice")
        self.response_format = config.get("response_format")
        self.sample_rate = config.get("sample_rate")
        self.instruct_text = config.get("instruct_text")
        self.stream_mode = config.get('stream_mode') # stream or double_stream
        self.host = "tts.linkerai.top"
        self.api_url = 'http://tts.linkerai.top:24003/tts'
        self.double_stream_url = 'http://tts.linkerai.top:24003/double_stream_chat'
        
    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        params = {
            "tts_text": text,
            "spk_id": self.voice,
            "frame_durition": 60,
            "stream": 'true',#str(True).lower(),  
            "target_sr": self.sample_rate,
            "audio_format":"opus",
            "instruct_text":self.instruct_text
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        with open(output_file,'w',encoding='utf-8') as f:
            f.write('http_post\n')
            f.write('%s\n'%(json.dumps(params,ensure_ascii=False)))
            f.write('%s'%(json.dumps(headers,ensure_ascii=False)))
        
    # def yield_data(self,url,params,headers):   
    #     response = requests.get(url=url, headers=headers, params=params, stream=True)
    #     if response.status_code == 200:
    #         for chunk in response.iter_content(chunk_size=None):
    #             if chunk:  
    #                 print(len(chunk))
    #                 yield chunk
    #     else:
    #         print(f"请求失败，状态码: {response.status_code}")
    #         print(f"错误信息: {response.text}")


    async def yield_data(self,url:str='',params:dict={},headers:dict={}):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, headers=headers,timeout=10) as response:
                    if response.status == 200:
                        async for r in response.content.iter_chunks():
                            yield r[0]
            except aiohttp.ClientError as e:
                pass

    def double_stream(self,question:str='',device_id:str=''):
        params = {
            "question": question,
            "device_id": device_id,
            "instruct_text": self.instruct_text,
            "audio_format": 'opus',
            "spk_id":self.voice
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        return self.yield_data(url=self.double_stream_url,params=params,headers=headers)


    def audio_to_opus_data(self, audio_file_path):
        data = b''
        if os.path.exists(audio_file_path):
            with open(audio_file_path,'rb') as f:
                data = f.read(10)
            if data.startswith(b'http_post'):
                duration = 100
                with open(audio_file_path,encoding='utf-8') as f:
                    _ = f.read(10)
                    code = []
                    for line in f.readlines():
                        code.append(json.loads(line.strip()))
                    params = code[0]
                    headers = code[1]
                    return self.yield_data(self.api_url,params=params,headers=headers),duration
                
            else: #兼容非流式音频播放
                file_type = os.path.splitext(audio_file_path)[1]
                if file_type:
                    file_type = file_type.lstrip('.')
                audio = AudioSegment.from_file(audio_file_path, format=file_type, parameters=["-nostdin"])

                audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
                duration = len(audio) / 1000.0
                raw_data = audio.raw_data
                encoder = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_AUDIO)
                frame_duration = 60  # 60ms per frame
                frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame

                opus_datas = []
                for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
                    chunk = raw_data[i:i + frame_size * 2]
                    if len(chunk) < frame_size * 2:
                        chunk += b'\x00' * (frame_size * 2 - len(chunk))
                    np_frame = np.frombuffer(chunk, dtype=np.int16)
                    opus_data = encoder.encode(np_frame.tobytes(), frame_size)
                    opus_datas.append(opus_data)
                return opus_datas, duration
        else:
            return None,None
        
if __name__ == "__main__":
    config = {'access_token':'123',
              'voice':'OUeAo1mhq6IBExi',
              'response_format':'opus',
              'sample_rate':16000
              }
    tts_provider = TTSProvider(config=config,delete_audio_file=True)
    tts_provider.text_to_speak('你好呀，你是谁','asdf.txt')
    data,dur = tts_provider.audio_to_opus_data('asdf.txt')
    for x in data:
        print(len(x))


