"""------------------------------------------------------------------------------"""
""" AUTHOR:  Riccardo Gallotti (rgallotti@gmail.com)                             """
""" VERSION: 1.0                                                                 """
"""------------------------------------------------------------------------------"""

#Recognize active stops, perform the stops' coarse graining, associate nodes with
#areacode, corrects inconsistencies in all timetables, computes intra-layer
#distances. Produce a set of intermediate files (nodes list, events list, 
#intra-layer edges list) used in 2_links.py and 3_finalformat.py


"""------------------------------------------------------------------------------"""
""" PARAMETERS                                                                   """
"""------------------------------------------------------------------------------"""

wdL = 500   #Walking distance from a facility (as the center should be reasonable, d < wdL)
wdS = wdL/2 #Walking distance for a group of bus stops (d <= 2*wdS)


#HIERARCHY: A > R > F > M > C > B > T
rankDictionary = {'A':1,'R':2,'F':3,'M':4,'BC':5,'B':5,'C':5}

"""------------------------------------------------------------------------------"""
""" IMPORT                                                                       """
"""------------------------------------------------------------------------------"""

import numpy as np
from math import sqrt
import time, csv
from os import system


"""------------------------------------------------------------------------------"""
""" FILE PATHS                                                                   """
"""------------------------------------------------------------------------------"""


INNOVATAtimetablesPath = '/Users/rgallott/Dropbox/IPhT/PlexMath/AirportData/Timetables/'
NaPTANPath = '/Users/rgallott/Work/PlexMath/Unzipped/NaPTANcsv/'
NPTDRTimetablesPath = '/Users/rgallott/Work/PlexMath/Unzipped/Timetables/'
outputPath = '/Users/rgallott/Work/PlexMath/Output/'

system("mkdir "+outputPath+"temp")

"""------------------------------------------------------------------------------"""
""" CLASSES                                                                      """
"""------------------------------------------------------------------------------"""

class StopPoint(object):
        
    def __init__(self,row):
        #Definitions
        self.isActive = False #Inactive until we see if it is used
        self.group = []
        #Identifiers
        self.atcocode = row[0]
        self.natgazid = row[11]
        self.name = row[6]
        #Position
        self.easting = int(row[2])
        self.northing = int(row[3])
        self.lon = float(row[4])
        self.lat = float(row[5])
        #Area
        self.atcoarea = self.atcocode[:3:]
        smsnumber = row[23]
        self.smsarea = smsnumber[:3:]
        #Type
        self.type = row[17]
        if  self.type == 'BCE'  or self.type == 'BST' or self.type == 'BCQ' or self.type == 'BCS' or self.type == 'BCT':
            self.mode = 'BC'#Bus & Coach
        elif self.type == 'AIR' or self.type == 'GAT':
            self.mode = 'A' #Air
        elif self.type == 'FTD' or self.type == 'FER' or self.type == 'FBT':
            self.mode = 'F' #Ferry
        elif self.type == 'RSE' or self.type == 'RLY' or self.type == 'RPL':
            self.mode = 'R' #Rail
        elif self.type == 'TMU' or self.type == 'MET' or self.type == 'PLT':
            self.mode = 'M' #Metro & Tram
        elif self.type == 'LCE' or self.type == 'LCB' or self.type == 'LPL':
            self.mode = 'L' #Lift & Cable car
        elif self.type == 'TXR' or self.type == 'STR':
            self.mode = 'T' #Taxi
        else: 
            self.mode = 'ERROR'
            print "DATA ERROR: no mode identified for stop:",self.atcocode
        self.modes = set() #The modes identified by the timetables


