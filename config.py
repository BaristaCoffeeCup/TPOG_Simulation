'''
由于python的全局变量不是很好用，所以单独设置一个对象来实现全局变量的调用
clocktime           系统时钟，用于模拟场景中的时间流动
distance            WBAN和MEC服务器的距离，由于该场景是移动场景，则该变量可能会删除
finishBuffer        系统中所有处理完成的任务全部送入该列表，用于最后计算系统收益
unavailableBuffer   失效列表，系统中所有由于超时而丢弃的任务全部送入该列表

暂定以上
'''



# 全局变量类，在该类对象中放置全局变量
class Globalmap(object):
    def _init_(self):
        self._global_dict = {'clocktime': 0,
                             'distance': 100,
                             'finishBuffer': [],
                             'unavailableBuffer': [],
                             'temp': [],
                             'timeReal': 0,
                             'Alpha': 0,  # 时延因子
                             'Beta': 0,  # 能耗因子
                             'numOfTask':0,
                             'delayAverage':[[0 for i in range(8)] for j in range(2)]
                             }

    def set_value(self, name, value):
        self._global_dict[name] = value

    def get_value(self, name):
        return self._global_dict[name]
