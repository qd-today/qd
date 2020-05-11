#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import requests
import json
import os
import codecs
import io

class send2phone:
    def __init__(self, *args, **kwargs):
        if ("barkurl" in kwargs):
            self.barklink = kwargs["barkurl" ]
        else: 
            self.barklink = ""
            
        if ("skey" in kwargs):
            self.skey = kwargs["skey" ]
        else: 
            self.skey = ""

            
    def send2bark(self, title, content):
        if (self.barklink):
            try:
                if (self.barklink[-1:] == u"/"):
                    self.barklink = self.barklink[0: len(self.barklink)-1]
                msg = u"{0}/推送标题/{1}/'{2}'".format(self.barklink, title, content)
                res = requests.get(msg,verify=False)
            except Exception as e:
                print('Reason:', e)
        return
        
    def send2s(self, title, content):
        if (self.skey != ""):
            try:
                self.skey = self.skey.replace(".send", "")
                link = u"https://sc.ftqq.com/{0}.send".format(self.skey)
                d = {'text': title, 'desp': content}
                res = requests.post(link, data=d , verify=False)
            except Exception as e:
                print('Reason:', e)

        return    
        
    # def send2BarkAndWJ(self, title, content):
    #     if (self.barklink) and (self.wj[u"链接"]):
    #         try:
    #             msg = u"{0}/推送标题/{1}/{2}?url=https://wj.qq.com".format(self.barklink, title, content)
    #             res = requests.get(msg,verify=False)
    #             s = "{\"id\":\"123456\",\"survey_type\":0,\"jsonLoadTime\":3,\"time\":1587372438,\"ua\":\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36\",\"referrer\":\"https://wj.qq.com/mine.html\",\"openid\":\"\",\"pages\":[{\"id\":\"1\",\"questions\":[{\"id\":\"qID\",\"type\":\"text_multiple\",\"blanks\":[{\"id\":\"fID\",\"value\":\"dasdas\"}]}]}],\"latitude\":\"\",\"longitude\":\"\",\"is_update\":false}"
    #             s = s.replace("123456", self.wj["ID"])
    #             s = s.replace("qID", self.wj[u"问题ID"])
    #             s = s.replace("fID", self.wj[u"填空ID"])
    #             t = "{0}  {1}".format(title, content).decode("utf-8")
    #             s = s.replace("dasdas", t)
    #             self.base_headers["Referer"] = self.wj[u"链接"]          
    #             rjson={
    #                 "survey_id": self.wj[u"ID"],
    #                 "answer_survey":s
    #             }
                
    #             res = requests.post("https://wj.qq.com/sur/collect_answer", 
    #                           headers=self.base_headers, 
    #                           json=rjson, 
    #                           verify=False)
    #         except Exception as e:
    #             print('Reason:', e) 

    #     return
    
if __name__ == "__main__":
    pushno = send2phone()
    pushno.send2bark("签到任务 {0} 失败".format('test'), "任务已禁用")
    pushno.send2s("签到任务 {0} 失败".format('test'), "任务已禁用")