class StopArea(object):
  
    def __init__(self,row):
        #Definitions
        self.stops = []
        self.children = []
        self.parent = []
        self.modes = set()
        self.isActive = True #Active until aggregated or seen as unused
        self.isCorrected = False

        #Identifiers
        self.id = row[0]
        self.name = row[1]
    
        #Position
        self.easting = int(row[4])
        self.northing = int(row[5])
        self.lon = float(row[6])
        self.lat = float(row[7])
        #Area
        self.atcoarea = self.id[:3:]
        #Characteristics
        self.type = row[2]
        if  self.type == 'GBCS' or self.type == 'GPBS' or self.type == 'GCLS' or self.type == 'GCCH':
            self.mode = 'BC'#Bus & Coach
        elif self.type == 'GAIR':
            self.mode = 'A' #Air
        elif self.type == 'GFTD':
            self.mode = 'F' #Ferry
        elif self.type == 'GRLS':
            self.mode = 'R' #Rail
        elif self.type == 'GTMU':
            self.mode = 'M' #Metro & Tram
        else:
            if row[3] == 'groupFromStop':
                self.mode = row[8]
            else:
                self.mode = 'ERROR'
                print "DATA ERROR: no mode identified for group:",self.id
        self.modesGroups = set([self.mode]) #The modes identified by the groups
        self.modes = set() #The modes identified by the timetables

        self.rank = 10000 #Placeholder for NULL


    def addStop(self,stop):
        self.stops.append(stop.atcocode)
        stop.group = self.id

    def addChild(self,group,stopsList,groupsList): #WARNING: the ordering of grouping should not matter
        if group.id != self.parent and group.id != self.id: #To avoid mirroring    
            if self.parent == []: 
                group.parent = self.id
                self.children.append(group.id)
                self.modesGroups.add(group.mode)
                self.stops += group.stops
                for stop in group.stops:
                    stopsList[stop].group = self.id
            else:
                group.parent = self.parent
                groupsList[self.parent].children.append(group.id)
                groupsList[self.parent].modesGroups.add(group.mode)
                groupsList[self.parent].stops += group.stops
                for stop in group.stops:
                    stopsList[stop].group = self.parent
            group.isActive = False

    def mergeWith(self,group,stopsList,groupsList):
        self.addChild(group,stopsList,groupsList)
        self.northing = (self.northing + group.northing)*0.5
        self.easting  = (self.easting  + group.easting )*0.5
        self.lat      = (self.lat + group.lat)*0.5
        self.lon      = (self.lon + group.lon)*0.5


    #GROUP OPERATIONS
    #------------------------------------
    def checkActivity(self,stopsList):
        if len(self.stops) == 0:
            self.isActive = False
            self.modes = set()
            self.radius = 0
        if len(self.stops) == 1:
            if stopsList[self.stops[0]].modes == set(['B']):
                stopsList[self.stops[0]].group = []
                self.stops = []
                self.isActive = False
                self.modes = set()
                self.radius = 0
            else:
                self.radius = 0

    def identifyModes(self,stopsList):
        self.modes = set()
        for stop in self.stops:
            self.modes = self.modes | stopsList[stop].modes
        if len(self.modes):
            self.rank = min([rankDictionary[x] for x in self.modes])
 
    def calculateSize(self,stopsList): #Calculate a size parameter for the cluster of points
        if len(self.stops) > 1:
            distQ = [( self.easting - stopsList[s].easting )**2 + ( self.northing - stopsList[s].northing )**2 for s in self.stops]
            self.radius = sqrt(np.max(distQ))
        elif (len(self.stops) < 1 or (len(self.stops) == 1 and self.modes == set(['B']) ) )and self.isActive:
            print "ERROR: group %s should be inactive"%self.id
        else: self.radius = 0

    def runGroupOperations(self,StopList):
        self.identifyModes(StopList)
        self.checkActivity(StopList)
        if self.isActive:
            self.calculateSize(StopList)

    #-----------------------------------------
    #Sometimes they are just placed at a wrong group point (i.e. north/east inversion)
    def correctCenter(self,stopsList,distance):
        n = [stopsList[stop].northing for stop in self.stops]
        e = [stopsList[stop].easting for stop in self.stops]
        
        if len(n) > 0 and len(e) > 0:        
            n0 =  np.mean(n)
            e0 =  np.mean(e)
            maxDSQ = 0
            for i in range(len(e)):
                dx = e[i]-e0
                dy = n[i]-n0
                dSQ = dx**2+dy**2
                if dSQ > maxDSQ:
                    maxDSQ = dSQ
            r = sqrt(maxDSQ)
            #if the correction is of an order of magnitude, always keep it
            if (self.radius > distance  and r <= distance) or r < self.radius*0.1: 
                self.radius = r
                #Like this we lose perfect correspondance between latlon and northeast
                self.lon = np.mean([stopsList[stop].lon for stop in self.stops])
                self.lat = np.mean([stopsList[stop].lat for stop in self.stops])
                self.northing = n0
                self.easting = e0
                self.isCorrected = True



    def removeBusStops(self,distance,stopsList):
        for ind,stop in enumerate(self.stops):
            if stopsList[stop].modes == set(['B']):
                dx = self.easting  - stopsList[stop].easting
                dy = self.northing - stopsList[stop].northing
                if dx**2+dy**2 > distance**2:
                    #Unassign group
                    stopsList[stop].group = []
                    #Remove from list
                    self.stops[ind] = '!'
                    self.isCorrected = True
        # remove all marked stops
        for i in range(0,self.stops.count('!')):
            self.stops.remove('!')




    def repairBusClusters(self,distance,stopsList):
        if len(self.stops) <= 1:
            print "ERROR: trying to correct a group of 1 or 0 bus stops"
        
        #Assuming that the cluster HAS to be corrected
        #Compute radius with new baricenter
        self.northing = np.mean([stopsList[s].northing for s in self.stops])
        self.easting  = np.mean([stopsList[s].easting  for s in self.stops])
        distQ = [( self.easting - stopsList[s].easting )**2 + ( self.northing - stopsList[s].northing )**2 for s in self.stops]
        self.radius = sqrt(np.max(distQ))

        while self.radius > distance and len(self.stops) > 2:
            #Erase farthest
            indmax = np.argmax(distQ)
            stopsList[self.stops[indmax]].group = []
            del self.stops[indmax]
            #Re-Compute baricenter and radius
            self.northing = np.mean([stopsList[s].northing for s in self.stops])
            self.easting  = np.mean([stopsList[s].easting  for s in self.stops])
            distQ = [( self.easting - stopsList[s].easting )**2 + ( self.northing - stopsList[s].northing )**2 for s in self.stops]
            self.radius = sqrt(np.max(distQ))

        #If last 2 elements are still too distant: separate and deactivate group
        if len(self.stops) <= 2 and self.radius > distance:
            for s in self.stops:
                stopsList[s].group = []
            self.stops = []
            self.isActive = False
            self.modes = set()
            self.radius = 0
        else:
            self.lon = np.mean([stopsList[s].lon for s in self.stops])
            self.lat = np.mean([stopsList[s].lat for s in self.stops])
        self.isCorrected = True


    def indentifyRepresentant(self,stopsList):
        self.atcoStop = self.id[0:3]+'0'+self.id[4:] #The name of the group without the G
        if self.atcoStop not in self.stops:
            ranks =  [rankDictionary[mode] for mode in [stopsList[stop].mode for stop in self.stops]]
            self.atcoStop = self.stops[ranks.index(min(ranks))] #a random high rank stop

        
