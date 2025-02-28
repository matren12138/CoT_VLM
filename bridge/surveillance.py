import carla
import os
import cv2
import argparse
import numpy as np
import time
import threading
import socket
from functools import partial
from datetime import datetime
from Configs import *

def init_carla(ip, port):
    client = carla.Client(ip, port)
    client.set_timeout(10.0)
    world = client.get_world()
    return world

def set_camera(world):
    global SIZE_X, SIZE_Y, LX, LY, LZ, PITCH_CAM
    blueprint_library = world.get_blueprint_library()
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', SIZE_X)
    camera_bp.set_attribute('image_size_y', SIZE_Y)
    camera_bp.set_attribute('fov', '110')
    camera_transform = carla.Transform(carla.Location(x = -45, y = 20, z = 25), carla.Rotation(pitch = -90))
    camera = world.spawn_actor(camera_bp, camera_transform)
    return camera

def process_image(args, dir_name, conn, image):
    os.makedirs(os.path.join(args.dir, dir_name), exist_ok = True)
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = array.reshape((image.height, image.width, 4))
    frame = array[:, :, :3]
    #cv2.imshow("CARLA Camera", frame)
    #threading.Thread(target=show_frame, args=(frame,)).start()
    label = datetime.now().strftime("%H-%M-%S")
    cv2.imwrite(os.path.join('..',args.dir, dir_name, "{}.jpg".format(label)), frame)
    conn.send(f"{dir_name}|{label}.jpg")
    if conn.poll():
        msg = conn.recv()
        if msg == "Done":
            print(f"Success saving {label}.jpg to {dir_name}")
        elif msg == "Bad Request":
            print(f"Abnormal Reply")
            exit(0)
        elif msg.split('|')[0] == "Process":
            print(f"Success sending {msg[1]}/{msg[2]}")
        else:
            print(f"Error occurs but success saving {label}.jpg to {dir_name}")
    time.sleep(1)
    cv2.waitKey(100)

def surveillance_runner(args, conn):
    world = init_carla(IP, PORT)
    camera = set_camera(world)
    dir_name = args.dir
    camera.listen(partial(process_image, args, dir_name, conn))
    try:
        while True:
            time.sleep(0.5)
    except Exception:
        if KeyboardInterrupt:
            print("Bye")
        else:
            print(f"Ending: {Exception}")
    finally:
        conn.send("conn send test")
        camera.stop()
        camera.destroy()

if __name__ == "__main__":
    dir_name = datetime.now().strftime("%Y-%m-%d-%H-%M")
    class template_args:
        def __init__(self):
            self.dir = "test"
    class template_conn:
        def __init__(self):
            self.name = 'template_conn'
        def send(self, item):
            print(item)
        def recv(self):
            return "Done"
        def poll(self):
            return True

    surveillance_runner(template_args(), template_conn())
