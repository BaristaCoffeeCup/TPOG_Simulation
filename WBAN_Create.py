'''
每个WBAN的中心节点中包括两个缓冲区：执行缓冲区和发送缓冲区，每个缓冲区大小为1GB，如果缓冲区已满，则丢弃当前需要进入缓冲区的任务
每个WBAN代表一个用户，每个用户的坐标会实时改变
该两个缓冲区中的任务都是串行排队，单个任务的最大数据量不会超过1000B比特
WBAN类方法暂时有以下几种

return_executionBuffer(self)                    判断当前WBAN的执行缓冲区的剩余空间是否还能装下单个任务，可以装下就返回1，不能就返回-1

return_transmitBuffer(self)                     判断当前WBAN的发送缓冲区的剩余空间是否还能装下单个任务，可以装下就返回1，不能就返回-1

add_Task_List(self, numOfPacket, Globalmap)     在固定时间片周期调用，按照一定概率生成任务，生成的任务先放在虚拟列表tasklist中，该缓冲区实际上并不存在
                                                numOfPacket是指这一批的任务的大小 = 单个数据包 * numOfPacket，这一机制还需要修改
                                                某一批任务生成后在本方法中会赋值一些基本属性，不包括计算和通信资源分配

buffer_Allocation(self, Globalmap)              当调用了算法之后，根据卸载决策将任务分别送入两个缓冲区，进入缓冲区后开始计算排队时延
                                                当缓冲区已满时，剩余的任务全部丢弃，缓冲区的模拟都是用列表实现的。任务按照优先级高到低排列

checkTaskAvailable(self, Globalmap, Task)       判断当前任务的时效性，当发送缓冲区或本地执行缓冲区中的任务将要进入信道或者本地CPU时，需要判断该任务是否会超时
                                                每个优先级任务的最大时延不同，时延 = 排队时延 + （发送时延）+ 执行时延，如果任务超时就丢弃

checkBufferAvailable(self, Globalmap)           由于信道或CPU中的任务都由上一个方法确定不会超时，本方法遍历发送缓冲区或本地执行缓冲区中的任务等待的时延是否超时
                                                如果超时就将该任务从缓冲区中删除，放入失效列表

task_execution(self, Globalmap)                 本地CPU执行方法，每次执行需要判断当前CPU中的任务是否执行完成，如果没有则结束方法，如果完成则将执行缓冲区中第一个任务调入

task_transmit(self, Globalmap)                  与上一个函数同理，如果任务发送完成，则将发送缓冲区的第一个任务return，如果没有完成则返回0
'''


from tabulate import tabulate
import math
import operator
import random
import sys

sys.setrecursionlimit(5000000)
from Task_Create import Task
from config import Globalmap


