# npy_editor/utils.py
import numpy as np
import os
import json

class DataProxy:
    """
    V23 DataProxy 的 Web 移植版
    负责处理 Numpy 数据的加载、结构识别和读写
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.raw_data = None
        self.structure_type = "unknown"
        self.length = 0
        self.available_keys = []
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError("NPY file not found")
        # 允许 pickle 以支持复杂结构
        self.raw_data = np.load(self.file_path, allow_pickle=True)
        self._analyze()

    def _analyze(self):
        """完全复刻 V23 的结构分析逻辑"""
        data = self.raw_data
        
        # 0维数组处理
        if isinstance(data, np.ndarray) and data.ndim == 0:
            data = data.item()
            self.raw_data = data

        # 降维处理
        if isinstance(data, (np.ndarray, list)) and hasattr(data, 'shape'):
            if len(data.shape) == 2:
                if data.shape[0] == 1:
                    data = data[0]
                    self.raw_data = data
                elif data.shape[1] == 1:
                    data = data.flatten()
                    self.raw_data = data

        # 单元素列表处理
        if isinstance(data, list) and len(data) == 1:
            if isinstance(data[0], (list, np.ndarray, dict)):
                data = data[0]
                self.raw_data = data

        # 结构识别
        if isinstance(data, dict):
            self.structure_type = "Dict of Lists"
            keys = list(data.keys())
            self.available_keys = sorted(keys)
            max_len = 0
            for k in keys:
                val = data[k]
                if hasattr(val, '__len__'):
                    max_len = max(max_len, len(val))
            self.length = max_len
            
        elif isinstance(data, (list, tuple, np.ndarray)):
            self.length = len(data)
            if self.length > 0:
                first = data[0]
                if isinstance(first, dict):
                    self.structure_type = "List of Dicts"
                    self.available_keys = sorted(list(first.keys()))
                elif isinstance(first, (list, tuple, np.ndarray)):
                    self.structure_type = "List of Lists"
                    self.available_keys = [f"Col {i}" for i in range(len(first))]
                else:
                    self.structure_type = "Simple Array"
                    self.available_keys = ["Value"]
            else:
                self.structure_type = "Empty List"
        else:
            self.structure_type = "Unknown"

    def get_column_data(self, key_name=None):
        """提取某一列数据，返回 list 以供 JSON 序列化"""
        try:
            arr = np.array([])
            if self.structure_type == "Simple Array":
                arr = np.array(self.raw_data)
            elif self.structure_type == "Dict of Lists":
                if key_name in self.raw_data:
                    arr = np.array(self.raw_data[key_name])
                else:
                    arr = np.zeros(self.length)
            elif self.structure_type == "List of Dicts":
                arr = np.array([float(item.get(key_name, np.nan)) for item in self.raw_data])
            elif self.structure_type == "List of Lists":
                col_idx = int(key_name.split(' ')[1])
                arr = np.array([item[col_idx] for item in self.raw_data])
            
            # Web端必须返回 list，不能返回 numpy array
            return np.nan_to_num(arr).tolist()
        except Exception as e:
            print(f"Error getting column {key_name}: {e}")
            return []

    def set_value(self, index, key_name, new_value):
        """写入数据"""
        try:
            index = int(index)
            new_value = float(new_value)
            
            if self.structure_type == "Simple Array":
                self.raw_data[index] = new_value
            elif self.structure_type == "Dict of Lists":
                self.raw_data[key_name][index] = new_value
            elif self.structure_type == "List of Dicts":
                self.raw_data[index][key_name] = new_value
            elif self.structure_type == "List of Lists":
                col_idx = int(key_name.split(' ')[1])
                self.raw_data[index][col_idx] = new_value
            return True
        except Exception as e:
            print(f"Error setting value: {e}")
            return False

    def save(self):
        """保存回文件"""
        np.save(self.file_path, self.raw_data)