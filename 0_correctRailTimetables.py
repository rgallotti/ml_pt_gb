"""------------------------------------------------------------------------------"""
""" AUTHOR:  Riccardo Gallotti (rgallotti@gmail.com)                             """
""" VERSION: 1.0                                                                 """
"""------------------------------------------------------------------------------"""

#Correct the Rail timetables from the '0000000' error. Produce a corrected copy
#of the timetable in the original .CIF format, used in 1_stops.py

"""------------------------------------------------------------------------------"""
""" PARAMETERS                                                                   """
"""------------------------------------------------------------------------------"""

#NONE

"""------------------------------------------------------------------------------"""
""" IMPORT                                                                       """
"""------------------------------------------------------------------------------"""

import numpy as np

"""------------------------------------------------------------------------------"""
""" FILE PATHS                                                                   """
"""------------------------------------------------------------------------------"""

NPTDRTimetablesPath = '/Users/rgallott/Work/PlexMath/Unzipped/'

"""------------------------------------------------------------------------------"""
""" CLASSES                                                                      """
"""------------------------------------------------------------------------------"""

class mySquareMatrix(object):
    def __init__(self,dimension):
        self.values = []
        for i in range(dimension):
            v = []
            for j in range(dimension):
                v.append(0)
            self.values.append(v)

"""------------------------------------------------------------------------------"""
""" FUNCTIONS                                                                    """
"""------------------------------------------------------------------------------"""

def minFromH(h):
    return 60*int(h[:2:])+int(h[2::])

def hFromMin(min):
    h = min/60
    if h >=24: h-=24
    if h == 0: hs = '00'
    elif h < 10: hs = '0'+str(h)
    else: hs = str(h)
    m = min%60
    if m == 0: ms = '00'
    elif m < 10: ms = '0'+str(m)
    else: ms = str(m)
    
    hP = hs+ms
    if hP == '2400': h = '0000'
    if int(hP) >= 2400:
        print 'Minute over the day margin '+str(min),hP
    
    return hP

"""------------------------------------------------------------------------------"""
""" MAIN                                                                         """
"""------------------------------------------------------------------------------"""

fileName = 'NATIONAL_RAIL_ATCORAIL'#451 CORRECTIONS IN 2010 DATA

readpath  = NPTDRTimetablesPath+'Timetables/'+fileName+'.CIF'
writepath = NPTDRTimetablesPath+'Timetables/'+fileName+'_corrected.CIF'


""" Identify missing trips (includes all suspects)"""
print "IDENTIFY MISSING"
MT = {}
with open(readpath,"r") as timetableData:
    rdr= iter(timetableData) #Iterator
    rdr.next() #Skips First Line
    missingLast = False
    aBuffer = []
    for line in rdr:
        head = line[:2:]
        atcocode = line[2:14:].strip()
        
        if head == 'QO':
            lastID = atcocode

        elif head =='QI':
            missingThis = line[14:22:] == '00000000'
            if missingLast or missingThis:
                ori = MT.get(lastID,'NotIndexed')
                if ori =='NotIndexed':
                    MT[lastID] = set([atcocode])
                else:
                    ori.add(atcocode)
            lastID = atcocode
            missingLast =  missingThis

        elif head =='QT':
            if missingLast:
                ori = MT.get(lastID,'NotIndexed')
                if ori =='NotIndexed':
                    MT[lastID] = set([atcocode])
                else:
                    ori.add(atcocode)


"""Incicize Suspects"""
print "INDICIZE SUSPECTS"

#Assuming QI and QT not wrong,

stopDictionary = {}
idn = 0
for ori in MT.keys():
    stopDictionary[ori] = idn
    idn+=1

for desSet in MT.values():
    for des in list(desSet):
        index = stopDictionary.get(des,'NotIndexed')
        if index == 'NotIndexed':
            stopDictionary[des] = idn
            idn+=1

dimension =  len(stopDictionary)

isError =  np.zeros([dimension,dimension])

for ori,v in MT.items():
    for des in list(v):
        oN = stopDictionary[ori]
        dN = stopDictionary[des]
        isError[oN][dN] =  1
        isError[dN][oN] =  1 #I try not to symmterize and see if I have enough info

"""CALCULATE TRAVELTIMES"""
print "CALCULATE TRAVELTIMES"

times  = np.zeros([dimension,dimension])
ntrips = np.zeros([dimension,dimension])

with open(readpath,"r") as timetableData:
    rdr= iter(timetableData) #Iterator
    rdr.next() #Skips First Line
    for line in rdr:
        head = line[:2:]
        if head == 'QO':
            aBuffer = []
            aBuffer.append(line)
        elif head =='QI':
            aBuffer.append(line)
        elif head =='QT':
            aBuffer.append(line)

            for l1 in range(len(aBuffer)-1):
                l2 = l1+1
                i1 = stopDictionary.get(aBuffer[l1][2:14:].strip(),'NotIndexed')
                i2 = stopDictionary.get(aBuffer[l2][2:14:].strip(),'NotIndexed')

                if i1 != 'NotIndexed' and i2 != 'NotIndexed':
                    if isError[i1][i2]:
                        if aBuffer[l1][14:22:] != '00000000' and aBuffer[l2][14:22:] != '00000000':
                            if l1 == 0 or aBuffer[l1][18:22:] == '0000':
                                t1 = aBuffer[l1][14:18:]
                            else:
                                t1 = aBuffer[l1][18:22:]
                            if aBuffer[l2][14:18:] == '0000' and l2 != len(aBuffer)-1:
                                t2 = aBuffer[l2][18:22:]
                            else:
                                t2 = aBuffer[l2][14:18:]
                            
                            if t2 > t1:
                                times[i1][i2]+=minFromH(t2) - minFromH(t1)
                                ntrips[i1][i2]+=1

for i in range(dimension):
    for j in range(dimension):
        if ntrips[i][j] > 0:
            times[i][j]/=float(ntrips[i][j])
        else:
            times[i][j] = -1


a,b = np.nonzero(isError)


""" Identify and correct errors """
print "CORRECT ERRORS"

#Assuming QI and QT not wrong,

#Use traveltimes if consistent and present
#If not: interpolate
outputFile = open(writepath,'w')
correctionsDone = 0
toPrint = False
with open(readpath,"r") as timetableData:
    
    rdr= iter(timetableData) #Iterator
    for line in rdr:

        head = line[:2:]
        if head == 'QO':
            aBuffer = []
            suspectList = []
            aBuffer.append(line)
            ind = 0
        
        
        elif head =='QI':
            aBuffer.append(line)
            ind+=1
            if line[14:22:] == '00000000':
                suspectList.append(ind)
        
        elif head =='QT':
            aBuffer.append(line)
            outBuffer = list(aBuffer)
            for susp in suspectList:
                i0 = 1
                i2 = 1
                while susp - i0 in suspectList:
                    i0+=1
                while susp + i2 in suspectList:
                    i2+=1
                if susp-i0 > 0:
                    t0 = aBuffer[susp-i0][18:22:]
                    if t0 == '0000':
                        t0 = aBuffer[susp-i0][14:18:]
                else:
                    t0 = aBuffer[susp-i0][14:18:]
                
                if susp+i2 < len(aBuffer)-1:
                    t2 = aBuffer[susp+i2][14:18:]
                    if t2 == '0000':
                        t2 = aBuffer[susp+i2][14:18:]
                else:
                    t2 = aBuffer[susp+i2][14:18:]
                
                if minFromH(t0) <= minFromH(t2) or i0+i2 > 2:
                    #Error
                    intTimes = []
                    missingTime = False
                    for i in range(susp - i0,susp + i2):
                        j = i+1
                        indI = stopDictionary[aBuffer[i][2:14:].strip()]
                        indJ = stopDictionary[aBuffer[j][2:14:].strip()]
                        IJtime = times[indI][indJ]
                        if IJtime >= 0:
                            intTimes.append(IJtime)
                        else:
                            intTimes = [1]*(i0+i2) #If I do not know all times

                            break
                        
                    totT = minFromH(t2)-minFromH(t0)
                    if totT < 0:
                        if i0+i2 > 2:
                            totT+=1440
                        else:
                            print "I DID A MESS"
                        
                    scaleTimes = [float(t)/sum(intTimes)*totT for t in intTimes]
                    
                    tPass = minFromH(t0)
                    for enI,i in enumerate(range(susp - i0+1,susp + i2)):
                        #is time bad? recheck
                        if aBuffer[i][14:22:] != '00000000':
                            print "WRONG"
                        else:
                            tPass+=scaleTimes[enI]
                            outBuffer[i] = aBuffer[i][:14:] + hFromMin(int(round(tPass)))+hFromMin(int(round(tPass)))+aBuffer[i][22::]
                            toPrint =  True
                            correctionsDone+=1

            outputFile.write(''.join(outBuffer))
            if toPrint:
                print ''.join(aBuffer) ,''.join(outBuffer)
            toPrint = False
        else:
            outputFile.write(line)



print "NUMBER OF CORRECTIONS DONE: " +str(correctionsDone)


outputFile.close()
