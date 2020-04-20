'''
WBAN单个任务对象，用于在固定时间片内生成特定的任务，任务属性如下：
数据量  优先级  价值    
本地计算频率        本地计算时延    本地计算能耗
云计算频率          云计算时延      云计算能耗      发送带宽        发送时延        发送能耗
卸载决策（0或1）    支付报酬       所属WBAN编号    选择服务器编号   排队时延       进入缓冲区时间点     离开缓冲区时间点
所属时间片         

'''

from tabulate import tabulate

import math


tabulate.PRESERVE_WHITESPACE = True

class Task(object):
    # 任务类，用于生成WBAN在某一时隙开始时产生的八个任务
    def __init__(self, dataSize, priority,numOfWBAN):

        self.dataSize = dataSize  # 任务的数据量
        self.priority = priority  # 任务的优先级

        self.timeLocal = 0  # 该任务在本地执行所需要的时间
        self.energyLocal = 0  # 该任务在本地执行所需要的能耗

        self.timeMEC = 0  # 该任务在服务器执行所需要的时间
        self.energyMEC = 0  # 该任务在服务器执行所需要的能耗

        self.timeTransmit = 0  # 该任务由WBAN中心节点发送至服务器需要的时间
        self.energyTransmit = 0  # 该任务由WBAN中心节点发送至服务器需要的能耗

        self.ifOffload = 0  # 该任务是卸载处理还是在本地处理，0：本地处理   1：卸载处理
        self.numOfWBAN = numOfWBAN  # 任务隶属的WBAN号

        self.timeWait = 0  # 任务在执行缓冲区/发送缓冲区/信道中的等待时间
        self.timeslice = 0  # 任务隶属的时间批次

        self.available = True  # 该任务是否在额定时延内执行完成
        self.priorityTrue = priority

        self.timeInto = 0  # 任务进入缓冲区的时钟时间


        self.finish = False         # 该任务是否已经完成
        self.userPriority = 0       # 用户优先级
        self.upDistance = 0         # 该任务上传距离
        self.migrateDistance = 0    #该任务的迁移距离
        self.waitInMEC = 0



    ##################################################################################################################

    # 设置任务的时间批次
    def set_timeslice_Task(self, timeslice):
        self.timeslice = timeslice

    # 设置任务的数据量
    def set_dataSize_Task(self, dataSize):
        self.dataSize = dataSize

    # 设置任务的优先级
    def set_priority_Task(self, priority):
        self.priority = priority

    # 设置任务的价值
    def set_value_Task(self, value):
        self.value = value

    # 设置任务的本地频率 本地处理的能耗和时延
    def set_Local_Task(self):
        # WBAN的CPU计算频率为1GHz
        frequencyLocal = 1 * math.pow(10, 9)
        # 本地处理时间 = 数据量（bit）* 1000 (处理1bit数据所需要的CPU周期) / 本地CPU频率
        self.timeLocal = self.dataSize * 1000 / frequencyLocal
        # 本地处理能耗 = 时延 * 功率 (0.5W)
        self.energyLocal = self.timeLocal * 0.5

    # 设置任务的服务器频率 卸载处理的能耗和时延
    def set_MEC_Task(self,power):
        # 服务器的计算能力是10GHz,处理1bit数据需要200周期
        frequencyMEC = power
        self.timeMEC = self.dataSize * 200 / frequencyMEC
        # self.energyMEC = pow(10, -24) * pow(frequencyMEC, 2)

    # 设置任务发射的时间和能耗
    def set_Transmit_Task(self, distance):
        # WBAN的带宽是5MHz
        bandwidth = 0.18 * pow(10, 6)
        # 计算信道
        noisePower = pow(10,-13)  # 噪声功率
        transmitPower = 0.1  # 发送功率为100mW
        channelCap = bandwidth * math.log( (1 + transmitPower*pow(distance, -4)/noisePower) ,2)  # 信道带宽

        # print("WBNA"+str(self.numOfWBAN)+"的信道容量为："+str(channelCap))

        self.timeTransmit = self.dataSize / channelCap
        self.energyTransmit = self.timeTransmit * 0.1  # 默认WBAN中心节点的发射功率为0.1W

    # 设置任务时卸载处理还是本地处理
    def set_ifOffload_Task(self, ifOffload):
        self.ifOffload = ifOffload

    # 设置任务在执行缓冲区/发送缓冲区中的等待时间
    def set_timeWait_Task(self, timeWait):
        self.timeWait = timeWait

    # 设置任务进入缓冲区的时间
    def set_timeInto_Task(self, timeInto):
        self.timeInto = timeInto

    # 设置任务离开缓冲区的时间
    def set_timeOut_Task(self, timeOut):
        self.timeOut = timeOut

    # 设置任务属于的WBAN的编号
    def set_numWBAN_Task(self, numOfWBAN):
        self.numOfWBAN = numOfWBAN



'''
#测试代码
task = Task(0,0,0,0,0,0,0,0,0,0,0,0)
Dict = task.__dict__
KEY = list(Dict.keys())
VALUE = list(Dict.values())
VALUE = [float(x) for x in VALUE]
showdata = []
showdata.append(VALUE)
print(KEY)
print(VALUE)
print(tabulate(showdata,headers=KEY,tablefmt='pipe',disable_numparse=True))
'''
