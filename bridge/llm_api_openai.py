"""But if the following instructions have implied that there is no ned for LLM to coordinate, only output clear."""

import http.client
import json
import base64
import os
import traceback
import logging
import socket
import time
import openai
from io import BytesIO
from PIL import Image
from multiprocessing import get_logger
from Configs import *

#baseprompt_0 = """There is a traffic accident in this picture.
#Assume you are a traffic police officer observing this scene, only reply essential information.
#Your task is to provide detailed instructions for clearing the traffic congestion. For each vehicle in the image, please provide the following:
#- Vehicle type
#- The direction in which the vehicle should move
#- The distance for which the vehicle should move (in meters)
#- The speed for which the vehicle should move (in kilometers per hour)
#Please pay attention to the overall traffic flow and ensure that your instructions will help clear the blockage efficiently.
#Below is the information about the vehicles in the picture:"""

baseprompts = [

# 0     Specify the scenario of the image
"""Please read the image and specify which situation the image is in what situation: accident or congestion. 
Congestion means there is a traffic jam that not all vehicles can run at their appropriate speed, accident means there is a collision between vehicles occurred.
And only reply one word and make sure there is indeed a collision in the image if the reply is accident.""",

# 1     Congestion: Reasoning
"""There is a congestion in this image.
Assume you are a traffic police officer observing this scene, only reply essential information.
First, please reply the main reason of this congestion in this format:
Reason: Inappropriate Speed
Step by step, first figure out their facing direction, given that you have known the main reason, then analyze what each vehicle should do, your task is to provide detailed instructions for clearing the traffic congestion. For each vehicle in the image, please provide the following step by step:
- Vehicle Type and Color
- The direction in which the vehicle should move
- The distance for which the vehicle should move (in meters)
- The speed for which the vehicle should move (in kilometers per hour)
Please pay attention to the overall traffic flow and ensure that your instructions will help clear the blockage efficiently.
Below is the information about the vehicle in the center of the image:""",

# 2     Congestion: Summary
"""Please summarize your instructions into a few words as follows: 
- Vehicle: vehicle type and color - Direction:Left, Right, Straight - Distance:M - Speed:KM/H
i.e. carolla direction:staright distance:100m speed:18km/h
Below is the instructions:""",

# 3     Accident: Reasoning
"""There is a traffic accident in the image.
Assume you are a traffic police officer observing this scene, only reply essential information. From the context, please provide the following step by step:
- The accident scene
- The causes of the accident
For each vehicle, please reply:
- Vehicle Type
- Cause of the Liability in the accident
- The conclusion of the apportionment of the liability in the accident: Major, Minor, None
- Instruction that could clear the lane
Below is the information about the vehicle in the center of the image:""",

# 4     Accident: Summary
"""Please summarize your instructions into a few words as follows: 
- Vehicle: vehicle type - The cause of liability in the accident - The conclusion of the apportionment of the liability in the accident
i.e. carolla Cause of Liability:unseasonable lane change Apportionment: Major
Below is the instructions:"""

]

# baseprompt_0 = """There is a congestion due to inappropriate speed in this picture.
# Assume you are a traffic police officer observing this scene, only reply essential information.
# Your task is to provide detailed instructions for clearing the traffic congestion. For each vehicle in the image, please provide the following:
# - Vehicle type
# - The direction in which the vehicle should move
# - The distance for which the vehicle should move (in meters)
# - The speed for which the vehicle should move (in kilometers per hour)
# Please pay attention to the overall traffic flow and ensure that your instructions will help clear the blockage efficiently.
# Below is the information about the vehicle in the center of the image:"""

# baseprompt_1 = """Please summarize your instructions into a few words as follows: 
# - Vehicle: vehicle type
# - Direction:Left, Right, Straight
# - Distance:M
# - Speed:KM/H
# i.e. carolla direction:staright distance:100m speed:18km/h
# Below is the instructions:"""

# In case the image is incomplete
def base64_check(b64_string):
    if b64_string == None:
        return False
    try:
        decoded_data = base64.b64decode(b64_string, validate=True)
        return True
    except base64.binascii.Error:
        return False

class ClearExit(Exception):
    pass