class Flight(object):
        
    def __init__(self,row):
        iataOri = row[2][:3:]
        iataDes = row[3][:3:]
        oriTerm = row[9][0]
        desTerm = row[10][0]

        self.km = row[4]
        self.mins = row[13]
        self.oriT = row[11]
        self.desT = row[12]
        self.days = row[15]

        #LGWN = LGW1, LGWS = LGW2, GLAM =  GLA, YYY = YYY1
        if oriTerm == 'N': oriTerm='1'
        if oriTerm == 'S': oriTerm='2'
        if oriTerm == 'M': oriTerm='1'
        if oriTerm == ' ': oriTerm='1'
        if desTerm == 'N': desTerm='1'
        if desTerm == 'S': desTerm='2'
        if desTerm == 'M': desTerm='1'
        if desTerm == ' ': desTerm='1'

        self.atcoOri = '9200'+iataOri+oriTerm.strip()
        self.atcoDes = '9200'+iataDes+desTerm.strip()



"""------------------------------------------------------------------------------"""
""" FUNCTIONS                                                                    """
"""------------------------------------------------------------------------------"""

#Assign Stops to Layers
def checkStopsInTimetable(stops,modeLetter,path):
    timetableData = open(path,'r')
    rdr= iter(timetableData) #Iterator
    rdr.next() #Skips First Line
   

    missingStops = []
    for line in rdr:
        head = line[:2:]
        if head == 'QO' or head =='QI' or head =='QT':
            atcocode = line[2:14:].strip()
            stop = stops.get(atcocode,'NotIndexed')
            if stop == 'NotIndexed':
                missingStops.append(atcocode)
            else:
                stop.isActive = True
                stop.modes.add(modeLetter)

                #Correct the use of taxi stops for busses
                if stop.mode == 'T':
                    if modeLetter == 'B' or modeLetter == 'C':
                        stop.mode = 'BC'
                    else:
                        stop.mode = modeLetter                      

    timetableData.close()

    return list(set(missingStops))


def checkUsedAirportTerminals(stops):
    #ALL MISSING AIRPORTS ARE IGNORED


    airTimetablesData = open(INNOVATAtimetablesPath+'UKDOMESTICOCT10.csv','r')
    for i in range(3): #Skips First Three Lines
        airTimetablesData.next() 

    csvreader = csv.reader(airTimetablesData, delimiter=',', quotechar='"')
    for ind,row in enumerate(csvreader):
        flight = Flight(row)

        stop = stops.get(flight.atcoOri,'NotIndexed')
        if stop != 'NotIndexed':
            stop.isActive = True
            stop.modes.add('A')
        
        stop = stops.get(flight.atcoDes,'NotIndexed')
        if stop != 'NotIndexed':
            stop.isActive = True
            stop.modes.add('A')

    airTimetablesData.close()



#NON INDEXED ARE MISSING STOPS: SKIP THEM
def writeLinks(atco2node,modeletter,readpath,writepath):
    #I have to handle non indexed
    timetableData = open(readpath,'r')
    linkData = open(writepath,'w')
    rdr= iter(timetableData) #Iterator
    rdr.next() #Skips First Line
    origin = -1
    nextDay = False

    lastGoodMinute = 0
    for line in rdr:
        head = line[:2:]       
        if head == 'QS':
            days = line[29:36:]
            if origin != -1: print "ORDERING ERROR IN TIMETABLE LINE:"+line
            #HERE I HAVE TO HANDLE RUNNING DATES TOO
        if head == 'QE': 
            pass #HERE I HAVE TO HANDLE RUNNING DATES TOO
        if head == 'QR':
            print "ERROR: no handling for route repetition is ready yet"
        if head == 'QG' or head == 'QJ' or head == 'QW':
            print "WARNING: no handling for node interchange is ready yet"
        if head == 'QO':
            nextDay = False
            badRoute = False
            if origin != -1: print "ORDERING ERROR IN TIMETABLE LINE:"+line
            atcocode = line[2:14:].strip()
            node = atco2node.get(atcocode,'NotIndexed')
            
            lastGoodMinute = 0 #It the first point the day should be correctly defined
            depT = line[14:18:]
            depMin = 60*int(depT[:2:])+int(depT[2::])#If depT = '0000', depMin = 0 -> Bad Departure
            if node != 'NotIndexed':
                origin = node
            else:
                origin = 'missing' #If missing i) remember it ii) keep track of time

        elif head =='QI':
            if origin == -1: print "ORDERING ERROR IN TIMETABLE LINE:"+line
            atcocode = line[2:14:].strip()
            node = atco2node.get(atcocode,'NotIndexed')

            arrT = line[14:18:]
            depT = line[18:22:]
            #If only one is 0000, keep the other to avoid errors
            if arrT == '0000' and depT != '0000':
                arrT = depT
            elif arrT != '0000' and depT == '0000':
                depT = arrT
            #Now I can hope all is ok
            arrMin = 60*int(arrT[:2:])+int(arrT[2::])
            if arrMin < depMin:
                if modeletter == 'B' and depMin-arrMin < 1320: #Start ignoring wrong bus routes if the difference is over 2h
                    badRoute = True
                else:
                    nextDay = True
            if nextDay == True:
                arrMin += 1440
                    
            if node != 'NotIndexed':
                for day in range(len(days)):
                    if days[day] == '1' and not badRoute and origin != 'missing': #If last missing, just don't print
                        linkData.write("%6d"%origin+modeletter+',%6d'%node+modeletter+',%5d'%(1440*day+depMin)+',%5d'%(1440*day+arrMin)+'\n')
                #Set next origin
                origin = node
            else: #if this missing: i) don't print, ii) remember it as missing origin
                origin = 'missing'

            #In any case, keep track of departure time
            if depT == '    ':
                depT = arrT
            depMin = 60*int(depT[:2:])+int(depT[2::]) + (nextDay * 1440)
                    
                    
        elif head =='QT':
            if origin == -1: print "ORDERING ERROR IN TIMETABLE LINE:"+line
            atcocode = line[2:14:].strip()
            node = atco2node.get(atcocode,'NotIndexed')
            if node != 'NotIndexed':
                arrT = line[14:18:]
                #Now I can hope all is ok
                arrMin = 60*int(arrT[:2:])+int(arrT[2::])
                if arrMin < depMin:
                    if modeletter == 'B' and depMin-arrMin < 1320: #Start ignoring wrong bus routes if the difference is over 2h
                        badRoute = True
                    else:
                        nextDay = True
                if nextDay == True:
                    arrMin += 1440
                for day in range(len(days)):
                    if days[day] == '1' and not badRoute and origin != 'missing': #If last missing, just don't print
                        linkData.write("%6d"%origin+modeletter+',%6d'%node+modeletter+',%5d'%(1440*day+depMin)+',%5d'%(1440*day+arrMin)+'\n')
            else:
                pass #if this missing, who cares?
            #In any case, reset
            origin = -1
            nextDay =  False
            badRoute =  False

        else:      
            origin = -1
            nextDay =  False
        lastLine = line


    timetableData.close()
    linkData.close()


