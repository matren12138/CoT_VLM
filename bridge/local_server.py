import os
import re
import json
import subprocess
import multiprocessing
import threading
import argparse
import logging
import time
import traceback
import difflib
import numpy as np
from multiprocessing import get_logger

from Configs import *
from llm_api import *

class LocalServer():
    def __init__(self, args, conns):
        self.args = args
        self.conns = conns
        self.logger = get_logger()
        self.logger.setLevel(logging.INFO)
        self.count = -1
        self.LLM = LLM_Mod(args)
        self.flags = np.zeros(len(conns))
        self.vehicles = ['None'] * len(self.conns)
        for idx, conn in enumerate(self.conns):
            self.vehicles[idx] = conn.recv()
        self.logger.info(f"Total number of threads: {len(self.conns)}")

    def match_response(self, response):
        pattern = re.compile(r"- Vehicle:\s*(?P<vehicle_type>[\w_]+(?:\d+)?(?:_\d+)?)\s*- Speed:\s*(?P<speed>\d+(?:\.\d+)?)\s*km/h")
        matches = pattern.findall(response)
        if not matches:
            self.logger.info(f"{RED}No Matches.{RESET}")
        for match in matches:
            model, speed = match
            matched = difflib.get_close_matches(model, self.vehicles, n=1, cutoff=0.6)
            # self.logger.info(f"Vehicles:{self.vehicles}")
            # self.logger.info(f"Matched:{matched}")
            if matched:
                idx = self.vehicles.index(matched[0])
                self.conns[idx].send(f"speed:{speed}km/h")
                self.logger.info(f"{GREEN}Success matches:{RESET} conn{idx} alter speed to {speed}km/h")
            else:
                pass
            # if model in self.vehicles:
            #     idx = self.vehicles.index(model)
            #     self.conns[idx].send(f"speed:{speed}km/h")

    def run(self):
        while True:
            filedir = None
            filename = None
            main_idx = 0
            try:
                # Check all conns to confirm that all have been received
                break_flag = 0
                while True:
                    if break_flag:
                        break
                    for idx, conn in enumerate(self.conns):
                        if conn.poll() and self.flags[idx] == 0:
                            msg = conn.recv()
                            backup_msg = msg
                            msg = msg.split("|")
                            self.flags[idx] = 1
                            if msg[1] == "IMG":
                                #if args.is_test or args.show_detail:
                                    #logger.info(f"Image created by thread {idx} with flags {flags}")
                                main_idx = idx
                                filedir = msg[-2]
                                filename = msg[-1]
                            #elif args.is_test or args.show_detail:
                                #logger.info(f"[Test Phase] child thread {idx} with flags {flags}")
                        if all(f == 1 for f in self.flags):
                            self.flags = [0] * len(self.flags)
                            self.count += 1
                            break_flag = 1
                            break
                if self.count < MAX_COUNT:
                    if self.args.is_test or self.args.show_detail:
                        self.logger.info(f"Received Message {backup_msg} ({self.count}/{MAX_COUNT})")
                if self.count == MAX_COUNT:
                    if self.args.is_test or self.args.show_detail:
                        self.logger.info(f"Received Message {backup_msg} ({self.count}/{MAX_COUNT})")
                    self.count = 0
                    if not self.args.is_test:
                        while True:
                            if filename is not None:
                                time.sleep(1)
                                res = self.LLM.infer(self.LLM.prompt_DFA(), os.path.join('..', self.args.dir, filedir, filename+'.txt'), os.path.join('..', self.args.dir, filedir, filename+'.jpg'))
                                #print(res)
                                if "No need to reply." in res:
                                    raise ClearExit("Congestion clear, ready to exit")
                                if self.LLM.check_finish():
                                    self.logger.info(f"{RED}Finish a Round{RESET}")
                                    self.match_response(res)
                                    time.sleep(1)
                                    # Clear all congested messages
                                    while True:
                                        cleared = True
                                        for idx, conn in enumerate(self.conns):
                                            if conn.poll() and self.flags[idx] == 0:
                                                msg = conn.recv()
                                                self.flags[idx] = 1
                                                cleared = False
                                            if all(f == 1 for f in self.flags):
                                                self.flags = [0] * len(self.flags)
                                                break
                                        if cleared:
                                            break
                                    break
                            else:
                                self.logger.info(f"Filename is None, skipping.")
                                raise FileNotFoundError()
                    else:
                        time.sleep(10)
                        print("Testing")
            except FileNotFoundError as e:
                continue
            except ClearExit as e:
                self.logger.info("Congestion or accident is clear now.")
                break
            except Exception as e:
                self.logger.error(traceback.format_exc())
                break

