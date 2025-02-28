from .config import config_to_trans
from .export_utils import *


class DataSave:
    def __init__(self, cfg, timeslot):
        self.cfg = cfg
        self.OUTPUT_FOLDER = None
        self.LIDAR_PATH = None
        self.KITTI_LABEL_PATH = None
        self.CARLA_LABEL_PATH = None
        self.IMAGE_PATH = None
        self.CALIBRATION_PATH = None
        self.SEMANTIC_PATH = None
        self._generate_path(self.cfg["SAVE_CONFIG"]["ROOT_PATH"], timeslot)
        self.captured_frame_no = self._current_captured_frame_num()
        self.IMAGE = None
        self.LIDAR = None
        self.SEMANTIC = None

    #def _gen_items(self, cfg):

    def _generate_path(self,root_path, timeslot):
        """ 生成数据存储的路径"""
        PHASE = "training"
        self.OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', root_path, PHASE, timeslot)
        folders = ['calib', 'image', 'kitti_label', 'carla_label', 'velodyne', 'semantic']
        #folders = ['semantic']

        for folder in folders:
            directory = os.path.join(self.OUTPUT_FOLDER, folder)
            if not os.path.exists(directory):
                os.makedirs(directory)

        self.LIDAR_PATH = os.path.join(self.OUTPUT_FOLDER, 'velodyne/{0:06}.bin')
        self.KITTI_LABEL_PATH = os.path.join(self.OUTPUT_FOLDER, 'kitti_label/{0:06}.txt')
        self.CARLA_LABEL_PATH = os.path.join(self.OUTPUT_FOLDER, 'carla_label/{0:06}.txt')
        self.IMAGE_PATH = os.path.join(self.OUTPUT_FOLDER, 'image/{0:06}.png')
        self.CALIBRATION_PATH = os.path.join(self.OUTPUT_FOLDER, 'calib/{0:06}.txt')
        self.SEMANTIC_PATH = os.path.join(self.OUTPUT_FOLDER, 'semantic/{0:06}.png')

    def _current_captured_frame_num(self):
        """获取文件夹中存在的数据量"""
        label_path = os.path.join(self.OUTPUT_FOLDER, 'semantic/')
        num_existing_data_files = len(
            [name for name in os.listdir(label_path) if name.endswith('.txt')])
        print("Right now there have been {} files in the dir.".format(num_existing_data_files))
        if num_existing_data_files == 0:
            return 0
        answer = input(
            "There already exists a dataset in {}. Would you like to (O)verwrite or (A)ppend the dataset? (O/A)".format(
                self.OUTPUT_FOLDER))
        if answer.upper() == "O":
            logging.info(
                "Resetting frame number to 0 and overwriting existing")
            return 0
        logging.info("Continuing recording data on frame number {}".format(
            num_existing_data_files))
        return num_existing_data_files

    def save_training_files(self, data):
        # lidar_fname = self.LIDAR_PATH.format(self.captured_frame_no)
        # kitti_label_fname = self.KITTI_LABEL_PATH.format(self.captured_frame_no)
        # carla_label_fname = self.CARLA_LABEL_PATH.format(self.captured_frame_no)
        # img_fname = self.IMAGE_PATH.format(self.captured_frame_no)
        # calib_filename = self.CALIBRATION_PATH.format(self.captured_frame_no)
        semantic_fname = self.SEMANTIC_PATH.format(self.captured_frame_no)
        for agent, dt in data["agents_data"].items():
            # camera_transform= config_to_trans(self.cfg["SENSOR_CONFIG"]["RGB"]["TRANSFORM"])
            # lidar_transform = config_to_trans(self.cfg["SENSOR_CONFIG"]["LIDAR"]["TRANSFORM"])
            # save_ref_files(self.OUTPUT_FOLDER, self.captured_frame_no)
            # save_image_data(img_fname, dt["sensor_data"][0])
            # save_label_data(kitti_label_fname, dt["kitti_datapoints"])
            # save_label_data(carla_label_fname, dt['carla_datapoints'])
            # save_calibration_matrices([camera_transform, lidar_transform], calib_filename, dt["intrinsic"])
            # save_lidar_data(lidar_fname, dt["sensor_data"][2])
            save_semantic_data(semantic_fname, dt['sensor_data'][0])
        self.captured_frame_no += 1