class LLM_Mod():
    def __init__(self, args):
        self.conn = http.client.HTTPSConnection(CONNURL, timeout=CONN_TIMEOUT)
        self.history = []
        self.scenario = 0
        self.flag = False
        self.branch = None
        self.logger = get_logger()
        self.logger.setLevel(logging.INFO)
        self.args = args
        self.terminal_width = os.get_terminal_size().columns
        self.init_api()

    def init_api(self):
        if not self.args.is_test:
            payload = json.dumps({
            "model": GPT_VERSION,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                        "type": "text",
                        "text": "Hello, this is for initiate the connection, no need to reply anything"
                        }
                    ]
                }
            ],
            "max_tokens": 100
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': GPG_KEY
            }
            self.conn.request("POST", "/v1/chat/completions", payload, headers)
            res = self.conn.getresponse()
            data = res.read()
            output = json.loads(data)
            response = output["choices"][0]["message"]["content"]
            self.logger.info(f"LLM API Initiated: {response}")

    def check_finish(self):
        return self.flag

    def get_scenario(self):
        return int(self.scenario)
    
    def prompt_DFA(self):
        print(f"***State Shift: From {self.scenario} to ", end='')
        if self.scenario == 0:
            prompt = baseprompts[0]
            self.scenario = 1
            self.flag = False
            print("1***")
        elif self.scenario == 1:
            try:
                if self.branch.lower() == 'congestion':
                    prompt = baseprompts[1]
                    self.scenario = 2
                    self.flag = False
                    print("2***")
                elif self.branch.lower() == 'accident':
                    prompt = baseprompts[3]
                    self.scenario = 4
                    self.flag = False
                    print("4***")
                else:
                    raise Exception("No valid branch instruction")
            except Exception as e:
                self.logger.info(f"Not getting right prompt: {e}")
                prompt = None
                self.scenario = 0
                prompt = baseprompts[0]
                print("0***")
        elif self.scenario == 2:
            prompt = baseprompts[2] + (self.history[-1][-1] if self.history else "")
            self.scenario = 3
            self.flag = True
            print("3***")
        elif self.scenario == 3:
            prompt = baseprompts[1]
            self.scenario = 2
            self.flag = False
            print("2***")
        elif self.scenario == 4:
            prompt = baseprompts[4] + (self.history[-1][-1] if self.history else "")
            self.scenario = 5
            self.flag = True
            print("5***")
        elif self.scenario == 5:
            prompt = baseprompts[3]
            self.scenario = 4
            self.flag = False
            print("4***")
        return prompt
            
    # def prompt_DFA(self):
    #     print(f"***Shift the state from {self.scenario} to ", end='')
    #     if self.scenario == 0:
    #         self.scenario = 1
    #         self.flag = False
    #         print("1")
    #         return baseprompt_0
    #     elif self.scenario == 1:
    #         self.scenario = 2
    #         self.flag = False
    #         print("2")
    #         return baseprompt_1 + (self.history[-1][-1] if self.history else "")
    #     elif self.scenario == 2:
    #         if self.history and "the traffic is cleared now." in self.history[-1][-1].lower():
    #             print("3: Situation Clear")
    #             self.scenario = 3
    #             self.flag = True
    #             raise ClearExit("CongestionClear")
    #         else:
    #             print("3")
    #             self.scenario = 3
    #             self.flag = True
    #             return baseprompt_0
    #     elif self.scenario == 3:
    #         self.scenario = 2
    #         self.flag = False
    #         print("2")
    #         return baseprompt_1 + (self.history[-1][-1] if self.history else "")

    def infer(self, prompt, text_path, image_path):
        if os.path.exists(text_path):
            flag = 0
            with open(text_path, 'r') as f:
                text = f.read()
        else:
            flag = 1
            text = ""
        if os.path.exists(image_path):
            root_path, name = os.path.split(image_path)
            time.sleep(2)
            dir_path, file_name = os.path.split(image_path)
            img = Image.open(image_path)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=30)
            img.save(os.path.join(dir_path, file_name.split('.')[0] + '.jpeg'), format='JPEG', quality=30)
            time.sleep(2)
            base64_image = None
            cnt = 0
            while not base64_check(base64_image):
                base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
                cnt += 1
                if cnt >= 5:
                    base64_image = None
                    self.logger.info(f"{RED}Error Loading Image: Cannot transform into base64{RESET}")
                    break
            #with open(image_path, "rb") as image_file:
            #    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        else:
            base64_image = None
            self.logger.info(f"{RED}Error Loading Image: Invalid Path{RESET}")
        if self.scenario % 2:
            final_prompt = prompt
        else:
            final_prompt = prompt# + text
        print("Prompt".center(self.terminal_width, '-'))
        print(final_prompt)
        if not self.scenario % 2 or self.scenario == 1:
            print("Base64_image Length", len(base64_image))
            payload = json.dumps({
            "model": GPT_VERSION,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                        "type": "text",
                        "text": final_prompt
                        },
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64,"+base64_image}
                        }
                    ]
                }
            ],
            "max_tokens": 10000
            })
        else:
            payload = json.dumps({
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                        "type": "text",
                        "text": final_prompt
                        }
                    ]
                }
            ],
            "max_tokens": 10000
            })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': GPG_KEY
        }
        try:
            if self.args.is_test:
                return "[TEST] This works!"
            else:
                count = 0
                while True:
                    try:
                        self.conn.request("POST", "/v1/chat/completions", payload, headers)
                        res = self.conn.getresponse()
                        break
                    except socket.timeout:
                        self.logger.info(f"{YELLOW}Connection Stall: Reconnecting...{RESET}")
                        self.conn = http.client.HTTPSConnection(CONNURL, timeout=CONN_TIMEOUT)
                        count += 1
                        if count >= 3:
                            self.logger.info(f"{RED}Cannot Build Connection, Exiting.{RESET}")
                            count = 0
                            res = None
                            return "Connection Failed, No Valid Response"
                if res:
                    data = res.read()
                    output = json.loads(data)
                    #if self.args.show_detail:
                    #    print("Raw Response".center(self.terminal_width, '-'))
                    #    print(output)
                    try:
                        response = output["choices"][0]["message"]["content"]
                    except:
                        self.logger.error(f"Bad Response: {output}")
                        response = None
                    if self.scenario == 1:
                        self.branch = 'accident' if 'accident' in response.lower() else 'congestion'
                    else:
                        self.branch = None
                    self.history.append(('prompt', prompt + text, image_path))
                    self.history.append(('reply', response))
                    print("Reply".center(self.terminal_width, '-'))
                    print(response)
                    with open(os.path.join(root_path,name.split('.')[0] + '_LLM.txt'), 'a') as f:
                        f.write("---Prompt---\n")
                        f.write(final_prompt + "\n")
                        f.write("---Response---\n")
                        f.write(response + "\n")
                        f.close()
                    return response
                else:
                    print("Reply".center(self.terminal_width, '-'))
                    print("Abnormal Connection: No response.")
                    return "Abnormal Connection: No response."
        except Exception as e:
            self.logger.info(F"[Details attached] Error occurs: {e}")
            self.logger.error(traceback.format_exc())
