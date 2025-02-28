import queue
import sys
import random
import logging
import numpy as np
import os
import glob
try:
    sys.path.append(glob.glob('../../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass
import carla

from .config import config_to_trans
from .data_utils import camera_intrinsic, filter_by_distance

class SensorAttachment:
    def __init__(self, world, datasaver, agent, cfg):
        self.cfg = cfg
        self.world = world
        self.agent = agent
        self.datasaver = datasaver
        self.frame = None
        self.actors = {"non_agents": [], "walkers": [], "agents": [], "sensors": {}}
        self.data = {"sensor_data": {}, "environment_data": None}
        self.attach()
        # try:
        #     self.attach()
        # except Exception as e:
        #     print("Error appending sensors")

    def attach(self):
        # Note: When attaching the sensors, use actor's get_world(), or queue will be empty.
        self.actors["agents"].append(self.agent)
        self.actors["sensors"][self.agent] = []
        for sensor, config in self.cfg["SENSOR_CONFIG"].items():
            if config["BLUEPRINT"] == 'sensor.camera.semantic_segmentation':
                sensor_bp = self.agent.get_world().get_blueprint_library().find(config["BLUEPRINT"])
                for attr, val in config["ATTRIBUTE"].items():
                    sensor_bp.set_attribute(attr, str(val))
                trans_cfg = config["TRANSFORM"]
                transform = carla.Transform(carla.Location(trans_cfg["location"][0],
                                                        trans_cfg["location"][1],
                                                        trans_cfg["location"][2]),
                                            carla.Rotation(trans_cfg["rotation"][0],
                                                        trans_cfg["rotation"][1],
                                                        trans_cfg["rotation"][2]))
                sensor = self.agent.get_world().spawn_actor(sensor_bp, transform, attach_to=self.agent)
                self.actors["sensors"][self.agent].append(sensor)
                print(f"Sensor {config['BLUEPRINT']} {sensor.id} attached to agent {self.agent.id}")
        self.world.tick()
    
    def listen(self):
        for agent, sensors in self.actors["sensors"].items():
            self.data["sensor_data"][agent] = []
            for sensor in sensors:
                q = queue.Queue()
                #q.put = lambda data: (print(f"Data added to queue: {data}, size {q.qsize()}"), q.put(data))[1]
                self.data["sensor_data"][agent].append(q)
                sensor.listen(q.put)
    

    def ontick(self):
        self.frame = self.world.tick()
        print("On tick")
        ret = {"environment_objects": None, "actors": None, "agents_data": {}}
        # Global Actors
        ret["environment_objects"] = self.world.get_environment_objects(carla.CityObjectLabel.Any)
        ret["actors"] = self.world.get_actors()
        # Agent Sensor 
        image_width = self.cfg["SENSOR_CONFIG"]["RGB"]["ATTRIBUTE"]["image_size_x"]
        image_height = self.cfg["SENSOR_CONFIG"]["RGB"]["ATTRIBUTE"]["image_size_y"]
        for agent, dataQue in self.data["sensor_data"].items():
            data = [self._retrieve_data(q) for q in dataQue]
            assert all(x.frame == self.frame for x in data)
            # assert all(x.frame == data[0].frame for x in data)
            ret["agents_data"][agent] = {}
            ret["agents_data"][agent]["sensor_data"] = data
            ret["agents_data"][agent]["intrinsic"] = camera_intrinsic(image_width, image_height)
            ret["agents_data"][agent]["extrinsic"] = np.asmatrix(
                self.actors["sensors"][agent][0].get_transform().get_matrix())
        filter_by_distance(ret, self.cfg["FILTER_CONFIG"]["PRELIMINARY_FILTER_DISTANCE"])
        return ret
    
    def _retrieve_data(self, q):
        while True:
            data = q.get()
            if data.frame == self.frame:
                return data