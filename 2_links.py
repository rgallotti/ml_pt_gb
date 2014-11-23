"""------------------------------------------------------------------------------"""
""" AUTHOR:  Riccardo Gallotti (rgallotti@gmail.com)                             """
""" VERSION: 1.0                                                                 """
"""------------------------------------------------------------------------------"""

#Sort and rewrite the events list, compute the minimal traveltime for all edges.
#Produce a second version of the events list and a intra-layer edges list, 
#used in 3_finalformat.py

"""------------------------------------------------------------------------------"""
""" PARAMETERS                                                                   """
"""------------------------------------------------------------------------------"""

#NONE

"""------------------------------------------------------------------------------"""
""" IMPORT                                                                       """
"""------------------------------------------------------------------------------"""

from os import system
import time, csv
import numpy as np


"""------------------------------------------------------------------------------"""
""" FILE PATHS                                                                   """
"""------------------------------------------------------------------------------"""

outputPath = '/Users/rgallott/Work/PlexMath/Output/'

"""------------------------------------------------------------------------------"""
""" CLASSES                                                                      """
"""------------------------------------------------------------------------------"""
class links(object):
    def __init__(self,row):
        self.assign(row)

    def assign(self,row):
        self.oriID = row[0].strip()
        self.desID = row[1].strip()
        oT = int(row[2])
        dT = int(row[3])
        self.n = 1
        self.minT = dT-oT
        self.oTdT = [[oT,dT]]
     
    def addRow(self,row):

        oT = int(row[2])
        dT = int(row[3])
        self.n += 1
        if (dT-oT < self.minT): #t is minimal traveltime
            self.minT = dT-oT
        if (dT-oT < 0 and dT%1440):
            print row
        self.oTdT.append([oT,dT])


    def calculateAndPrint(self,writeAll,writeTopology):
        self.oTdT = sorted(self.oTdT, key=lambda x: x[0])

        writeAll.write("%7s"%self.oriID+",%7s"%self.desID+",%6d"%self.minT+",%4d\n"%self.n)
        writeTopology.write("%7s"%self.oriID+",%7s"%self.desID+",%6d"%self.minT+",%4d\n"%self.n)
        for l in self.oTdT:
            writeAll.write("%d,%d\n"%(l[0],l[1]))


"""------------------------------------------------------------------------------"""
""" FUNCTIONS                                                                    """
"""------------------------------------------------------------------------------"""

def doOneMode(modeletter):

    #Define Program Quantities

    #Read Stops
    linkData = open(outputPath+'temp/link'+modeletter+'sort.csv','r')
    linksTimeData = open(outputPath+'time_links'+modeletter+'.csv','w')
    linksTopologyData = open(outputPath+'topo_links.csv',"a")

    csvreader = csv.reader(linkData, delimiter=',')

    first = True
    for ind,row in enumerate(csvreader):
        oriID = row[0].strip()
        desID = row[1].strip()
        if first:
            aLinks = links(row)
            first = False
            continue
        if oriID == aLinks.oriID and desID == aLinks.desID:
            aLinks.addRow(row)
        else:
            aLinks.calculateAndPrint(linksTimeData,linksTopologyData)
            aLinks.assign(row)

    linkData.close()

    global passTime
    endTime = time.time()
    print "--------------------\n"+modeletter+": Write link data: %5.2f seconds\n--------------------\n"%(endTime-passTime)
    passTime =  endTime



    

"""------------------------------------------------------------------------------"""
""" MAIN                                                                         """
"""------------------------------------------------------------------------------"""
startTime = time.time()
passTime = startTime

#Starts on an empty file
system("rm "+outputPath+"topo_links.csv")

#Sort the temporal link information using the system sort command. 
#The output is sorted by 1)Origin 2)Destination 3)Departure Time 4)Arrival time
system("sort -g "+outputPath+"temp/linkF.csv > "+outputPath+"temp/linkFsort.csv")
system("sort -g "+outputPath+"temp/linkR.csv > "+outputPath+"temp/linkRsort.csv")
system("sort -g "+outputPath+"temp/linkM.csv > "+outputPath+"temp/linkMsort.csv")
system("sort -g "+outputPath+"temp/linkC.csv > "+outputPath+"temp/linkCsort.csv")
system("sort -g "+outputPath+"temp/linkA.csv > "+outputPath+"temp/linkAsort.csv")

endTime = time.time()
print "--------------------\nSort Small Things: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

#Using the sorted files we create the link files
doOneMode('F')
doOneMode('R')
doOneMode('M')
doOneMode('C')
doOneMode('A')


#Same for the bus layer (takes the largest fraction of time)
system("sort -g "+outputPath+"temp/linkB.csv > "+outputPath+"temp/linkBsort.csv")

endTime = time.time()
print "--------------------\nSort Bus: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

doOneMode('B')
endTime = time.time()
print "--------------------\nEND: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime