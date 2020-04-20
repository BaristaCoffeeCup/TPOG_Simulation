from Task_Create import Task
from WBAN_Create import WBAN
from MECserver_create import MEC
from config import Globalmap
from Algorithm_System import AS
from Algorithm_System import AHP

import math
import operator
import random
import copy
import numpy as np
import datetime


# 生成需要调用的句柄
Globalmap = Globalmap()     #全局变量句柄
Globalmap._init_()
AS = AS()                   #系统算法句柄


# 布置服务器
MEC1  = MEC(1,  [1316,93],   412.5, 3*math.pow(10,9)  )
MEC2  = MEC(2,  [1025,1293], 460.0, 4*math.pow(10,9)  )
MEC3  = MEC(3,  [1985,374],  475,   7*math.pow(10,9)  )
MEC4  = MEC(4,  [1946,1353], 562.5, 8*math.pow(10,9)  )
MEC5  = MEC(5,  [464,398],   570,   5*math.pow(10,9)  )
MEC6  = MEC(6,  [1191,1184], 570,   6*math.pow(10,9)  )

MECList = [MEC1, MEC2, MEC3, MEC4, MEC5,MEC6]


# 设置用户的移动速度为5米每秒    #####此处设置用户的移动速度，最后一个参数
WBAN_A = WBAN(1, 1, 1000, [750, 820], 20)

# 在固定周期生成用户
numOfUser = [30,40,50,80,70,60]
for i in range(len(MECList)):
    MECList[i].add_WBAN(30)     #####此处调整服务器范围内的用户数量

# 确定程序停止时间，
timeFinish = 60*pow(10,6)

time1 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

compare = []
check = []

# 系统运作循环
while 1:

    # 获取当前系统时钟
    timeSystem = Globalmap.get_value("clocktime")

    numOfAdd = [1,2,5,6,3,4]
    #每五秒增加一个用户
    if timeSystem % (5*pow(10,6)) == 0:
        for i in range(len(MECList)):
            MECList[i].add_WBAN(numOfAdd[i])


    # 目标用户更新坐标
    WBAN_A.check_Coordinate(Globalmap, MECList[WBAN_A.server - 1].coordinate)


    # 这一句是层次分析法选择最优服务器
    serverNow = WBAN_A.server
    ans = AS.migration_Decision(WBAN_A, MECList)
    #print("最优服务器：" + str(ans))
    if timeSystem == 0 or timeSystem % 1000 == 0:
        if WBAN_A.server == 0:
            WBAN_A.server = ans
            MECList[WBAN_A.server - 1].WBANList.insert(0, WBAN_A)

        else:
            if WBAN_A.server == ans:
                pass
            elif WBAN_A.server != ans:
                # 离开原来的服务器用户名单
                MECList[WBAN_A.server - 1].WBANList.remove(WBAN_A)
                # 加入新的服务器用户名单
                WBAN_A.server = ans
                MECList[WBAN_A.server - 1].WBANList.insert(0, WBAN_A)





    # ***************************************************************************************

    #WBAN生成任务，执行任务
    for h in range(len(MECList)):

        for k in range(len(MECList[h].WBANList)):

            if (timeSystem % 1000000 == 0 or timeSystem == 0) and timeSystem < 60*pow(10,6):                #####这里设置数据到达率

                MECList[h].WBANList[k].add_Task_List(6, Globalmap)
                #AS.offload_Decision(MECList[h].WBANList[k],MECList,Globalmap)
                MECList[h].WBANList[k].buffer_Allocation(Globalmap)

            elif timeSystem % 1000 == 0:
                MECList[h].WBANList[k].checkBufferAvailable(Globalmap)


            MECList[h].WBANList[k].task_execution(Globalmap)



    #发送任务
    for j in range(len(MECList)):

        #接收任务
        MECList[j].receive_Task(Globalmap)

        #分送任务
        MECList[j].buffer_Allocation(Globalmap)

        #执行任务
        MECList[j].MEC_TaskExecution(Globalmap)

        #服务器删除失效任务
        MECList[j].checkBufferAvailable(Globalmap)


    if  timeSystem % 1000000 == 999990:
        AS.updateAverageDelay(Globalmap)


    timeSystem += 10
    Globalmap.set_value('clocktime', timeSystem)
    print("当前时间为：" + str(timeSystem))
    #print(WBAN_A.server)

    if timeSystem == timeFinish:
        print("用户已经完成移动")
        break



###########################################################################################################################


un = Globalmap.get_value('finishBuffer')
an = Globalmap.get_value('unavailableBuffer')

un = [ un[i] for i in range(len(un)) if un[i].numOfWBAN == 1 ]
an = [ an[i] for i in range(len(an)) if an[i].numOfWBAN == 1 ]



un.extend(an)
#计算总时延和总能耗，用于前两张图
delay = 0
energy = 0

#计算时延和能耗
for k in range(len(un)):
    delay += (1-un[k].ifOffload)*un[k].timeLocal + un[k].ifOffload*(un[k].timeTransmit + un[k].timeMEC)  + un[k].timeWait
    energy += (1-un[k].ifOffload)*un[k].energyLocal + un[k].ifOffload*un[k].energyTransmit


WBAN_A.printFinishBuffer(un,an)

print("总能耗为："+str(delay))
print("平均时延为："+str(delay / len(un)))
print("平均能耗为："+str(energy / len(un)))


time2 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(str(time1))
print(str(time2))


#计算单个任务的时延和能耗
waitPer = [ 0 for i in range(8)]
energyPer = [ 0 for i in range(8)]
delayPer = [ 0 for i in range(8)]
numTask = [ 0 for i in range(8)]
for i in range(len(un)):
    index = un[i].priorityTrue
    if un[i].available == True:
        delayPer[index] += (1-un[i].ifOffload)*un[i].timeLocal + un[i].ifOffload*(un[i].timeTransmit + un[i].timeMEC) + un[i].timeWait
        waitPer[index] += un[i].timeWait
        energyPer[index] += (1-un[i].ifOffload)*un[i].energyLocal + un[i].ifOffload*un[i].energyTransmit
        numTask[index] += 1
    elif un[i].available == False:
        delayPer[index] += 10*pow(10,-3)


for i in range(len(energyPer)):
    if numTask[i] == 0:
        energyPer[i] = 0
        delayPer[i] = 10*pow(10,-3)
        waitPer[i] = 0
    else:
        energyPer[i] = energyPer[i] / numTask[i]
        delayPer[i] = delayPer[i] / (len(un)/8)
        waitPer[i] = waitPer[i] / numTask[i]


print("各优先级任务的平均排队时延如下：")
print(waitPer)
print("各优先级任务的平均完成时延如下：")
print(delayPer)
print("各优先级任务的平均能耗如下：")
print(energyPer)

print("完成任务数：")
print(len(un))
print("各优先级生成任务数：")
print(WBAN_A.numOfTask)
print("各优先级完成任务数：")
print(numTask)

































