# -*- coding: utf-8 -*-
import os
import sys
import time
import yaml

# 参数解析模块
import argparse
# 插件动态加载模块
from pluginbase import PluginBase
# 超tm好用的日志模块，_防止其他模块引用时引用成未设置的日志对象
from loguru import logger as _logger


class Config:
    """
    配置文件类

    默认解析`config.yaml`文件，逐个逐层读取参数，并赋值给:class:`Config`
    :param yaml_path 需解析yaml格式配置文件的路径
    """
    # 程序基础路基
    __BASE_PATH = os.path.dirname(__file__)

    # 配置文件路径
    __CONFIG_FILE = 'config.yaml'

    def __init__(self, yaml_path=None):
        # 使用loguru的日志对象为配置的日志对象
        self.logger = _logger
        # 字段解析深度，未配置字段解析到最深一层
        self.fields_depth = {'plugins': 1}
        # 当前配置包含插件列表
        self.plugins = None
        self.__load_config(yaml_path)
        self.__load_args()
        self.__logger_config()
        self.__pre_load_plugins()

    def __logger_config(self):
        """
        使用配置文件，配置日志对象
        :return: 配置文件对象
        """
        self.log_path and self.logger.add(self.log_path)
        return self

    def __load_config(self, yaml_path=None):
        """
        配置文件加载参数
        :param yaml_path: 配置文件路径，如果为空则使用默认的配置文件路径
        :return: 配置文件对象
        """
        yaml_path = yaml_path or self.__CONFIG_FILE
        # 如果yaml为多层目录，认为不需要拼接基本路径
        if os.sep not in yaml_path:
            yaml_path = os.path.join(self.__BASE_PATH, yaml_path)

        # 处理中文乱码问题
        with open(yaml_path, 'r', encoding='utf-8') as f:
            self.__set_property(yaml.safe_load(f.read()))
        return self

    def __set_property(self, properties, prefix='', depth=None):
        """
        设置配置文件类属性
        :param properties: 需要遍历的属性字典
        :param prefix: 需添加的前缀
        :param depth: 属性设置的深度，如果深度大于1，并且属性类型为字典则继续迭代设置属性
        :return: 配置文件对象
        """
        properties = properties or {}
        for name, value in properties.items():
            full_name = prefix + name if prefix == '' else prefix + '_' + name
            if depth is None:
                depth = self.fields_depth.get(full_name) if full_name in self.fields_depth else sys.maxsize
            # 如果属性为字典并且属性深度大于1
            if isinstance(value, dict) and depth > 1:
                self.__set_property(value, full_name, depth - 1)
            else:
                setattr(self, full_name, value)

        return self

    def __load_args(self):
        """
        设置程序运行参数
        :return: 配置文件对象
        """
        p = argparse.ArgumentParser()
        p.add_argument('--start-time', help='文件记录查询开始时间', type=str)
        p.add_argument('--end-time', help='文件记录查询结束时间', type=str)
        p.add_argument('--log-path', help='日志记录路径', type=str)
        p.add_argument('--upload', help='上传文件路径(如果设置,程序执行上传s3逻辑)', type=str)
        args = p.parse_args()
        self.start_time = self.get_timestamp(args.start_time)
        self.end_time = self.get_timestamp(args.end_time)
        self.log_path = args.log_path
        self.upload_path = args.upload
        return self

    @staticmethod
    def get_timestamp(time_str, mill=True):
        """
        时间字符串转时间戳
        :param time_str: 时间字符串
        :param mill: 是否返回毫秒时间戳
        :return: 时间戳
        """
        tp = 0
        if time_str:
            if len(time_str) == 10:
                tp = time.mktime(time.strptime(time_str, '%Y-%m-%d'))
            elif len(time_str) == 19:
                tp = time.mktime(time.strptime(time_str, '%Y-%m-%d %H:%M:%S'))
            else:
                raise AttributeError("请输入时间格式参数")
        return int(tp) * 1000 if mill else int(tp)

    def __pre_load_plugins(self):
        """
        设置插件目录，初始化pluginSource对象
        :return: 配置文件对象
        """
        plugin_path = self.__BASE_PATH + os.sep + 'plugins'
        plugin_base = PluginBase(package=plugin_path)
        plugin_sources = plugin_base.make_plugin_source(searchpath=[plugin_path])
        self.__load_plugins(self.plugins, plugin_sources)
        return self

    @staticmethod
    def __load_plugins(plugins, plugin_sources):
        """
        校验插件是否存在，并加载插件
        :param plugins 需加载插件列表
        :param plugin_sources 插件加载对象
        """
        all_plugins = plugin_sources.list_plugins()
        if plugins:
            for parse_type, plus in plugins.items():
                if isinstance(plus, list):
                    plugin_objs = []
                    for plugin in plus:
                        if plugin not in all_plugins:
                            raise ValueError('plugin: {} 未找到执行文件'.format(plugin))
                        plugin_objs.append(plugin_sources.load_plugin(plugin))
                    plugins[parse_type] = plugin_objs
                if isinstance(plus, str):
                    if plus not in all_plugins:
                        raise ValueError('plugin: {} 未找到执行文件'.format(plus))
                    plugin_obj = plugin_sources.load_plugin(plus)
                    plugins[parse_type] = plugin_obj
                if isinstance(plus, dict):
                    Config.__load_plugins(plus, plugin_sources)


class StrTimeParseAction(argparse.Action):
    """
    字符串解析为时间时间戳类
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        nargs or raise ValueError('nargs not allowed')
        super().__init__(option_strings, dest, nargs=None, **kwargs)


if __name__ == '__main__':
    conf = Config()
    for m in [i for i in dir(conf) if not i.startswith('__')]:
        field = getattr(conf, m)
        if callable(field):
            continue
        print(m, field)