def writeFlightLinks(atco2node,modeletter,readpath,writepath):
    airTimetablesData = open(readpath,'r')
    linkData = open(writepath,'w')


    for i in range(2): #Skips First Two Lines
        airTimetablesData.next() 

    csvreader = csv.reader(airTimetablesData, delimiter=',', quotechar='"')
    legend = csvreader.next()
    for ind,row in enumerate(csvreader):
        flight = Flight(row)
        depMin = 60*int(flight.oriT[:2:])+int(flight.oriT[2::])
        arrMin = 60*int(flight.desT[:2:])+int(flight.desT[2::])
        origin = atco2node.get(flight.atcoOri,'NotIndexed')
        destination = atco2node.get(flight.atcoDes,'NotIndexed')
        
        if arrMin < depMin: arrMin += 1440 #In case of change of date
        if origin != 'NotIndexed' and destination != 'NotIndexed':
            for day in range(len(flight.days)):
                if flight.days[day] != '.':
                    linkData.write('%6d'%origin+modeletter+',%6d'%destination+modeletter+',%5d'%(1440*day+depMin)+',%5d'%(1440*day+arrMin)+'\n')
                   
    airTimetablesData.close()

def mergeSameRankGroups(modeRank,distance,stops,groups):
    mergeGroups = [ g for g in groups.values() if g.rank == modeRank and g.isActive]
    for gi in range(len(mergeGroups)):
        g = mergeGroups[gi]
        for g2i in range(gi+1,len(mergeGroups)):
            g2 = mergeGroups[g2i]
            if g2.isActive: #Exclude second use of a merged group
                maxDQ = max(g.radius,g2.radius,distance)**2
                dq = (g.northing-g2.northing)**2 + (g.easting - g2.easting)**2
                if dq < maxDQ:
                    g.mergeWith(g2,stops,groups)
                    g.runGroupOperations(stops)


def joinGroupsToHigherRank(modeRank,distance,stops,groups):
    takergroups    = [ g for g in groups.values() if g.rank == modeRank and g.isActive]
    joinablegroups = [ g for g in groups.values() if g.rank >  modeRank and g.isActive]

    for g in takergroups:
        removeList = []
        for g2 in joinablegroups:
            if g2.isActive:
                maxDQ = max(g.radius,g2.radius,distance)**2
                dq = (g.northing-g2.northing)**2 + (g.easting - g2.easting)**2
                if dq <  maxDQ:
                    g.addChild(g2,stops,groups)
                    g.runGroupOperations(stops)
                    removeList.append(g2)

"""------------------------------------------------------------------------------"""
""" MAIN                                                                         """
"""------------------------------------------------------------------------------"""


startTime = time.time()
passTime = startTime

#Define Program Quantities
stops = {}
groups = {}


#Read Stops
stopsData = open(NaPTANPath+'Stops.csv','r')
stopsData.next() #Skips First Line

csvreader = csv.reader(stopsData, delimiter=',', quotechar='"')
for ind,row in enumerate(csvreader):
    #Stops 
    atcocode = row[0]
    stops[atcocode] = StopPoint(row)
stopsData.close()

endTime = time.time()
print "--------------------\nRead Stops: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

#Select Only Used Stops: Read Timetables
checkUsedAirportTerminals(stops)
endTime = time.time()
print "--------------------\nRead AIR Timetables: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

missingBus   = checkStopsInTimetable(stops,'B',NPTDRTimetablesPath+'NATIONAL_BUS_ATCOPT.CIF')
missingCoach = checkStopsInTimetable(stops,'C',NPTDRTimetablesPath+'NATIONAL_COACH_ATCOPT.CIF')
missingMetro = checkStopsInTimetable(stops,'M',NPTDRTimetablesPath+'NATIONAL_METRO_ATCOPT.CIF')
missingRail  = checkStopsInTimetable(stops,'R',NPTDRTimetablesPath+'NATIONAL_RAIL_ATCORAIL_corrected.CIF')
missingFerry = checkStopsInTimetable(stops,'F',NPTDRTimetablesPath+'NATIONAL_FERRY_ATCOPT.CIF')
missingStops = missingBus + missingCoach + missingFerry + missingMetro + missingRail

