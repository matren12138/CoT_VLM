# Public imports
import os
import argparse
import socket
import subprocess
import multiprocessing
import logging
import time
import traceback
from datetime import datetime
from multiprocessing import Manager, Lock, get_logger
# Self-set modules
import local_server
import autorun_configurable
import control_vehicle
import surveillance
from Configs import *

"""
This script is for providing all scripts by simple use. Try to run the script like this:

python carla_runner.py autorun -c 1 -l -d
"""


terminal_width = os.get_terminal_size().columns

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description='CARLA Data Processor')
    argparser.add_argument(
        '--log_dir',
        default=None,
        type = str,
        help='data dir')
    argparser.add_argument(
        'command', 
        type=str, 
        choices = ['surveillance', 'autorun', 'control'],
        help="Type of commands")
    argparser.add_argument(
        '-c', '--count', 
        type=int, 
        default=1,
        help="Count of autorun/controlled vehicles")
    argparser.add_argument(
        '--count_auto', 
        type=int, 
        default=0,
        help="Count of autorun vehicles")
    argparser.add_argument(
        '--host',
        metavar='H',
        default='localhost',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '--username',
        default="sincloud",
        type = str,
        help='server username')
    argparser.add_argument(
        '--server_path',
        default="/mnt/nodestor/LLM_Carla/datasets/",
        type = str,
        help='server scp path')
    argparser.add_argument(
        '--dir',
        default="testdata",
        type = str,
        help='output directory name')
    argparser.add_argument(
        '--filter',
        metavar='PATTERN',
        default='vehicle.*',
        help='Actor filter (default: "vehicle.*")')
    argparser.add_argument(
        '--generation',
        metavar='G',
        default='2',
        help='restrict to certain actor generation (values: "1","2","All" - default: "2")')
    argparser.add_argument(
        '-l', '--loop',
        action='store_true',
        dest='loop',
        help='Sets a new random destination upon reaching the previous one (default: False)')
    argparser.add_argument(
        "-a", "--agent", type=str,
        choices=["Behavior", "Basic", "Constant"],
        help="select which agent to run",
        default="Basic")
    argparser.add_argument(
        '-b', '--behavior', type=str,
        choices=["cautious", "normal", "aggressive"],
        help='Choose one of the possible agent behaviors (default: normal) ',
        default='normal')
    argparser.add_argument(
        '-s', '--seed',
        help='Set seed for repeating executions (default: None)',
        default=None,
        type=int)
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        help='Window resolution (default: 1280x720)')
    argparser.add_argument(
        '--sync',
        action='store_true',
        help='Synchronous mode execution')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='Print debug information')
    argparser.add_argument(
        '--dir_bak',
        default="test",
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
    argparser.add_argument(
        '--is_block',
        action='store_true',
        help='Whether we should update some info')
    argparser.add_argument(
        '--rolename',
        metavar='NAME',
        default='hero',
        help='actor role name (default: "hero")')
    argparser.add_argument(
        '--gamma',
        default=2.2,
        type=float,
        help='Gamma correction of the camera (default: 2.2)')
    argparser.add_argument(
        '--autopilot',
        action='store_true',
        help='enable autopilot')
    argparser.add_argument(
        '--fix_place',
        action='store_true',
        help='Whether the initial place is fixed')
    argparser.add_argument(
        '-sp', '--specified_place',
        default=0,
        type = int,
        help='Specified place.')
    argparser.add_argument(
        '-ns', '--normal_speed',
        action='store_true',
        help='Whether this is a test func(do we really send stuff to server)')
    argparser.add_argument(
        '-ks', '--kitti_sensor',
        action='store_true',
        help='Attachment of sensors for kitti format dataset')
    args = argparser.parse_args()
    args.width, args.height = [int(x) for x in args.res.split('x')]
    dir_name = datetime.now().strftime("%Y-%m-%d-%H-%M")
    log_format = '%(levelname)s at %(asctime)s: %(message)s'
    date_format = '%m-%d-%H-%M-%S'
    log_level = logging.INFO
    logging.basicConfig(format=log_format, datefmt=date_format, level=log_level)
    logger = get_logger()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(stream_handler)
    logger.info('listening to server %s:%s', args.host, args.port)
    # Set up the server to listen on localhost and port 12345
    #os.makedirs(dir_name, exist_ok=True)
    args.dir_bak = dir_name
    manager = Manager()
    try:
        if args.command == 'surveillance':
            p_conn, c_conn = multiprocessing.Pipe()
            lserver = multiprocessing.Process(target = local_server.local_server, args = (args, p_conn,))
            camera_handler = multiprocessing.Process(target = surveillance.surveillance_runner, args = (args, c_conn,))
            lserver.start()
            camera_handler.start()
            lserver.join()
            camera_handler.join()
        elif args.command == 'autorun':
            p_conn, c_conn = zip(*[multiprocessing.Pipe() for _ in range(args.count)])
            p_conn = list(p_conn)
            c_conn = list(c_conn)
            lserver = multiprocessing.Process(target = local_server.local_server, args = (args, p_conn,))
            lserver.start()
            auto_vehicles = []
            for i in range(args.count):
                auto_vehicles.append(multiprocessing.Process(target = autorun_configurable.game_loop, args = (args, c_conn[i], i)))
            for subprocess_ in auto_vehicles:
                subprocess_.start()
                time.sleep(1)
            lserver.join()
            for subprocess_ in auto_vehicles:
                subprocess_.join()
        elif args.command == 'control':
            p_conn, c_conn = zip(*[multiprocessing.Pipe() for _ in range(args.count + args.count_auto)])
            p_conn = list(p_conn)
            c_conn = list(c_conn)
            lserver = multiprocessing.Process(target = local_server.local_server, args = (args, p_conn,))
            lserver.start()
            control_vehicles = []
            auto_vehicles = []
            for i in range(args.count):
                control_vehicles.append(multiprocessing.Process(target = control_vehicle.game_loop, args = (args, c_conn[i], i)))
            for subprocess_ in control_vehicles:
                subprocess_.start()
                time.sleep(5)
            for i in range(args.count, args.count + args.count_auto):
                auto_vehicles.append(multiprocessing.Process(target = autorun_configurable.game_loop, args = (args, c_conn[i], i)))
            for subprocess_ in auto_vehicles:
                subprocess_.start()
                time.sleep(5)
            lserver.join()
            for subprocess_ in control_vehicles:
                subprocess_.join()
    except KeyboardInterrupt:
        if args.command == 'surveillance':
            lserver.terminate()
            lserver.join()
            camera_handler.terminate()
            camera_handler.join()
        elif args.command == 'autorun':
            lserver.terminate()
            lserver.join()
            for subprocess_ in auto_vehicles:
                subprocess_.terminate()
                subprocess_.join()
        elif args.command == 'control':
            lserver.terminate()
            lserver.join()
            for subprocess_ in control_vehicles:
                subprocess_.terminate()
                subprocess_.join()
            for subprocess_ in auto_vehicles:
                subprocess_.terminate()
                subprocess_.join()
    finally:
        logging.info('Exiting carla_runner')