class WBAN(object):
    def __init__(self, number, priority, energy, coordinate, speed):
        # WBAN的编号
        self.number = number
        # WBAN的优先级
        self.priority = priority
        # WBAN剩余能量
        self.energy = energy
        # WBAN当前时刻的坐标
        self.coordinate = coordinate
        # WBAN的移动速度
        self.speed = speed

        # WBAN的当前时刻的连接服务器的编号
        self.server = 0
        # WBAN与当前所处覆盖范围的MEC服务器的距离
        self.distance = 0
        # WBAN的任务列表，不是真实存在的缓冲区
        self.taskList = []
        # WBAN的传输任务等待区
        self.transmitBuffer = []
        # WBAN的执行任务缓冲区
        self.executionBuffer = []
        # WBAN是否可以发送下一个任务
        self.tranState = True
        # WBAN是否可以执行下一个任务
        self.exeState = True

        self.energyTrue = energy

        #WBAN的移动方向
        self.angle = random.randint(0,365)
        #WBAN更换移动方向的时间点
        self.timeChange = 0
        #完成的总任务数
        self.numOfTask = [ 0 for i in range(8) ]
        #发送成功的任务数
        self.numOfTransmit = []
        #各优先级迁移的任务数
        self.numOfMigrate = [ 0 for i in range(8) ]


    ##################################################################################################################

    def set_Priority_WBAN(self, priority):
        self.priority = priority

    def set_Energy_WBAN(self, energy):
        self.energy = energy

    def set_Coordinate_WBAN(self, coordinate):
        self.coordinate = coordinate

    def set_Distance_WBAN(self,distance):
        self.distance = distance

    ##################################################################################################################

    # 计算当前执行缓冲区或发送缓冲区中的数据量，缓冲区最大数据量为1GB，如果剩余空间不足则需要在任务池中等待，假设任务池是无穷大的
    # 任务生成后按照优先级高低和是否卸载放入本地执行任务池或者发送任务池中
    def return_executionBuffer(self):
        maxSize = pow(2, 30)
        temp = 0
        for i in range(1, len(self.executionBuffer)):
            temp += self.executionBuffer[i].dataSize

        if maxSize - temp >= 300:
            return 1
        elif maxSize - temp < 300:
            return -1

    def return_transmitBuffer(self):
        maxSize = pow(2, 30)
        temp = 0
        for i in range(1, len(self.transmitBuffer)):
            temp += self.transmitBuffer[i].dataSize

        if maxSize - temp >= 300:
            return 1
        elif maxSize - temp < 300:
            return -1

    ##################################################################################################################

    # 对应WBAN的八个优先级的节点生成任务
    def add_Task_List(self, numOfPacket, Globalmap):
        # 获取当前系统时钟
        time = Globalmap.get_value('clocktime')

        # 八个优先级任务的数据量
        sizeOfTask = [128, 192, 256, 768, 256, 192, 192, 64]  # 2000bit
        # 在某一时刻，不同优先级任务按照不同概率生成
        #probability = [0.8, 0.8, 0.8, 0.3, 0.4, 0.4 * self.priority, 0.2 * self.priority, 0.1 * self.priority]

        for j in range(0,numOfPacket):
            # 每个优先级任务的数据量相同，每秒生成一次
            for i in range(0, 8):

                task = Task(0, i, self.number)
                task.set_dataSize_Task(sizeOfTask[i])  # 任务的数据量
                task.set_priority_Task(i)  # 任务的优先级，如果卸载处理，其优先级对于任务优先级*WBAN优先级
                task.set_timeslice_Task(time)  # 任务产生时的时间片
                task.set_numWBAN_Task(self.number)  # 任务所隶属的WBAN的编号
                task.userPriority = self.priority

                self.taskList.append(task)
                self.numOfTask[i] += 1

        self.taskList = sorted(self.taskList, key=operator.attrgetter('priority'))
        self.taskList = list(reversed(self.taskList))

        '''
        for i in range(0, 8):
            # 判断当前任务是否生成，按照一定的概率随机生成
            p = np.array([probability[i], 1-probability[i]])
            index = np.random.choice([1, 0], p=p.ravel())
            if index == 1:
                value = pow(self.priority, 2) * pow(i+1, 2) * \
                    math.log2(1+sizeOfTask[i])
                value = format(value, '.10f')
                task = Task(0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                task.set_dataSize_Task(sizeOfTask[i]*numOfPacket)  # 任务的数据量
                task.set_priority_Task(i)  # 任务的优先级，如果卸载处理，其优先级对于任务优先级*WBAN优先级
                task.set_value_Task(value)  # 任务的价值
                task.set_timeslice_Task(time)  # 任务产生时的时间片
                task.set_numWBAN_Task(self.number)  # 任务所隶属的WBAN的编号

                self.taskList.append(task)
        '''

    ##################################################################################################################

    # 遍历当前生成的业务列表，根据每个任务是否卸载将其放入对应的列表，等待排序，需要判断这两个缓冲区剩余空间的大小
    def buffer_Allocation(self, Globalmap):

        # 获取当前系统时钟和失效列表
        time = Globalmap.get_value('clocktime')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')

        # 现将当前生成的任务列表中的任务按照任务优先级从高到低进行排序
        self.taskList = sorted(self.taskList, key=operator.attrgetter('priority'))
        self.taskList = list(reversed(self.taskList))

        # 获取本地执行缓冲区和发送缓冲区的状况，等于1则可以继续放入任务，等于-1则不能放入任务
        check_1 = self.return_executionBuffer()
        check_2 = self.return_transmitBuffer()

        for i in range(len(self.taskList)):

            # 若当前本地执行Buffer有空闲空间，则将该任务放入本地执行Buffer
            if self.taskList[i].ifOffload == 0:
                # 如果该缓冲区有足够的空间,则放入该任务
                if check_1 == 1:
                    self.executionBuffer.append(self.taskList[i])
                    self.taskList[i].timeInto = time  # 任务进入本地执行Buffer的时间点
                # 如果该缓冲区没有足够的空间，则将该任务放入失效列表
                elif check_1 == -1:
                    self.taskList[i].available = False
                    unavailableBuffer.append(self.taskList[i])

            # 若当前发送Buffer有空闲空间，则将该任务送入发送Buffer
            elif self.taskList[i].ifOffload == 1:
                # 如果该缓冲区有足够的空间,则放入该任务
                if check_2 == 1:
                    # 如果该任务卸载，则优先级=本身任务优先级 + WBAN优先级
                    # self.taskList[i].priority = self.taskList[i].priority + self.priority
                    self.transmitBuffer.append(self.taskList[i])
                    self.taskList[i].timeInto = time  # 任务进入发送Buffer的时间点
                # 如果该缓冲区没有足够的空间，则将该任务放入失效列表
                elif check_2 == -1:
                    self.taskList[i].available = False
                    unavailableBuffer.append(self.taskList[i])

        # 重新赋值失效列表
        Globalmap.set_value('unavailableBuffer', unavailableBuffer)
        # 清空任务列表
        self.taskList.clear()

    ##################################################################################################################

    #优先级调度，当一个任务本地计算完成或者发送成功时，调整等待队列中的任务的优先级，重新排序
    def HRRN(self,Globalmap,choice):

        #获取当前系统时钟和与服务器的距离
        time = Globalmap.get_value('clocktime')

        if choice == 1:
            # 调整本地执行队列的任务优先级
            for i in range(len(self.executionBuffer)):
                # 计算该任务本地计算时延
                self.executionBuffer[i].set_Local_Task()
                # 该任务在队列中的等待时间
                temp = time - self.executionBuffer[i].timeInto
                temp = temp * pow(10,-6)

                m = temp/self.executionBuffer[i].timeLocal
                n = math.floor( math.log((m+2),2) )

                # 重置任务的优先级
                priorityTemp1 = self.executionBuffer[i].priorityTrue + (n-1) + \
                                (temp - (pow(2,n)-2)*self.executionBuffer[i].timeLocal)/( pow(2,n)*self.executionBuffer[i].timeLocal )

                self.executionBuffer[i].set_priority_Task(priorityTemp1)

            # 按照优先级重新排序
            self.executionBuffer = sorted(self.executionBuffer, key=operator.attrgetter('priority'),reverse=True)
            #self.executionBuffer = sorted(self.executionBuffer, key=operator.attrgetter('timeslice'))


        #********************************************

        elif choice == 2:
            # 调整本地发送队列的任务优先级
            for j in range(len(self.transmitBuffer)):
                # 计算任务发送时延
                self.transmitBuffer[j].set_Transmit_Task(self.distance)
                # 该任务在队列中的等待时间
                temp = time - self.transmitBuffer[j].timeInto
                temp = temp * pow(10, -6)

                m = temp / self.transmitBuffer[j].timeTransmit
                n = round(math.log((m + 2), 2))

                # 重置任务优先级
                priorityTemp2 = self.transmitBuffer[j].priorityTrue + (n-1) + \
                                (temp - (pow(2, n) - 2) * self.transmitBuffer[j].timeTransmit) / (
                                pow(2, n) * self.transmitBuffer[j].timeTransmit)

                self.transmitBuffer[j].set_priority_Task(priorityTemp2)

            # 按照优先级重新排序
            self.transmitBuffer = sorted(self.transmitBuffer,key=operator.attrgetter('priority'),reverse=True)
            #self.transmitBuffer = sorted(self.transmitBuffer, key=operator.attrgetter('timeslice'))


    ##################################################################################################################

    # 检查将要执行或者发送的一个任务在送入CPU/信道时是否会超时
    def checkTaskAvailable(self, Globalmap, Task):

        # 获取当前系统时钟和失效列表
        time = Globalmap.get_value('clocktime')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')

        # 设置每个优先级的额定处理时延
        # maxDelay = [40000, 35000, 30000, 25000, 20000, 15000, 10000, 5000]
        maxDelay = [10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3),
                    10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3)]
        index = Task.priorityTrue

        # 如果该任务在本地执行
        if Task.ifOffload == 0:
            Task.set_Local_Task()
            # 计算该任务已有的等待时延+在该缓冲区中的时延+执行时延
            temp = time - Task.timeInto
            temp = temp*pow(10,-6) + Task.timeWait + Task.timeLocal
            if temp > maxDelay[index]:
                return -1
            elif temp <= maxDelay[index]:
                return 1

        # 如果该任务卸载执行
        elif Task.ifOffload == 1:
            Task.set_Transmit_Task(self.distance)
            # 计算该任务已有的等待时延+在该缓冲区中的时延+发送时延
            temp = time - Task.timeInto
            temp = temp * pow(10, -6) + Task.timeWait + Task.timeTransmit
            if temp > maxDelay[index]:
                return -1
            elif temp <= maxDelay[index]:
                return 1

    # 检查WBAN的两个缓冲区中是否有超时的任务，如果有就丢弃
    def checkBufferAvailable(self, Globalmap):
        # 获取当前系统时钟和失效列表
        time = Globalmap.get_value('clocktime')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')

        # 设置每个优先级的额定处理时延，单位是微秒
        # maxDelay = [40000, 35000, 30000, 25000, 20000, 15000, 10000, 5000]
        maxDelay = [10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3),
                    10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3)]


        if len(self.executionBuffer) > 1:
            # 分别判断两个缓冲区中的任务是否过去，如果过期就直接删除
            for i in range(1, len(self.executionBuffer)):
                temp = time - self.executionBuffer[i].timeInto
                temp = temp * pow(10, -6)
                index = self.executionBuffer[i].priorityTrue
                if temp < maxDelay[index]:
                    continue
                elif temp >= maxDelay[index]:
                    self.executionBuffer[i].available = False
                    self.executionBuffer[i].timeWait = temp
                    unavailableBuffer.append(self.executionBuffer[i])
                    # 重新赋值失效列表
                    Globalmap.set_value('unavailableBuffer', unavailableBuffer)
                    # self.executionBuffer.remove(self.executionBuffer[i])

            # 将失效的任务从等待队列中删除
            self.executionBuffer = [self.executionBuffer[k] for k in range(len(self.executionBuffer)) if self.executionBuffer[k].available == True]


        if len(self.transmitBuffer) > 1:
            for i in range(1, len(self.transmitBuffer)):
                temp = time - self.transmitBuffer[i].timeInto
                temp = temp * pow(10, -6)
                index = self.transmitBuffer[i].priorityTrue
                if temp < maxDelay[index]:
                    continue
                elif temp >= maxDelay[index]:
                    self.transmitBuffer[i].available = False
                    self.transmitBuffer[i].timeWait = temp
                    unavailableBuffer.append(self.transmitBuffer[i])
                    # 重新赋值失效列表
                    Globalmap.set_value('unavailableBuffer', unavailableBuffer)
                    # self.transmitBuffer.remove(self.transmitBuffer[i])

                    # 将失效的任务从等待队列中删除
            self.transmitBuffer = [self.transmitBuffer[k] for k in range(len(self.transmitBuffer)) if self.transmitBuffer[k].available == True]


    ##################################################################################################################

    # 本地执行函数，用于处理本地执行缓冲区的任务  每个时间片执行一次 处理执行缓冲区第一个任务

    def task_execution(self, Globalmap):
        # 获取当前系统时钟
        time = Globalmap.get_value('clocktime')
        finishBuffer = Globalmap.get_value('finishBuffer')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')

        # 判断当前CPU是否空闲，检查exeState变量
        if self.exeState == False:

            if len(self.executionBuffer) == 0:
                self.exeState = True
                return 0

            elif len(self.executionBuffer) > 0:
                # 检查当前执行缓冲区的第一个任务是否执行完
                if (time - self.executionBuffer[0].timeInto) < math.ceil(self.executionBuffer[0].timeLocal * math.pow(10, 6)):
                    # 当前CPU中的任务还没有执行完
                    # print('WBAN' + str(self.number) + '正在执行任务')
                    return 0
                elif (time - self.executionBuffer[0].timeInto) >= math.ceil(self.executionBuffer[0].timeLocal * math.pow(10, 6)):
                    # 当前CPU中的任务执行完毕，将该任务从执行缓冲区中取出，放入完成缓冲区，设置CPU空闲
                    self.exeState = True
                    self.executionBuffer[0].finish = True

                    finishBuffer.append(self.executionBuffer[0])
                    Globalmap.set_value('finishBuffer', finishBuffer)

                    self.executionBuffer.remove(self.executionBuffer[0])

                    ###这里决定是否调用HRRN算法###
                    self.HRRN(Globalmap,1)
                    ###这里决定按照普通优先级排序###
                    #self.executionBuffer = sorted(self.executionBuffer, key=operator.attrgetter('priority'),reverse=True)
                    # 传统HRRN
                    #self.HRRNTraditional(Globalmap, 1)




        if self.exeState == True:

            #如果缓冲区中没有任务,返回0
            if len(self.executionBuffer) == 0:
                return 0

            elif len(self.executionBuffer) > 0:
                # 首先判断执行缓冲区第一个任务在执行过程中会不会超时
                check = self.checkTaskAvailable(Globalmap, self.executionBuffer[0])

                # 如果当前这个任务在执行时会超时，则删除这个任务，执行下一个任务
                if check == -1:
                    self.exeState = True

                    # 将不满足执行统条件的任务送入失效列表
                    self.executionBuffer[0].available = False
                    self.executionBuffer[0].timeWait += (time - self.executionBuffer[0].timeInto) * pow(10, -6)

                    unavailableBuffer.append(self.executionBuffer[0])
                    Globalmap.set_value('unavailableBuffer', unavailableBuffer)
                    # del self.executionBuffer[0]
                    self.executionBuffer.remove(self.executionBuffer[0])
                    self.task_execution(Globalmap)
                # 如果不会超时
                elif check == 1:
                    self.executionBuffer[0].timeWait += (time - self.executionBuffer[0].timeInto)*pow(10,-6)  # 该任务在执行缓冲区中等待的时间
                    self.executionBuffer[0].timeInto = time  # 开始执行该任务的起始时间
                    self.executionBuffer[0].set_Local_Task()  # 计算该任务的本地执行时延和本地执行能耗
                    self.exeState = False  # 设置CPU被占用
                    # 计算WBAN剩余的能量
                    energy = self.energy - self.executionBuffer[0].energyLocal
                    self.set_Energy_WBAN(energy)

                    return 0



    ##################################################################################################################

    # WBAN发送缓冲区的管理，判断当前信道是否可用，发送出的任务放入MEC的等待缓冲区，每个时间片执行一次 处理发送缓冲区第一个业务
    def task_transmit(self, Globalmap):

        # 获取当前系统时钟和距离,以及递归时需要用的临时变量
        time = Globalmap.get_value('clocktime')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')


        if self.tranState == True:

            #如果发送队列没有任务，返回0
            if len(self.transmitBuffer) == 0:
                return 0

            elif len(self.transmitBuffer) > 0:
                # 首先判断发送缓冲区第一个任务在执行过程中会不会超时
                check = self.checkTaskAvailable(Globalmap, self.transmitBuffer[0])

                # 如果当前这个任务在发送时会超时，则删除这个任务，执行下一个任务
                if check == -1:
                    self.tranState = True
                    # 将不满足发送统条件的任务送入失效列表
                    self.transmitBuffer[0].available = False
                    self.transmitBuffer[0].timeWait += (time - self.transmitBuffer[0].timeInto) * pow(10, -6)
                    unavailableBuffer.append(self.transmitBuffer[0])
                    Globalmap.set_value('unavailableBuffer', unavailableBuffer)

                    self.transmitBuffer.remove(self.transmitBuffer[0])

                    self.task_transmit(Globalmap)  # 递归

                # 如果不会超时
                elif check == 1:
                    self.transmitBuffer[0].timeWait += (time - self.transmitBuffer[0].timeInto)*pow(10,-6)  # 该任务在发送缓冲区中等待的时间
                    self.transmitBuffer[0].timeInto = time  # 开始发送该任务的起始时间
                    self.transmitBuffer[0].set_Transmit_Task(self.distance)  # 计算该任务的本地执行时延和本地执行能耗

                    self.tranState = False  # 设置发送设备被占用
                    # 计算WBAN剩余的能量
                    energy = self.energy - self.transmitBuffer[0].energyTransmit
                    self.set_Energy_WBAN(energy)



        # 检查当前信道是否空闲，检查tranState变量
        if self.tranState == False:

            if len(self.transmitBuffer) == 0:
                self.tranState = True
                return 0

            elif len(self.transmitBuffer) > 0:

                # 检查发送缓冲区第一个业务是否已经发送完
                if (time - self.transmitBuffer[0].timeInto) < math.ceil(self.transmitBuffer[0].timeTransmit * math.pow(10, 6)):
                    # 当前的任务还没有发送完
                    # print('WBAN' + str(self.number) + '正在发送任务')
                    return 0
                elif (time - self.transmitBuffer[0].timeInto) >= math.ceil(self.transmitBuffer[0].timeTransmit * math.pow(10, 6)):
                    # 当前信道里的任务已经发送完了，将该任务从发送缓冲区中取出，并用return返回该任务，并存入MEC服务器的等待缓冲区
                    self.tranState = True

                    # 重置任务优先级 = 原任务优先级
                    self.transmitBuffer[0].upDistance = self.distance   #记录上传距离
                    self.transmitBuffer[0].priority = self.transmitBuffer[0].priorityTrue
                    temp = self.transmitBuffer.pop(0)
                    self.numOfTransmit.append(temp.priorityTrue)


                    ###这里决定是否调用HRRN算法
                    self.HRRN(Globalmap, 2)
                    ###这里按照普通优先级排序###
                    #self.transmitBuffer = sorted(self.transmitBuffer, key=operator.attrgetter('priority'),reverse=True)
                    #传统HRRN
                    #self.HRRNTraditional(Globalmap,2)

                    return temp




    ##################################################################################################################


    # 计算当前时刻WBAN所在的坐标
    def check_Coordinate(self, Globalmap , coordinate):
        # 获取当前系统时钟
        timeNow = Globalmap.get_value('clocktime')
        # 获取用户在上一时刻的坐标
        x = self.coordinate[0]
        y = self.coordinate[1]

        #其他时间按照直线运动

        timeRun = timeNow * pow(10,-6)
        x_New = 750 + self.speed * timeRun
        y_New = 820

        # 获取服务器的横纵坐标
        x_MEC = coordinate[0]
        y_MEC = coordinate[1]

        # 将计算出的坐标值赋值给WBAN的坐标变量
        coordinate = [x_New, y_New]
        self.set_Coordinate_WBAN(coordinate)

        # 计算此时二者的距离并更新
        distance = ( abs(x_New-x_MEC)**2 + abs(y_New-y_MEC)**2 ) ** 0.5
        self.set_Distance_WBAN(distance)

        # print(str(self.number)+"号当前距离是："+str(self.distance))



    ##################################################################################################################

    #获取当前WBAN的本地执行队列和发送队列的等待时延
    def getQueueDelay(self):

        delayLocal = 0
        delayTransmit = 0

        for i in range(len(self.executionBuffer)):
            delayLocal += self.executionBuffer[i].timeLocal

        for j in range(len(self.transmitBuffer)):
            delayTransmit += self.transmitBuffer[j].timeTransmit

        # print("WBAN执行队列时延为："+str(delayLocal))
        # print("WBAN发送队列时延为："+str(delayTransmit))
        # print()
        return [delayLocal,delayTransmit]



    ##################################################################################################################

    def HRRNTraditional(self,Globalmap,choice):

        #获取当前系统时钟和与服务器的距离
        time = Globalmap.get_value('clocktime')

        if choice == 1:
            # 调整本地执行队列的任务优先级
            for i in range(len(self.executionBuffer)):
                # 计算该任务本地计算时延
                self.executionBuffer[i].set_Local_Task()
                # 该任务在队列中的等待时间
                temp = time - self.executionBuffer[i].timeInto
                temp = temp * pow(10,-6)

                # 重置任务的优先级
                priorityTemp1 = self.executionBuffer[i].priorityTrue + (temp + self.executionBuffer[i].timeLocal)/self.executionBuffer[i].timeLocal

                self.executionBuffer[i].set_priority_Task(priorityTemp1)

            # 按照优先级重新排序
            self.executionBuffer = sorted(self.executionBuffer, key=operator.attrgetter('priority'),reverse=True)
            #self.executionBuffer = sorted(self.executionBuffer, key=operator.attrgetter('timeslice'))

        elif choice == 2:
            # 调整本地发送队列的任务优先级
            for j in range(len(self.transmitBuffer)):
                # 计算任务发送时延
                self.transmitBuffer[j].set_Transmit_Task(self.distance)
                # 该任务在队列中的等待时间
                temp = time - self.transmitBuffer[j].timeInto
                temp = temp * pow(10, -6)

                # 重置任务优先级
                priorityTemp2 = self.transmitBuffer[j].priorityTrue + (temp + self.transmitBuffer[j].timeTransmit)/self.transmitBuffer[j].timeTransmit

                self.transmitBuffer[j].set_priority_Task(priorityTemp2)

            # 按照优先级重新排序
            self.transmitBuffer = sorted(self.transmitBuffer,key=operator.attrgetter('priority'),reverse=True)
            #self.transmitBuffer = sorted(self.transmitBuffer, key=operator.attrgetter('timeslice'))

    ##################################################################################################################

















    ##################################################################################################################


    # 打印当前WBAN所有任务的属性值
    def print_TaskList(self):

        KEYS = ['数据量', '优先级', '本地时延', '本地能耗', 'MEC时延','MEC能耗', '发送时延', '发送能耗',
                '决策', 'BAN号', '排队时延', '时间片', '有效', '原优先级']
        VALUE = []
        for i in range(len(self.taskList)):
            value = self.taskList[i].__dict__.values()
            value = list(value)
            for j in range(0, 3):
                value.pop(14)
            value = [float(x) for x in value]
            VALUE.append(value)
        print()
        print("WBAN " + str(self.priority) + " 任务细节如下：")
        print(tabulate(VALUE, headers=KEYS, tablefmt='rst', disable_numparse=True))
        print()
        print()

    ##################################################################################################################

    # 输出当前在发送缓冲区内的任务细节
    def printTransmitBuffer(self):

        KEYS = ['数据量', '优先级', '本地时延', '本地能耗', 'MEC时延', 'MEC能耗', '发送时延', '发送能耗',
                '决策', 'BAN号', '排队时延', '时间片', '有效', '原优先级']
        VALUE = []
        for i in range(len(self.transmitBuffer)):
            value = self.transmitBuffer[i].__dict__.values()
            value = list(value)
            for j in range(0, 4):
                value.pop(14)
            value = [float(x) for x in value]
            VALUE.append(value)
        print()
        print("WBAN " + str(self.priority) + " 发送缓冲区细节如下：")
        print(tabulate(VALUE, headers=KEYS, tablefmt='rst', disable_numparse=True))
        print()
        print()

    ##################################################################################################################

    # 输出当前在执行缓冲区内的任务细节
    def printExecutionBuffer(self):

        KEYS = ['数据量', '优先级', '本地时延', '本地能耗', 'MEC时延', 'MEC能耗', '发送时延', '发送能耗',
                '决策', 'BAN号', '排队时延', '时间片', '有效', '原优先级']
        VALUE = []
        for i in range(len(self.executionBuffer)):
            value = self.executionBuffer[i].__dict__.values()
            value = list(value)
            for j in range(0, 4):
                value.pop(14)
            value = [float(x) for x in value]
            VALUE.append(value)
        print()
        print("WBAN " + str(self.priority) + " 执行缓冲区细节如下：")
        print(tabulate(VALUE, headers=KEYS, tablefmt='rst', disable_numparse=True))
        print()
        print()

    ##################################################################################################################

        # 输出当前在执行缓冲区内的任务细节
    def printFinishBuffer(self,list1,list2):

        finishBuffer = list1
        unavailableBuffer = list2

        KEYS = ['数据量', '优先级', '本地时延', '本地能耗', 'MEC时延', 'MEC能耗', '发送时延', '发送能耗',
                    '决策', 'BAN号', '排队时延', '时间片', '有效', '原优先级']
        VALUE = []
        for i in range(len(finishBuffer)):
            value = finishBuffer[i].__dict__.values()
            value = list(value)
            for j in range(0, 6):
                value.pop(14)
            value = [float(x) for x in value]
            VALUE.append(value)

        print()
        print(" 完成缓冲区细节如下：")
        print(tabulate(VALUE, headers=KEYS, tablefmt='rst', disable_numparse=True))
        print()
        print()

        VALUE = []
        for i in range(len(unavailableBuffer)):
            value = unavailableBuffer[i].__dict__.values()
            value = list(value)
            for j in range(0, 5):
                value.pop(14)
            value = [float(x) for x in value]
            VALUE.append(value)

        print()
        print(" 失效缓冲区细节如下：")
        print(tabulate(VALUE, headers=KEYS, tablefmt='rst', disable_numparse=True))
        print()
        print()



    ##################################################################################################################

'''gl = Globalmap()
gl._init_()
WBAN_A = WBAN(1, 1, 1000, [2650, 3825], 5)
WBAN_A.add_Task_List(1, gl)

# WBAN_A.taskList = list(reversed(WBAN_A.taskList))

WBAN_A.taskList = [ WBAN_A.taskList[i] for i in range(len(WBAN_A.taskList)) if WBAN_A.taskList[i].priority < 4]

WBAN_A.print_TaskList()'''





