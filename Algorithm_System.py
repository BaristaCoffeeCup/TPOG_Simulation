import math
import operator
import random
import copy
import numpy as np

from Task_Create import Task
from WBAN_Create import WBAN
from MECserver_create import MEC
from config import Globalmap

#创建系统算法类，将需要使用的算法作为该类的方法
class AS(object):

    def __init__(self):
        pass


    #####################################################################################################################

    #获取当前用户所处的坐标，能够提供计算服务器的服务器列表
    def getSelectedMEC(self,MECList,WBAN):

        #候选MEC列表，用户方法返回值
        selectedMEC = []
        selectedDistance = []
        selectedNumber = []
        #获取用户的坐标
        x_WBAN = WBAN.coordinate[0]
        y_WBAN = WBAN.coordinate[1]

        #计算目标WBAN距离所有服务器的距离
        for i in range(len(MECList)):

            #获取某一个服务器的坐标
            x_MEC = MECList[i].coordinate[0]
            y_MEC = MECList[i].coordinate[1]

            #计算用户与该服务器的距离
            distanceTemp = ( abs(x_MEC - x_WBAN)**2 + abs(y_MEC - y_WBAN)**2 ) ** 0.5

            #判断该服务器是否可以提供服务
            if distanceTemp < MECList[i].radius:
                selectedMEC.append(MECList[i])
                selectedDistance.append(distanceTemp)
                selectedNumber.append(MECList[i].number)

        #将候选列表和候选服务器的距离返回
        return [selectedMEC,selectedDistance,selectedNumber]


    #####################################################################################################################

    #判断是否要开始进行迁移 每个时间片判断一次，获取候选服务器列表
    #候选服务器符合 0.95和1.5准则
    def judge_Migrate(self,MECList,WBAN):

        #获取当前可连接的设备列表和距离列表
        result = self.getSelectedMEC(MECList,WBAN)
        selectedMEC = result[0]
        selectedDistance = result[1]
        selectedNumber = result[2]


        print("当前连接的服务器编号为：" + str(WBAN.server) )

        #如果可连接的服务器只有一个，则不必使用层次分析法
        if len(selectedMEC) == 1 or len(selectedMEC) == 0:
            #如果范围内只有一个服务器时，选择该服务器
            if len(selectedMEC) == 1:
                WBAN.server = selectedMEC[0].number
            return False

        #如果可连接的服务器多于一个，则开始第一层筛选
        elif len(selectedMEC) > 1:

            index1 = MECList.index(WBAN.server)
            tempMEC = MECList[index1]
            selectedMEC.append(tempMEC)
            index = selectedMEC.index(tempMEC)

            #初始化比较属性的二维数组
            comparedList = [ [1000]*4 for i in range(len(selectedMEC)) ]

            #将当前服务器列表中每个服务器需要比较的属性赋值给比较列表
            for i in range(len(selectedMEC)):
                # 属性 1，服务器的带宽
                comparedList[i][0] = selectedMEC[i].bandwidth
                # 属性 2，服务器的距离
                comparedList[i][1] = selectedDistance[i]
                # 属性 3，服务器的计算能力
                comparedList[i][2] = selectedMEC[i].computePower
                # 属性 4，服务器的平均等待时延
                comparedList[i][3] = selectedMEC[i].getAverageDelay()


            #当某个服务器的四个属性均不低于当前服务器的0.95 且 至少有一个属性大于当前服务器的1.2倍，则列为候选服务器
            #声明两个准则是否成立的标志
            flag = [0 for i in range(len(selectedMEC))]

            #开始两条准则的判断
            for m in range(len(comparedList)):
                if m == index:
                    continue
                else:
                    if comparedList[m][0] >= 1.2 * comparedList[index][0] or \
                                    comparedList[m][1] >= 1.2 * comparedList[index][1] or \
                                    comparedList[m][2] >= 1.2 * comparedList[index][2] or \
                                    comparedList[m][3] >= 1.2 * comparedList[index][3]:
                        flag[m] = 1

                    elif comparedList[m][0] >= 0.95 * comparedList[index][0] and \
                                    comparedList[m][1] >= 0.95 * comparedList[index][1] and \
                                    comparedList[m][2] >= 0.95 * comparedList[index][2] and \
                                    comparedList[m][3] >= 0.95 * comparedList[index][3]:
                        flag[m] = 1

            print("当前候选服务器状态为" + str(flag))

            candidateMEC = []

            if sum(flag) == 0:
                print("当前没有可候选服务器")
                return False
            elif sum(flag) > 0:
                for k in range(len(flag)):
                    if flag[k] == 1:
                        candidateMEC.append(selectedMEC[k])
                print("当前有可候选服务器")
                #将候选列表返回
                return candidateMEC


    #####################################################################################################################

    # 卸载决策，调用层次分析法求解当前时刻的时延因子和能耗因子，并求出效益值，最后确定当前任务是否卸载
    def offload_Decision(self,WBAN,MECList,Globalmap):

        # 对于每一个任务的两个因子
        factorList = []

        delayMEC = Globalmap.get_value('delayAverage')
        time = Globalmap.get_value('clocktime')

        # 计算出每一个优先级任务的因子组
        for i in range(len(WBAN.taskList)):

            #获取三个属性
            taskChar = WBAN.taskList[i].priority + 1     #任务优先级
            userChar = WBAN.priority                     #用户优先级
            energyChar = WBAN.energy / WBAN.energyTrue        #设备电量

            # 三个属性之间的关系矩阵
            matrixOfThree = [[1, 1, 2 / 3], [1, 1, 2 / 3], [3 / 2, 3 / 2, 1]]
            AHP1 = AHP(matrixOfThree)

            # 任务优先级对因子的影响矩阵
            matrixOfTask = [ [1,taskChar] , [1/taskChar,1] ]
            AHP2 = AHP(matrixOfTask)

            # 用户优先级对因子的影响矩阵
            matrixOfUser = [ [1,userChar] , [1/userChar,1] ]
            AHP3 = AHP(matrixOfUser)

            # 设备剩余电量对因子的影响矩阵
            matrixOfEnergy = [ [1,energyChar] , [1/energyChar,1] ]
            AHP4 = AHP(matrixOfEnergy)

            # 计算三个属性的权重
            weightThree = AHP1.normailze_Vector(matrixOfThree)
            # 计算三个属性的独立权重
            weightTask = AHP2.normailze_Vector(matrixOfTask)
            weightUser = AHP3.normailze_Vector(matrixOfUser)
            weightEnergy = AHP4.normailze_Vector(matrixOfEnergy)
            weightFactor = [ weightTask,weightUser,weightEnergy ]
            # print("属性权重"+str(weightFactor))

            #两个矩阵相乘得到时延因子和能耗因子
            Factor = np.dot(weightThree,weightFactor)
            Factor = list(Factor)
            # timeFactor = Factor[0]      #时延因子
            # energyFactor = Factor[1]    #能耗因子
            factorList.append(Factor)

        print(factorList)


        #获取当前连接的服务器
        index = WBAN.server - 1
        targetMEC = MECList[index]

        # 获取本地排队时延和服务器排队时延
        res1 = WBAN.getQueueDelay()
        delayQueueLocal = res1[0]                       #本地执行排队时延
        delayQueueTran = res1[1]                        #发送排队时延
        delayQueueMEC = targetMEC.getAverageDelay()     #服务器平均排队时延

        for i in range(len(WBAN.taskList)):

            indexPlus = WBAN.taskList[i].priorityTrue

            # 获取与当前任务优先级对应的因子组
            timeFactor = factorList[i][0]     #时延因子
            energyFactor = factorList[i][1]    #能耗因子

            # 计算本地处理时延和能耗
            WBAN.taskList[i].set_Local_Task()
            # 计算发送时延和能耗
            WBAN.taskList[i].set_Transmit_Task(WBAN.distance)
            # 计算服务器处理时延和能耗
            WBAN.taskList[i].set_MEC_Task(targetMEC.computePower)

            #计算本地执行时延和能耗
            delayLocal = WBAN.taskList[i].timeLocal + delayQueueLocal   #本地执行时延和排队时延
            energyLocal = WBAN.taskList[i].energyLocal                  #本地执行能耗
            benefitLocal = timeFactor * delayLocal + energyFactor * energyLocal

            # 计算卸载处理时延和能耗
            # 发送时延 + 发送排队时延 + 服务器排队时延 + 服务器执行时延
            delayOffload = WBAN.taskList[i].timeTransmit + delayMEC[1][indexPlus] + WBAN.taskList[i].timeMEC + delayQueueTran
            energyOffload = WBAN.taskList[i].energyTransmit     #发送能耗
            benefitOffload = timeFactor*delayOffload + energyFactor*energyOffload

            benefitLocal = benefitLocal
            benefitOffload = benefitOffload

            #判断是否要卸载
            if benefitLocal > benefitOffload:
                WBAN.taskList[i].ifOffload = 1
                WBAN.taskList[i].timeInto = time
                WBAN.transmitBuffer.append(WBAN.taskList[i])

            elif benefitLocal <= benefitOffload:
                WBAN.taskList[i].ifOffload = 0
                WBAN.taskList[i].timeInto = time
                WBAN.executionBuffer.append(WBAN.taskList[i])

        WBAN.taskList = []


    #####################################################################################################################

    # 多属性迁移决策，使用层次分析法确定是否迁移并且迁移到哪一个服务器
    def migration_Decision(self,WBAN,candidateMEC):
        # 候选服务器的个数
        row = len(candidateMEC)
        # 获取当前WBAN连接的服务器
        numNow = WBAN.server

        # 每个服务器有三个属性：计算能力，时延，距离，三个属性的判断举证
        matrixFour = [ [1, 1/5, 1/3  ],
                       [5, 1,   5/3  ],
                       [3, 3/5, 1    ] ]

        # 候选服务器的三个属性的实际数值列表
        dataList = [ [-1]*3 for i in range(len(candidateMEC)) ]

        #计算每个候选服务器与本WBAN的距离
        x_WABN = WBAN.coordinate[0]
        y_WBAN = WBAN.coordinate[1]

        for i in range(len(candidateMEC)):
            #获取某个服务器的横纵坐标
            x_MEC = candidateMEC[i].coordinate[0]
            y_MEC = candidateMEC[i].coordinate[1]

            #计算距离
            distance = (abs(x_MEC-x_WABN)**2 + abs(y_MEC-y_WBAN)**2 )**0.5
            dataList[i][2] = distance

            #获取服务器的平均等待时延
            delay = candidateMEC[i].getAverageDelay()
            if delay == 0:
                dataList[i][1] = 1*pow(10,-6)
            else:
                dataList[i][1] = delay

            #服务器的计算能力
            dataList[i][0] = candidateMEC[i].computePower / pow(10,9)

        #print([x[1] for x in dataList])
        #服务器计算能力之于其权重的影响矩阵
        matrixOfCompute = [ [-1]*row for i in range(row) ]
        for i in range(len(matrixOfCompute)):
            for j in range(len(matrixOfCompute[i])):
                A = abs( dataList[i][0]-dataList[j][0] ) + 1
                if dataList[i][0]-dataList[j][0] > 0:
                    matrixOfCompute[i][j] = round(A, 10)
                    matrixOfCompute[j][i] = round(1/A, 10)
                elif dataList[i][0]-dataList[j][0] <= 0:
                    matrixOfCompute[i][j] = round(1 / A, 10)
                    matrixOfCompute[j][i] = round(A, 10)


        #服务器排队时延之于其权重的影响矩阵
        matrixOfDelay = [ [-1]*row for i in range(row) ]
        for i in range(len(matrixOfDelay)):
            for j in range(len(matrixOfDelay[i])):
                A = dataList[i][1] / dataList[j][1]
                matrixOfDelay[i][j] = round(1/A,10)
                matrixOfDelay[j][i] = round(A,10)


        #服务器距离之于其权重的影响矩阵
        matrixOfDistance = [ [-1]*row for i in range(row) ]
        for i in range(len(matrixOfDistance)):
            for j in range(len(matrixOfDistance[i])):
                A = dataList[i][2] / dataList[j][2]
                matrixOfDistance[i][j] = round(1/A,10)
                matrixOfDistance[j][i] = round(A,10)


        #调用层次分析法
        AHP0 = AHP(matrixFour)
        AHP2 = AHP(matrixOfCompute)
        AHP3 = AHP(matrixOfDelay)
        AHP4 = AHP(matrixOfDistance)

        #四属性权重
        weightFour = AHP0.normailze_Vector(matrixFour)
        #各属性对服务器权重
        weightCompute = AHP2.normailze_Vector(matrixOfCompute)
        weightDelay = AHP3.normailze_Vector(matrixOfDelay)
        weightDistance = AHP4.normailze_Vector(matrixOfDistance)

        weightProperty = [weightCompute,weightDelay,weightDistance]

        #计算服务器权重
        weightOfMEC = np.dot(weightFour,weightProperty)

        #通过权重返回最优的服务器
        weightOfMEC = list(weightOfMEC)
        indexOfBest = weightOfMEC.index(max(weightOfMEC))

        #indexOfBest = weightCompute.index(max(weightCompute))
        #indexOfBest = weightDelay.index(max(weightDelay))
        #indexOfBest = weightDistance.index(max(weightDistance))

        bestMEC = candidateMEC[indexOfBest]

        return bestMEC.number

    #####################################################################################################################

    #任务迁移函数，当用户迁移完成后，将原服务器未完成的任务迁移到新的服务器中继续排队
    def task_Migration(self,WBAN,MECFrom,MECTo):

        # 比较两个服务器的编号是否一样
        numberFrom = MECFrom.number
        numberTo = MECTo.number

        #获取用户的编号
        numberWBAN = WBAN.number

        #迁移任务序列
        migrationList = []

        #计算两个服务器的距离
        x_1 = MECFrom.coordinate[0]
        y_1 = MECFrom.coordinate[1]
        x_2 = MECTo.coordinate[0]
        y_2 = MECTo.coordinate[1]
        distanceBetween = ( abs(x_1-x_2)**2 + abs(y_1-y_2)**2 ) * 0.5

        # 获取服务器之间的传输速率
        migrationSpeed = [
            [1.0, 9.1, 8.2, 8.2, 9.4, 6.4, 10.0],
            [9.1, 1.0, 7.9, 9.4, 9.1, 6.7, 8.5],
            [8.2, 7.9, 1.0, 9.7, 6.4, 9.7, 9.7],
            [8.2, 9.4, 9.7, 1.0, 7.3, 9.1, 8.8],
            [9.4, 9.1, 6.4, 7.3, 1.0, 4.9, 7.9],
            [6.4, 6.7, 9.7, 9.1, 4.9, 1.0, 7.6],
            [10.0, 8.5, 9.7, 8.8, 7.9, 7.6, 1.0]
        ]

        if numberFrom == numberTo:
            return 0

        elif numberFrom != numberTo:
            #遍历原服务器的排队队列
            for i in range(len(MECFrom.executionBuffer)):

                if len(MECFrom.executionBuffer[i]) <= 1:
                    continue

                elif len(MECFrom.executionBuffer[i]) > 1:

                    for j in range(1, len(MECFrom.executionBuffer[i])):

                        #  判断该任务是否属于移动用户且没有完成
                        if MECFrom.executionBuffer[i][j].numOfWBAN == numberWBAN and MECFrom.executionBuffer[i][j].finish == False:

                            # 剥离该任务,计算迁移时延并将该时延算入排队时延
                            MECFrom.executionBuffer[i][j].timeWait += MECFrom.executionBuffer[i][j].dataSize / (10*pow(10,8))
                            MECFrom.executionBuffer[i][j].migrateDistance += distanceBetween
                            migrationList.append(MECFrom.executionBuffer[i][j])
                            MECFrom.executionBuffer[i][j].available = False

                        else:
                            continue

                # 将失效的任务从等待队列中删除
                MECFrom.executionBuffer[i] = \
                    [MECFrom.executionBuffer[i][k] for k in range(len(MECFrom.executionBuffer[i])) if MECFrom.executionBuffer[i][k].numOfWBAN != numberWBAN]


            # 将待迁移任务列表按照当前的优先级进行排序
            migrationList = sorted(migrationList, key=operator.attrgetter('priority'))
            migrationList = list(reversed(migrationList))

            # 将这些任务送入新的服务器的排队队列
            for l in range(len(migrationList)):

                # 获取队列最短的队列的索引
                choice = min(MECTo.sizeOfBuffer)
                index = MECTo.sizeOfBuffer.index(choice)

                # 重新计算该任务的服务器处理时延
                migrationList[l].set_MEC_Task(MECTo.computePower)

                # 送入缓冲区
                MECTo.executionBuffer[index].append(migrationList[l])
                MECTo.sizeOfBuffer[index] += migrationList[l].dataSize


    #####################################################################################################################

    #更新平均排队时延
    def updateAverageDelay(self,Globalmap):

        #获取完成列表     平均排队时延列表
        finishBuffer = Globalmap.get_value('finishBuffer')
        delayMEC = [[0 for i in range(8)] for j in range(2)]
        numOfPriority = [[0 for i in range(8)] for j in range(2)]
        time = Globalmap.get_value('clocktime')

        # finishBuffer = [ finishBuffer[i] for i in range(len(finishBuffer)) if finishBuffer[i].timeslice == (time+10-1000000)  ]
        local = [ finishBuffer[i] for i in range(len(finishBuffer)) if finishBuffer[i].ifOffload == 0  ]
        offload = [finishBuffer[i] for i in range(len(finishBuffer)) if finishBuffer[i].ifOffload == 1]

        for i in range(len(local)):
            index = local[i].priorityTrue
            delayMEC[0][index] += local[i].timeWait
            numOfPriority[0][index] += 1

        for j in range(len(offload)):
            index = offload[j].priorityTrue
            delayMEC[1][index] += offload[j].waitInMEC
            numOfPriority[1][index] += 1

        for i in range(len(delayMEC)):
            for j in range(len(delayMEC[i])):
                if numOfPriority[i][j] >0:
                    delayMEC[i][j] /= numOfPriority[i][j]

        Globalmap.set_value('delayMEC',delayMEC)
        #print(delayMEC)
        #print(len(finishBuffer))