missingStopsModes = {}
for ms in missingStops:
    missingStopsModes[ms] = set()
for ms in missingBus:
    missingStopsModes[ms].add('B')
for ms in missingCoach:
    missingStopsModes[ms].add('C')
for ms in missingMetro:
    missingStopsModes[ms].add('M')
for ms in missingRail:
    missingStopsModes[ms].add('R')
for ms in missingFerry:
    missingStopsModes[ms].add('F')

print "Number of Missing Stops:",len(missingStops)

cont = 0
for i,s in stops.items():
    if s.isActive:
        cont+=1

print "Number of Active Stops: %d out of %d"%(cont,len(stops))




endTime = time.time()
print "--------------------\nRead Timetables: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


#Read Groups
groupsData = open(NaPTANPath+'/Groups.csv','r')
groupsData.next() #Skips First Line

csvreader = csv.reader(groupsData, delimiter=',', quotechar='"')
for ind,row in enumerate(csvreader):
    groupid = row[0]
    groups[groupid] = StopArea(row)

groupsData.close()

endTime = time.time()
print "--------------------\nRead Groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


#Read Stops In Group
stopsInGroupData = open(NaPTANPath+'StopsInGroup.csv','r')
stopsInGroupData.next() #Skips First Line

csvreader = csv.reader(stopsInGroupData, delimiter=',', quotechar='"')
for ind,row in enumerate(csvreader):
    groupid = row[0]
    stopid  = row[1]
    if stops[stopid].isActive:
        group = groups.get(groupid,'NotIndexed')
        if group == 'NotIndexed':
            print "DATA ERROR: Missing Group:",groupid,stopid
        else:
            if stops[stopid].group == []: #Assign stop only once
                group.addStop(stops[stopid])

stopsInGroupData.close()

endTime = time.time()
print "--------------------\nRead Stops In Group: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


#Read Groups in Group
groupsInGroupData = open(NaPTANPath+'GroupsInGroup.csv','r')
groupsInGroupData.next() #Skips First Line

csvreader = csv.reader(groupsInGroupData, delimiter=',', quotechar='"')
for ind,row in enumerate(csvreader):
    parentid = row[0]
    childid  = row[1]
    groups[parentid].addChild(groups[childid],stops,groups)


groupsInGroupData.close()
endTime = time.time()
print "--------------------\nRead Groups in Group: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

#Define group AREAS
for group in groups.values():
    areas = [stops[s].atcoarea for s in group.stops if int(stops[s].atcoarea) < 900] #Only local stops (<900) have a well defined area
    if len(areas) > 0:
        #Majority rule, imposed to all stops
        group.atcoarea = max(set(areas), key=areas.count)
        for s in group.stops:
            if stops[s].atcoarea != group.atcoarea: stops[s].atcoarea = group.atcoarea
                
endTime = time.time()
print "--------------------\nDefine group AREAS: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

#Correct single groups

#- FERRY HARBORS AND AIRPORTS are kept as defined
#- Centers are corrected with the baricenter if the correction put a group in the wdL range
#- RAIL, METRO and COACH stops are kept if present, and bus stops out of wdL are removed
#- BUS clusters are corrected with a specific method and a stricter walking distance

initialGroups = 0
finalGroups = 0
for group in groups.values():
    #The things to do to make the group consistent

    if group.isActive:
        group.runGroupOperations(stops)
    if group.isActive:
        initialGroups+=1
    if group.isActive and group.radius:
        group.correctCenter(stops,wdL)

    tryCorrection = False

    #- RAIL STATIONS:
    if group.isActive and group.mode == 'R'  and group.radius > wdL and 'B' in group.modes:
        group.removeBusStops(wdL,stops)
        tryCorrection = True
    #- METRO STATIONS
    if group.isActive and group.mode == 'M'  and group.radius > wdL and 'B' in group.modes:
        group.removeBusStops(wdL,stops)
        tryCorrection = True
    #- COACHES STATIONS
    if group.isActive and group.mode == 'BC' and group.radius > wdL and 'C' in group.modes:
        group.removeBusStops(wdL,stops) #Start removing only bus stops
        tryCorrection = True
        if group.radius > wdL: #If it is not sufficient
            group.repairBusClusters(wdL,stops) #Repair the cluster removing also coach stops
    #- BUS GROUPS
    if group.isActive and group.mode == 'BC' and group.radius > wdS and not 'C' in group.modes:
        group.repairBusClusters(wdS,stops)
        tryCorrection = True
    if tryCorrection:
        group.runGroupOperations(stops)
    #Recalculate after removals
    if group.isActive:
        finalGroups+=1

print "Corrected/Final/Initial Active Groups Number:%d/%d/%d"%(len([g for g in groups.values() if g.isActive and g.isCorrected]),finalGroups,initialGroups)


endTime = time.time()
print "--------------------\nErase Stops single groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


nonBusAreas = [ g for g in groups.values() if ('A' in g.modes or 'F' in g.modes or 'R' in g.modes or 'M' in g.modes) and g.isActive]
print "Unlinked High Rank %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)


