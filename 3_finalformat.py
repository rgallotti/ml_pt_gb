"""------------------------------------------------------------------------------"""
""" AUTHOR:  Riccardo Gallotti (rgallotti@gmail.com)                             """
""" VERSION: 1.0                                                                 """
"""------------------------------------------------------------------------------"""

#Compute the inter-layer traveltime, corrects the minimal traveltime when 0. 
#Produces the final format of the dataset.

"""------------------------------------------------------------------------------"""
""" PARAMETERS                                                                   """
"""------------------------------------------------------------------------------"""

walkingSpeed = 5  /3.6 *60 #5 Km/h in [m/min]

#Times in minutes
minTravel = 1.0 #added a minimum intra e interlayer traveltime of 1 minute
minWalk   = 1.0
airportDepartureTime = 120
airportLandingTime = 30

modes = ['A','F','R','M','C','B']
layDict = {'A':0,'R':2,'F':1,'M':3,'B':5,'C':4}


"""------------------------------------------------------------------------------"""
""" IMPORT                                                                       """
"""------------------------------------------------------------------------------"""
import math
import csv
import numpy as np


"""------------------------------------------------------------------------------"""
""" LOCALIZATION                                                                 """
"""------------------------------------------------------------------------------"""

outputPath = '/Users/rgallott/Work/PlexMath/Output/'
releasePath = '/Users/rgallott/Work/PlexMath/Data_Release/'



"""------------------------------------------------------------------------------"""
""" FUNCTIONS                                                    `               """
"""------------------------------------------------------------------------------"""

def dis(lat1,lon1,lat2,lon2):

    lat0 = (lat1+lat2)*0.5
    c_lat= 0.6*100000*(1.85533-0.006222*math.sin(lat0*math.pi/180))
    c_lon= c_lat*math.cos(lat0*math.pi/180)

    dx = c_lon*(lon1-lon2)
    dy = c_lat*(lat1-lat2)
    
    return int(math.sqrt(dx**2 + dy**2))

"""------------------------------------------------------------------------------"""
""" MAIN                                                                         """
"""------------------------------------------------------------------------------"""

#Rewrite nodes.csv in the final format

nodesLatLon ={}

with open(outputPath+'nodes.csv', 'r') as nodesFile, open(releasePath+'nodes.csv', 'w') as nodes_rel :
    nodes_rel.write('\"node\",\"layer\",\"lat\",\"lon\",\"zone\",\"atcocode\"\n')

    csvreader = csv.reader(nodesFile, delimiter=',', quotechar='"')
    for row in csvreader:
        nodeID = int(row[0][:6:].strip())
        nodeMode = row[0][6]
        lat = float(row[1])
        lon = float(row[2])
        atcocode = row[3]
        zone = int(row[4])
        nodes_rel.write('%6d,%1d,%8.5f,%8.5f,%3d,\"%s\"\n'%(nodeID,layDict[nodeMode],lat,lon,zone,atcocode))
        nodesLatLon[nodeID] = (lat,lon)



#Build the finald edges.csv file joining the intra_layer and topo_links links
with open(releasePath+"edges.csv","w") as edgesFile:
    edgesFile.write('\"ori_node\",\"des_node\",\"ori_layer\",\"des_layer\",\"minutes\",\"km\"\n')

    with open(outputPath+"topo_links.csv","r") as fileData:
        csvreader = csv.reader(fileData, delimiter=',')
        for row in csvreader:
            nodeA_ID = int(row[0][:6:].strip())
            nodeA_Mode = row[0][6]
            nodeB_ID = int(row[1][:6:].strip())
            nodeB_Mode = row[1][6]
            dt    = int(row[2])
            if dt < minTravel:
                dt = minTravel

            aLL = nodesLatLon[nodeA_ID]
            bLL = nodesLatLon[nodeB_ID]
            d = dis(aLL[0],aLL[1],bLL[0],bLL[1])*0.001 #In km

            edgesFile.write('%6d,%6d,%1d,%1d,%3d,%7.3f\n'%(nodeA_ID,nodeB_ID,layDict[nodeA_Mode],layDict[nodeB_Mode],dt,d))


    with open(outputPath+"intra_layers.csv","r") as fileData:
        csvreader = csv.reader(fileData, delimiter=',')
        for row in csvreader:
            nodeA_ID = int(row[0][:6:].strip())
            nodeA_Mode = row[0][6]
            nodeB_ID = int(row[1][:6:].strip())
            nodeB_Mode = row[1][6]

            d = float(row[2])
            dtAB = minWalk + d/walkingSpeed #ds in m -> dt in min + minimum walkingtime of 1 minute
            dtBA = dtAB
        
            if nodeA_Mode == 'A':
                dtAB = airportLandingTime   + d/walkingSpeed
                dtBA = airportDepartureTime
                
            if nodeB_Mode == 'A':
                dtBA = airportLandingTime   + d/walkingSpeed
                dtAB = airportDepartureTime
            edgesFile.write('%6d,%6d,%1d,%1d,%3d,%6.3f\n'%(nodeA_ID,nodeB_ID,layDict[nodeA_Mode],layDict[nodeB_Mode],dtAB,d*0.001))
            edgesFile.write('%6d,%6d,%1d,%1d,%3d,%6.3f\n'%(nodeB_ID,nodeA_ID,layDict[nodeB_Mode],layDict[nodeA_Mode],dtBA,d*0.001))



#Rewrite the time_links in an unique events.txt file
isFirst = True
with open(releasePath+"events.txt","w") as eventsFile:
    for m in modes:
        with open(outputPath+"time_links"+m+".csv","r") as fileData:
            csvreader = csv.reader(fileData, delimiter=',')
            for row in csvreader:
                if len(row) == 4:
                    if not isFirst:
                        eventsFile.write('\n')
                    isFirst = False

                    nodeA_ID = int(row[0][:6:].strip())
                    nodeA_Mode = row[0][6]
                    nodeB_ID = int(row[1][:6:].strip())
                    nodeB_Mode = row[1][6]
                    dt    = int(row[2])
                    if dt < minTravel:
                        dt = minTravel
                    eventsFile.write('%6d,%6d,%1d,%1d'%(nodeA_ID,nodeB_ID,layDict[nodeA_Mode],layDict[nodeB_Mode]))
                elif len(row) == 2:
                    oriT = int(row[0])
                    desT = int(row[1])
                    eventsFile.write(',%d,%d'%(oriT,desT-oriT))