#*************************************************************************************************************************************************#
#*************************************************************************************************************************************************#
#*************************************************************************************************************************************************#
#*************************************************************************************************************************************************#

#层次分析法，采用特征值法求解
class AHP(object):

    def __init__(self, array):          # array是每个指标下面对应的判断矩阵，即原始数据
        self.row = len(array)           # 计算矩阵的行数
        self.col = len(array[0])        # 计算矩阵的列数

    #计算矩阵的最大特征值和对应的特征向量
    def get_Eigen(self,array):

        #使用numpy包计算特征值和特征向量
        eigenValue,eigenVector = np.linalg.eig(array)
        #print("特征值为：" + str(eigenValue))
        #print("特征向量为：" + str(eigenVector))
        #将特征值转化成列表
        listValue = list(eigenValue)

        #获取最大特征值及对应的特征向量
        max_Value = max(listValue)
        index = listValue.index(max_Value)
        max_Vector = eigenVector[:,index]
        #print("最大特征值：" + str(max_Value) + "对应特征向量为：" + str(max_Vector))

        return [max_Value,max_Vector]

    #建立RI矩阵,n是矩阵阶数
    def RImatrix(self,n):

        #  建立平均随机一致性指标R.I
        RI_dict = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

        # 获取对应的RI值
        return RI_dict[n]

    #一致性检验
    def consistence_Test(self,array):

        #计算CI = (最大特征值 - 阶数) / (阶数 - 1)
        res = self.get_Eigen(array)
        max_Value = res[0]              #最大特征值
        CI = (max_Value - self.row) / (self.row - 1)

        #获取RI值
        RI = self.RImatrix(self.row)

        #计算CR
        CR = CI / RI
        if CR < 0.10:
            # print("通过一致性检验")
            return True
        else:
            # print("未通过一致性检验")
            return False

    #特征向量归一化
    def normailze_Vector(self,array):

        vector_After = []
        res = self.get_Eigen(array)
        max_Vector = res[1]

        #求特征向量的每一个元素的和
        sumOfVector = sum(max_Vector)
        #将每一个元素归一化
        for i in range(len(max_Vector)):
            vector_After.append( max_Vector[i] / sumOfVector )

        #将该层指标的权重返回
        vector_After = map(float,vector_After)
        vector_After = list(vector_After)
        #保留五位小数
        for z in range(len(vector_After)):
            vector_After[z] = round(vector_After[z],6)
        return vector_After


#*************************************************************************************************************************************************#
#*************************************************************************************************************************************************#
#*************************************************************************************************************************************************#
#*************************************************************************************************************************************************#


