#A0) Join airports if they share the same first 6 letters in atcocode (both stops and groups)
airGroups = [ g for g in groups.values() if 'A' in g.modes and g.isActive and g.parent == []]
airStops  = [ s for s in stops.values()  if 'A' in s.modes and s.group == [] and s.isActive ]
for gi in range(len(airGroups)):
    g = airGroups[gi]
    for g2i in range(gi+1,len(airGroups)):
        g2 = airGroups[g2i]
        if g.id[:7] == g2.id[:7]:
            if int(g.id[7])< int(g2.id[7]):
                g.mergeWith(g2,stops,groups)
                g.runGroupOperations(stops)

            else:
                g2.mergeWith(g,stops,groups)
                g2.runGroupOperations(stops)

    for s in airStops:
        if g.id[:7] == s.atcocode[:3]+'G'+s.atcocode[4:7]:
             print "ERROR: THIS STOP HAS TO BE MERGED",g.name,g.id, s.name, s.atcocode
#Make free airport a group
for mS in airStops:
    newArea = StopArea([mS.atcocode,mS.name,mS.type,'groupFromStop',mS.easting,mS.northing,mS.lon,mS.lat,mS.mode])
    newArea.addStop(mS)
    groups[mS.atcocode] = newArea
    groups[mS.atcocode].runGroupOperations(stops)



#A1) Join all inferiors groups and non bus stops within wdL + BUILD UP HEATROW
airGroups = [ g for g in groups.values() if 'A' in g.modes and g.isActive and g.parent == []]
joinablegroups = [ g for g in groups.values() if g.isActive and g.parent == []]
nonBCstops = [s for s in stops.values() if s.mode != 'BC' if s.isActive and s.group == []]

for g in airGroups:
    for g2 in joinablegroups:
        maxDQ = max(g.radius,g2.radius,wdL)**2
        if g2 != g and g2.isActive:
            dq = (g.northing-g2.northing)**2 + (g.easting - g2.easting)**2
            if dq <  maxDQ or (g.id == '920GLHR1' and g2.name[:8] == 'Heathrow' and dq < 3000**2):
                g.addChild(g2,stops,groups)
                g.runGroupOperations(stops)
    maxDQ = max(g.radius,wdL)**2
    for s in nonBCstops:
        dq = (g.northing-s.northing)**2 + (g.easting - s.easting)**2
        if dq < maxDQ:
            g.addStop(s)
            g.runGroupOperations(stops)



nonBusAreas = [ g for g in groups.values() if ('A' in g.modes or 'F' in g.modes or 'R' in g.modes or 'M' in g.modes) and g.isActive]
print "Unlinked High Rank %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)

endTime = time.time()
print "--------------------\nCorrect Airport groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime





#OTHER MEANS
#O1) Make groups from high rank stops
nonBusStops = [ s for s in stops.values() if ('F' in s.modes or 'R' in s.modes or 'M' in s.modes) and s.group == [] and s.isActive]

for mS in nonBusStops:
    newArea = StopArea([mS.atcocode,mS.name,mS.type,'groupFromStop',mS.easting,mS.northing,mS.lon,mS.lat,mS.mode])
    newArea.addStop(mS)
    groups[mS.atcocode] = newArea
    groups[mS.atcocode].runGroupOperations(stops)


#02)  R: wdL, F & M: wdS (to not do a mess in london)
#GROUP MERGING AND JOINING FUNCTIONS



#R
mergeSameRankGroups(2,wdL,stops,groups)
joinGroupsToHigherRank(2,wdL,stops,groups)



nonBusAreas = [ g for g in groups.values() if ('A' in g.modes or 'F' in g.modes or 'R' in g.modes or 'M' in g.modes) and g.isActive]
print "Unlinked High Rank %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
endTime = time.time()
print "--------------------\nCorrect Rail groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


#F
mergeSameRankGroups(3,wdS,stops,groups)
joinGroupsToHigherRank(3,wdS,stops,groups)

nonBusAreas = [ g for g in groups.values() if ('A' in g.modes or 'F' in g.modes or 'R' in g.modes or 'M' in g.modes) and g.isActive]
print "Unlinked High Rank %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
endTime = time.time()
print "--------------------\nCorrect Ferry groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime



#M
mergeSameRankGroups(4,wdS,stops,groups)
joinGroupsToHigherRank(4,wdS,stops,groups)


nonBusAreas = [ g for g in groups.values() if ('A' in g.modes or 'F' in g.modes or 'R' in g.modes or 'M' in g.modes) and g.isActive]
print "Unlinked High Rank %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
endTime = time.time()
print "--------------------\nCorrect Metro groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime



#Stops inclusion
#A group can absorb a bus stop if it is within range

freeBusStops = [s for s in stops.values() if s.group == [] and s.modes == set('B') and s.isActive]

proposedInclusions1 = {}
proposedInclusions2 = {}

for group in groups.values():
    #For all groups in layers A,F,R,M,C, C only off street
    if group.isActive and group.modes != set('B') and (group.mode != 'BC' or group.type == 'GBCS'):
        for stop in freeBusStops:
            dq = (group.northing-stop.northing)**2 + (group.easting - stop.easting)**2
            #If a bus stop is in group radius or walking distance (whatever is minimal): propose assignation to that cluster with distance d
            if dq < group.radius**2:
                a =  proposedInclusions1.get(stop.atcocode,'NI')
                if a == 'NI':
                    proposedInclusions1[stop.atcocode] = [[group.mode,group.id,dq]]
                else:
                    a.append([group.mode,group.id,dq])
            elif dq < wdS**2:
                a =  proposedInclusions2.get(stop.atcocode,'NI')
                if a == 'NI':
                    proposedInclusions2[stop.atcocode] = [[group.mode,group.id,dq]]
                else:
                    a.append([group.mode,group.id,dq])