def local_server(args, conns):
    logger = get_logger()
    logger.setLevel(logging.INFO)
    Server_ = LocalServer(args, conns)
    logger.info(f"{YELLOW}Initiated Class LocalServer{RESET}")
    Server_.run()

# def local_server(args, conns):
#     logger = get_logger()
#     logger.setLevel(logging.INFO)
#     count = 0
#     llm_trans = LLM_Mod(args)
#     flags = np.zeros(len(conns))
#     logger.info(f"Total number of threads: {len(conns)}")
#     # Repetition on receiving data
#     while True:
#         filedir = None
#         filename = None
#         main_idx = 0
#         try:
#             # Check all conns to confirm that all have been received
#             break_flag = 0
#             while True:
#                 if break_flag:
#                     break
#                 for idx, conn in enumerate(conns):
#                     if conn.poll() and flags[idx] == 0:
#                         msg = conn.recv()
#                         backup_msg = msg
#                         msg = msg.split("|")
#                         flags[idx] = 1
#                         if msg[1] == "IMG":
#                             #if args.is_test or args.show_detail:
#                                 #logger.info(f"Image created by thread {idx} with flags {flags}")
#                             main_idx = idx
#                             filedir = msg[-2]
#                             filename = msg[-1]
#                         #elif args.is_test or args.show_detail:
#                             #logger.info(f"[Test Phase] child thread {idx} with flags {flags}")
#                     if all(f == 1 for f in flags):
#                         flags = [0] * len(flags)
#                         count += 1
#                         break_flag = 1
#                         break
#             if count < MAX_COUNT:
#                 if args.is_test or args.show_detail:
#                     logger.info(f"Received Message {backup_msg} ({count}/{MAX_COUNT})")
#             if count == MAX_COUNT:
#                 if args.is_test or args.show_detail:
#                     logger.info(f"Received Message {backup_msg} ({count}/{MAX_COUNT})")
#                 count = 0
#                 if not args.is_test:
#                     while True:
#                         if filename is not None:
#                             time.sleep(5)
#                             res = llm_trans.infer(llm_trans.prompt_DFA(), os.path.join('..', args.dir, filedir, filename+'.txt'), os.path.join('..', args.dir, filedir, filename+'.jpg'))
#                             #print(res)
#                             if "No need to reply." in res:
#                                 raise ClearExit("Congestion clear, ready to exit")
#                             if llm_trans.check_finish():
#                                 conns[idx].send(res)
#                                 time.sleep(1)
#                                 # Clear all congested messages
#                                 while True:
#                                     cleared = True
#                                     for idx, conn in enumerate(conns):
#                                         if conn.poll() and flags[idx] == 0:
#                                             msg = conn.recv()
#                                             flags[idx] = 1
#                                             cleared = False
#                                         if all(f == 1 for f in flags):
#                                             flags = [0] * len(flags)
#                                             break
#                                     if cleared:
#                                         break
#                                 break
#                         else:
#                             logger.info(f"Filename is None, skipping.")
#                             raise FileNotFoundError()
#                 else:
#                     time.sleep(10)
#                     print("Testing")
#         except FileNotFoundError as e:
#             continue
#         except ClearExit as e:
#             logger.info("Congestion or accident is clear now.")
#             break
#         except Exception as e:
#             logger.error(traceback.format_exc())
#             break

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(
        description='CARLA Data Processor')
    argparser.add_argument(
        '--dir',
        default="testdata",
        type = str,
        help='output directory name')
    argparser.add_argument(
        '--is_test',
        action='store_true',
        help='Whether this is a test func(do we really send stuff to server)')
    argparser.add_argument(
        '-d', '--show_detail',
        action='store_true',
        help='Whether the procedure show the detailed workflow')
    args = argparser.parse_args()
    class template_conn:
        def __init__(self, num):
            self.name = 'template_conn'
            self.num = num
        def send(self, item):
            print(f"Test pipe sending: {item}")
        def recv(self):
            if self.num == 0:
                return "WRITE|IMG"
            else:
                return "WRITE|NONE"
        def poll(self):
            return True
    log_format = '%(levelname)s at %(asctime)s: %(message)s'
    date_format = '%m-%d-%H-%M-%S'
    log_level = logging.INFO
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format
    )
    logger = get_logger()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(stream_handler)
    #local_server(args, template_conn())
    args.is_test = True
    try:
        p = multiprocessing.Process(target=local_server, args=(args, [template_conn(0), template_conn(1)]))
        p.start()
        p.join()
    except KeyboardInterrupt:
        p.terminate()
        p.join()
        logger.info("Exiting local_server test")