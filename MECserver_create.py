'''
每个MEC服务器设定有四个CPU，每个CPU的缓冲区设定为无限大，即不考虑内存大小

waitbuffer_addTask(self, Task)                  一个MEC服务器可能会在某一时间片接收到多个WBAN发送来的数据，同时接受到的任务放入虚拟列表waitBuffer
                                                然后进行优先级排序，waitBuffer实际不存在，任务在该列表中不存在排队时延

receive_Task(self, WBANList, Globalmap)         形参WBANList是当前场景中所有WBAN的集合，是一个列表。本函数每次遍历列表，如果有任务发送完成，则将任务送入
                                                waitBuffer中，在调用waitbuffer_addTask方法，进行排序

buffer_Allocation(self, Globalmap)              由于任务已经完成排序，则按照顺序将任务有限分配到可用的且缓冲区中数据量最小的CPU缓冲区中，进入缓冲区后开始计算排队时延

MEC_TaskExecution(self, Globalmap)              服务器CPU执行方法，方法执行原理和WBAN的CPU执行方法相似  
'''

import math
import operator
import random
import sys

sys.setrecursionlimit(5000000)

from Task_Create import Task
from WBAN_Create import WBAN
from config import Globalmap

class MEC(object):
    # 设置单个MEC服务器共具备四个工作缓冲区
    def __init__(self, number, coordinate , radius, computePower):

        # 本MEC服务器的编号
        self.number = number
        # 本服务器的坐标，该坐标固定
        self.coordinate = coordinate
        # 本服务器的覆盖范围
        self.radius = radius
        # 本服务器的计算能力
        self.computePower = computePower

        # 本服务器覆盖范围之内的用户列表
        self.WBANList = []
        # 每个WBAN共四个CPU，各有一个执行缓冲区
        self.executionBuffer = [[] for i in range(2)]
        # 等待分配缓冲区，该缓冲区实际并不存在
        self.waitBuffer = []
        # 当前四个CPU是否可以执行CPU缓冲区中的下一个任务
        self.exeBufferState = [True, True]
        # 当前四个CPU中的执行缓冲区中的数据量
        self.sizeOfBuffer = [0, 0]
        # 接收的任务数
        self.numOfReceive = []
        # 执行的任务数
        self.numOfExe = []


    ##################################################################################################################

    def waitbuffer_addTask(self, Task):
        # 每次向等待分配缓冲区放入一个任务，都需要将缓冲区队列进行一次排序,排队缓冲区内按优先级从高到低排列
        self.waitBuffer.append(Task)
        #self.waitBuffer = sorted(self.waitBuffer, key=operator.attrgetter('priority'))
        #self.waitBuffer = list(reversed(self.waitBuffer))

    ##################################################################################################################

    # 将WBAN发送到MEC服务器中的任务放入到waitBuffer中，每个时间片执行一次
    # 该函数的参数WBANList是指将系统中多个WBAN放入到一个列表中
    def receive_Task(self,Globalmap):

        # 对当前系统里的所有用户进行一个判断，判断是否有WBAN发送完任务
        for i in range(len(self.WBANList)):
            # 获取当前WBAN是否完成一个任务的发送
            check = self.WBANList[i].task_transmit(Globalmap)
            # 如果没有发送成功，task_transmit函数的返回值是0,则继续处理下一个任务
            if check == 0:
                continue
            # 如果有一个任务发送成功，即task_transmit函数的返回值是一个Task类对象
            elif type(check) == Task:
                # 将该任务放入虚拟缓冲区中

                self.waitbuffer_addTask(check)
                self.numOfReceive.append(check)


        self.waitBuffer = sorted(self.waitBuffer, key=operator.attrgetter('priority','userPriority'))
        self.waitBuffer = list(reversed(self.waitBuffer))

    ##################################################################################################################

    # 将排队缓冲区的任务分配到各个CPU缓冲区中
    def buffer_Allocation(self, Globalmap):

        # 获取当前系统时钟
        time = Globalmap.get_value('clocktime')

        for i in range(len(self.waitBuffer)):
            choice = min(self.sizeOfBuffer)

            # 给当前任务赋值进入缓冲区的时间
            self.waitBuffer[i].timeInto = time

            # 选择当前数据量最小的缓冲区，将当前任务放入该缓冲区
            index = self.sizeOfBuffer.index(choice)
            # 由于每个任务获得的计算资源一致，所以送入队列时就可以计算处理时延
            self.waitBuffer[i].set_MEC_Task(self.computePower)

            self.executionBuffer[index].append(self.waitBuffer[i])
            self.sizeOfBuffer[index] += self.waitBuffer[i].dataSize

        # 当虚拟缓冲区中的任务都分配到CPU缓冲区中，将虚拟缓冲区清空
        self.waitBuffer = []

    ##################################################################################################################

    #固定用户生成,按照给定的速率在本服务器范围内生成WBAN用户
    def add_WBAN(self,numOfWBAN):

        #为避免出现生成的用户坐标与服务器坐标一致，所以只随机生成一个方向的坐标和与服务器的距离
        for i in range(numOfWBAN):
            #随机生成用户与服务器之间的距离
            y_coordinate = random.uniform(1,self.radius)
            #随机生成用户的横坐标
            x_coordinate = random.uniform(1,self.radius)
            #随机生成用户的编号，目标用户编号是1，其他无所谓
            number = random.randint(2,1000)
            #随机生成用户的优先级，范围1-5
            priority = 1
            #随机生成用户的剩余电量
            energy = random.randint(5000,10000)

            #计算用户的纵坐标
            #distance = pow( ( pow(y_coordinate,2)+pow(x_coordinate,2) ),0.5)
            distance = 500

            coordinate = [x_coordinate,y_coordinate]


            # print("WBAN"+str(number)+"的坐标为："+str(coordinate))

            #生成WBAN对象，速度为0
            WBANTemp = WBAN(number,priority,energy,coordinate,0)
            WBANTemp.server = self.number
            WBANTemp.distance = distance

            #将生成的用户送入WBAN队列
            self.WBANList.append(WBANTemp)


    ##################################################################################################################

    # 卸载任务处理函数，计算卸载任务的处理时延和处理能耗
    def MEC_TaskExecution(self, Globalmap):
        # 获取当前系统时钟
        time = Globalmap.get_value('clocktime')
        finishBuffer = Globalmap.get_value('finishBuffer')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')

        # 首先循环判断当前四个CPU是否空闲
        for i in range(len(self.executionBuffer)):

            if len(self.executionBuffer[i]) == 0:
                self.exeBufferState[i] = True
                continue

            elif len(self.executionBuffer[i]) > 0:
                # 判断每一个CPU是否被占用
                if self.exeBufferState[i] == False:
                    # 如果该任务还没有执行完
                    if (time - self.executionBuffer[i][0].timeInto) < math.ceil(self.executionBuffer[i][0].timeMEC * math.pow(10, 6)):
                        self.exeBufferState[i] = False
                        continue
                    # 如果该任务执行完了
                    elif (time - self.executionBuffer[i][0].timeInto) >= math.ceil(self.executionBuffer[i][0].timeMEC * math.pow(10, 6)):
                        self.exeBufferState[i] = True
                        self.executionBuffer[i][0].finish = True
                        finishBuffer.append(self.executionBuffer[i][0])
                        Globalmap.set_value('finishBuffer', finishBuffer)
                        self.sizeOfBuffer[i] -= self.executionBuffer[i][0].dataSize
                        # del self.executionBuffer[i][0]
                        self.numOfExe.append(self.executionBuffer[i][0])
                        self.executionBuffer[i].remove(self.executionBuffer[i][0])

                        #调用HRRN算法
                        self.HRRN(Globalmap)
                        ###普通优先级调度###
                        #self.executionBuffer[i] = sorted(self.executionBuffer[i], key=operator.attrgetter('priority'),reverse=True)
                        # 传统HRRN
                        #self.HRRNTraditional(Globalmap)

                        continue




        # 将处理完成的任务取出后，再处理缓冲区中的下一个任务
        for i in range(len(self.executionBuffer)):

            if len(self.executionBuffer[i]) == 0:
                self.exeBufferState[i] = True
                continue

            elif len(self.executionBuffer[i]) > 0:
                # 如果当前CPU是空闲的
                if self.exeBufferState[i] == True:
                    # 判断当前将要执行的任务在执行时是否会超时
                    check = self.checkTaskAvailable(Globalmap, self.executionBuffer[i][0])

                    if check == -1 or self.executionBuffer[i][0].available == False:
                        self.exeBufferState[i] = True
                        # 将不满足执行统条件的任务送入失效列表
                        self.executionBuffer[i][0].available = False
                        self.executionBuffer[i][0].timeWait += (time - self.executionBuffer[i][0].timeInto) * pow(10,-6)
                        self.executionBuffer[i][0].waitInMEC = (time - self.executionBuffer[i][0].timeInto) * pow(10,-6)

                        unavailableBuffer.append(self.executionBuffer[i][0])
                        Globalmap.set_value('unavailableBuffer', unavailableBuffer)
                        # del self.executionBuffer[i][0]
                        self.executionBuffer[i].remove(self.executionBuffer[i][0])
                        self.MEC_TaskExecution(Globalmap)


                    elif check == 1 and self.executionBuffer[i][0].available == True:
                        self.executionBuffer[i][0].timeWait += (time - self.executionBuffer[i][0].timeInto)*pow(10,-6)  # 任务在执行缓冲区中等待的时间
                        self.executionBuffer[i][0].waitInMEC = (time - self.executionBuffer[i][0].timeInto) * pow(10,-6)
                        self.executionBuffer[i][0].set_MEC_Task(self.computePower)  # 计算该任务的卸载执行时延和能耗
                        self.executionBuffer[i][0].timeInto = time  # 该任务调度进入CPU的时间
                        self.exeBufferState[i] = False

                        continue



    ##################################################################################################################

    #获取当前服务器四个队列的平均排队时延
    def getAverageDelay(self):

        averageDelay = 0

        for i in range(len(self.executionBuffer)):
            for j in range(len(self.executionBuffer[i])):
                averageDelay += self.executionBuffer[i][j].timeMEC

        averageDelay = averageDelay / 4

        return averageDelay

    ##################################################################################################################

    # HRRN算法，优先级调度，当一个任务在服务器中处理完成时，调整等待队列中的任务的优先级，重新排序
    def HRRN(self,Globalmap):

        # 获取当前系统时钟和与服务器的距离
        time = Globalmap.get_value('clocktime')

        for i in range(len(self.executionBuffer)):

            for j in range(len(self.executionBuffer[i])):

                # 该任务该队列中排队的时间
                temp = time - self.executionBuffer[i][j].timeInto
                temp = temp * pow(10,-6) + self.executionBuffer[i][j].timeWait

                m = temp / self.executionBuffer[i][j].timeMEC
                n = math.floor(math.log((m + 2), 2))

                # 计算新的优先级
                priorityTemp = self.executionBuffer[i][j].priorityTrue + (n-1) + \
                               (temp - (pow(2, n) - 2) * self.executionBuffer[i][j].timeMEC) / (
                               pow(2, n) * self.executionBuffer[i][j].timeMEC)
                # 更新优先级
                self.executionBuffer[i][j].set_priority_Task(priorityTemp)

            # 当CPU处理完一个任务时调用，所以将队列整体重排序
            self.executionBuffer[i] = sorted(self.executionBuffer[i], key=operator.attrgetter('priority'),reverse=True)
            #self.executionBuffer[i] = list(reversed(self.executionBuffer[i]))


    ##################################################################################################################

    def HRRNTraditional(self,Globalmap):

        # 获取当前系统时钟和与服务器的距离
        time = Globalmap.get_value('clocktime')

        for i in range(len(self.executionBuffer)):

            for j in range(len(self.executionBuffer[i])):

                # 该任务该队列中排队的时间
                temp = time - self.executionBuffer[i][j].timeInto
                temp = temp * pow(10,-6) + self.executionBuffer[i][j].timeWait

                # 计算新的优先级
                priorityTemp = self.executionBuffer[i][j].priorityTrue + (temp + self.executionBuffer[i][j].timeMEC) / self.executionBuffer[i][j].timeMEC
                # 更新优先级
                self.executionBuffer[i][j].set_priority_Task(priorityTemp)

            # 当CPU处理完一个任务时调用，所以将队列整体重排序
            self.executionBuffer[i] = sorted(self.executionBuffer[i], key=operator.attrgetter('priority'),reverse=True)
            #self.executionBuffer[i] = list(reversed(self.executionBuffer[i]))



    ##################################################################################################################

    # 判断任务送入服务器执行时会不会超时
    def checkTaskAvailable(self,Globalmap,Task):

        # 获取当前系统时钟
        time = Globalmap.get_value('clocktime')
        # 设置每个优先级的额定处理时延
        # maxDelay = [40000, 35000, 30000, 25000, 20000, 15000, 10000, 5000]
        maxDelay = [10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3),
                    10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3)]
        index = Task.priorityTrue

        #计算本任务的服务器处理的时延
        Task.set_MEC_Task(self.computePower)

        # 计算该任务已有的等待时延+在该缓冲区中的时延+执行时延
        temp = time - Task.timeInto
        temp = temp*pow(10,-6)  + Task.timeWait + Task.timeMEC + Task.timeTransmit

        if temp > maxDelay[index]:
            # print("CPU检测失效")
            return -1
        elif temp <= maxDelay[index]:
            return 1


    # 检索服务器的八个队列中的任务是否超时
    def checkBufferAvailable(self,Globalmap):

        # 获取当前系统时钟和失效列表
        time = Globalmap.get_value('clocktime')
        unavailableBuffer = Globalmap.get_value('unavailableBuffer')

        # 设置每个优先级的额定处理时延，单位是微秒
        # maxDelay = [40000, 35000, 30000, 25000, 20000, 15000, 10000, 5000]
        maxDelay = [10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3),
                    10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3), 10 * pow(10, -3)]

        for i in range(len(self.executionBuffer)):

            if len(self.executionBuffer[i]) <= 1:
                continue

            elif len(self.executionBuffer[i]) > 1:
                for j in range(len(self.executionBuffer[i])):

                    temp = time - self.executionBuffer[i][j].timeInto
                    temp = temp * pow(10, -6) + self.executionBuffer[i][j].timeTransmit + self.executionBuffer[i][j].timeWait
                    index = self.executionBuffer[i][j].priorityTrue

                    # 如果该任务没有超时
                    if temp <= maxDelay[index]:
                        continue
                    # 如果该任务超时
                    elif temp > maxDelay[index]:
                        # print("缓冲区检测失效")
                        self.executionBuffer[i][j].available = False
                        unavailableBuffer.append(self.executionBuffer[i][j])
                        # 重新赋值失效列表
                        Globalmap.set_value('unavailableBuffer', unavailableBuffer)

                        # 将失效的任务从等待队列中删除
                self.executionBuffer[i] = [self.executionBuffer[i][k] for k in range(len(self.executionBuffer[i])) if self.executionBuffer[i][k].available == True]




    ##################################################################################################################