modGroup1 = []

#Range defined by actual radius+proximity to an important stop (not BC)
for s,p in proposedInclusions1.items():
    #Check if at WD from any high rank stop in group
    p2 = []
    for aGroup in p:
        dq = [(stops[s].northing-stops[aStop].northing)**2+(stops[s].easting-stops[aStop].easting)**2 for aStop in groups[aGroup[1]].stops if stops[aStop].mode != 'BC']
        if len(dq)>0:
            if min(dq) < wdS**2:
                p2.append(aGroup)
    if len(p2) == 0:
        continue
    else:
        p = p2
    
    if len(p) == 1:
        groups[p[0][1]].addStop(stops[s])
        modGroup1.append(groups[p[0][1]])
    else:
        #If ranks different pick higher rank, if equal pick minmal distance
        ranks = [rankDictionary[ss[0]]+sqrt(ss[2])*0.0001 for ss in p]
        indMin = ranks.index(min(ranks))
        groups[p[indMin][1]].addStop(stops[s])
        modGroup1.append(groups[p[indMin][1]])

correctedWithRadius = len(set(modGroup1))


modGroup2 = []

#Range defined by WD+proximity to an important stop
#THIS HAS TO BE DONE, EVEN IF IT IS ROUGH, IF NOT MANY RAIL STATIONS WOULD BE DISCONNECTED FROM THE BUS SYSTEM
for s,p in proposedInclusions2.items():
    
    #Check if at WD from any high rank stop in group
    p2 = []
    for aGroup in p:
        dq = [(stops[s].northing-stops[aStop].northing)**2+(stops[s].easting-stops[aStop].easting)**2 for aStop in groups[aGroup[1]].stops if stops[aStop].mode != 'BC']
        if len(dq)>0:
            if min(dq) < wdS**2:
                p2.append(aGroup)
    if len(p2) == 0:
        continue
    else:
        p = p2
    
    if len(p) == 1:
        groups[p[0][1]].addStop(stops[s])
        modGroup2.append(groups[p[0][1]])
    else:
        #If ranks different pick higher rank, if equal pick minmal distance
        ranks = [rankDictionary[ss[0]]+sqrt(ss[2])*0.0001 for ss in p]
        indMin = ranks.index(min(ranks))
        groups[p[indMin][1]].addStop(stops[s])
        modGroup2.append(groups[p[indMin][1]])

correctedWithWD = len(set(modGroup2))


#AT THIS POINT, I FREE UNCHILDED GROUPS OF 1 STOPS, so that they can be merged in the following
preN = 0
for group in groups.values():
    if group.isActive:
        if len(group.stops) == 1 and group.parent == []:
            group.isActive = False
            stops[group.stops[0]].group = []
            group.stops = []
            group.modes = set()
            group.radius = 0
        else:
            preN+=1




#A stop can absorb a lower rank group/stop if it is within range
#if taker single: create group of 2 with taker as representant

freeOtherStops = [s for s in stops.values() if s.group == [] and s.mode != 'BC' and s.isActive] #Only A,F,R,M stops can become new groups
proposedInclusions3 = {}

for group in freeOtherStops:
    for stop in freeBusStops:
        dq = (group.northing-stop.northing)**2 + (group.easting - stop.easting)**2
        if dq < wdS**2:
            a = proposedInclusions3.get(stop.atcocode,'NI')
            if a == 'NI':
                proposedInclusions3[stop.atcocode] = [[group.mode,group.atcocode,dq]]
            else:
                a.append([group.mode,group.atcocode,dq])


modGroup3 = {}

for s,p in proposedInclusions3.items():
    if len(p) == 1:
        a = modGroup3.get(stops[p[0][1]],'NI')
        if a == 'NI':
            modGroup3[stops[p[0][1]]] = [stops[p[0][1]],stops[s]]
        else:
            a.append(stops[s])
    else:
        #If ranks different pick higher rank, if equal pick minmal distance
        ranks = [rankDictionary[ss[0]]+sqrt(ss[2])*0.0001 for ss in p]
        indMin = ranks.index(min(ranks))
        a = modGroup3.get(stops[p[indMin][1]],'NI')
        if a == 'NI':
            modGroup3[stops[p[indMin][1]]] = [stops[p[indMin][1]],stops[s]]
        else:
            a.append(stops[s])


newGroups = 0
#Here all the processes applied to the groups should happen for the new one
for ng in modGroup3.values():
    mS = ng[0] #main stop
    #Create
    newArea = StopArea([mS.atcocode,mS.name,mS.type,'groupFromStop',mS.easting,mS.northing,mS.lon,mS.lat,mS.mode])
    for ngi in ng:
        newArea.addStop(ngi)
    newArea.runGroupOperations(stops)
    
    newGroups+=1
    groups[mS.atcocode] = newArea

print "Corrected Radius/Corrected WD/New Groups:%d/%d/%d"%(correctedWithRadius,correctedWithWD,newGroups)


nonBusAreas = [ g for g in groups.values() if ('A' in g.modes or 'F' in g.modes or 'R' in g.modes or 'M' in g.modes) and g.isActive]
print "Unlinked High Rank %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
nonBusAreas = [ g for g in groups.values() if g.rank == 1 and g.isActive]
print "Unlinked Airports %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
nonBusAreas = [ g for g in groups.values() if g.rank == 2 and g.isActive]
print "Unlinked Rail %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
nonBusAreas = [ g for g in groups.values() if g.rank == 3 and g.isActive]
print "Unlinked Ferry %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)
nonBusAreas = [ g for g in groups.values() if g.rank == 4 and g.isActive]
print "Unlinked Metro %4.1f%%"%(float(len([n for n in nonBusAreas if len(n.modes) == 1]))/len(nonBusAreas)*100)


endTime = time.time()
print "--------------------\nBus stops inclusions in higher groups: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


#FINAL GROUP PROCESSING: IDENTIFY STOP REPRESENTANT AND DEACTIVATION GROUPS OF 1 ELEMENT
postN = 0
for group in groups.values():
    if group.isActive:
        group.runGroupOperations(stops)
        if group.isActive:
            postN+=1

print "Pre/Post Final Active Groups Number:%d/%d"%(preN,postN)



endTime = time.time()
print "--------------------\nFinal Group Processing: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime




#DEFINE NODES
atco2node = {}
repr2node = {}

nodeID = 0

distances = []

for group in groups.values():
    if group.isActive:
        group.indentifyRepresentant(stops)
        repr2node[group.atcoStop] = nodeID #group representant
        
        for stop in group.stops:
            atco2node[stop] = nodeID
        #Here I compute distances
        modeList = list(group.modes)
        for i in range(len(modeList)):
            for j in range(i+1,len(modeList)):
                
                sI = [stops[stop] for stop in group.stops if modeList[i] in stops[stop].modes]
                sJ = [stops[stop] for stop in group.stops if modeList[j] in stops[stop].modes]
                d = 0
                n = 0
                for ssi in sI:
                    for ssj in sJ:
                        d+= sqrt((ssi.northing - ssj.northing)**2 + (ssi.easting - ssj.easting)**2)
                        n+= 1
                if n> 0: d /= n
                distances.append([str(nodeID)+modeList[i],str(nodeID)+modeList[j],d])
        
        nodeID+=1
for stop in stops.values():
    if stop.isActive and stop.group == []:
        atco2node[stop.atcocode] = nodeID
        repr2node[stop.atcocode] = nodeID
        #Here I compute distances
        for i in range(len(stop.modes)):
            for j in range(i+1,len(stop.modes)):
                distances.append([str(nodeID)+list(stop.modes)[i],str(nodeID)+list(stop.modes)[j],0])
        nodeID+=1

endTime = time.time()
print "--------------------\nDEFINE NODES: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

#PRINT LINKS

writeLinks(atco2node,'C',NPTDRTimetablesPath+'NATIONAL_COACH_ATCOPT.CIF', outputPath+'temp/linkC.csv')
writeLinks(atco2node,'F',NPTDRTimetablesPath+'NATIONAL_FERRY_ATCOPT.CIF', outputPath+'temp/linkF.csv')
writeLinks(atco2node,'M',NPTDRTimetablesPath+'NATIONAL_METRO_ATCOPT.CIF', outputPath+'temp/linkM.csv')
writeLinks(atco2node,'R',NPTDRTimetablesPath+'NATIONAL_RAIL_ATCORAIL_corrected.CIF',outputPath+'temp/linkR.csv')
writeLinks(atco2node,'B',NPTDRTimetablesPath+'NATIONAL_BUS_ATCOPT.CIF',   outputPath+'temp/linkB.csv')

writeFlightLinks(atco2node,'A',INNOVATAtimetablesPath+'UKDOMESTICOCT10.csv',outputPath+'temp/linkA.csv')



endTime = time.time()
print "--------------------\nPRINT LINKS: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime

#PRINT NODES
# NODEID | lat lon | ATCOcode region
#may add natgazid of the leading element of the group

repr2node_output = sorted(repr2node.items(), key=lambda x: abs(x[1]))

nodesFile = open(outputPath+ "nodes.csv", "w")

countGlobalAreas = 0
for atcocode,nodeID in repr2node_output:
    if nodeID >= 0:
        if stops[atcocode].group == []:
            for m in stops[atcocode].modes:
                nodesFile.write("%6d"%nodeID + m + ",")
                nodesFile.write("%8.5f"%stops[atcocode].lat + ","+ "%8.5f"%stops[atcocode].lon + ",")
                nodesFile.write("%12s"%atcocode + ",")
                nodesFile.write("%3s"%stops[atcocode].atcoarea + "\n")
            if int(stops[atcocode].atcoarea) >= 900: countGlobalAreas+=1
        else:
            thisGroup = groups[stops[atcocode].group]
            for m in thisGroup.modes:
                nodesFile.write("%6d"%nodeID + m + ",")
                nodesFile.write("%8.5f"%thisGroup.lat + ","+ "%8.5f"%thisGroup.lon + ",")
                nodesFile.write("%12s"%thisGroup.id + ",")
                nodesFile.write("%3s"%thisGroup.atcoarea + "\n")
            if int(thisGroup.atcoarea) >= 900: countGlobalAreas+=1

nodesFile.close()

print "Area unknown for %d nodes out of %d"%(countGlobalAreas,len(repr2node_output))

endTime = time.time()
print "--------------------\nPRINT NODES: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime


#PRINT INTRA-LAYER DISTANCES

intraLayersFile = open(outputPath+ "intra_layers.csv", "w")


for d3 in distances:
    intraLayersFile.write("%7s,%7s,%3d\n"%(d3[0],d3[1],round(d3[2])))

intraLayersFile.close()



endTime = time.time()
print "--------------------\nINTRALAYER DISTANCES: %5.2f seconds\n--------------------\n"%(endTime-passTime)
passTime =  endTime




