In order to ensure the replicability and reproducibility of our dataset

Gallotti, R. \& Barthelemy, M. Dryad Digital Repository. doi:10.5061/dryad.pc8m3 (2014).

we share here all codes that were developed for producing this dataset. The software is written in Python 2.7. The input files needed are the air timetables provided to us by Innovata LLC, which are included in our dataset  and the 2010 snapshot the NPTDR data. In particular: 
- the folder identified in the code as "NPTDRTimetablesPath" is contained in all the unzipped version of the files present in the folder October-2010/Timetable Data/CIF/National; 
- the folder "NaPTANPath"  contains the file present in the .zip file October-2010/NaPTANcsv.zip;
- the folder "INNOVATAtimetablesPath" contains the file UKDOMESTICOCT10.csv that accompanies our dataset. 



The workflow consists in the following steps:

0_correctRailTimetables.py
Correct the Rail timetables from the '0000000' error. It produces a corrected copy of the timetable in the original .CIF format, used in step 1.

1_stops.py
Recognizes active stops, performs the stops' coarse-graining, associates nodes with areacode, corrects inconsistencies in all timetables, computes intra-layer distances. It produces a set of intermediate files (nodes list, events list, intra-layer edges list) used for the steps 2 and 3.

2_links.py
Sorts and rewrites the events list, compute the minimal traveltime for all edges. The output is a second version of the events list and a intra-layer edges list, used in step 3.

3_finalformat.py  
Computes the inter-layer traveltime, corrects the minimal traveltime when 0. The output is  the final format of the dataset.
\end{description}

The file layers.csv is simply typed in a text editor. Several parameters can be easily modified in this workflow. The walking distance wd is defined in step 1. Walking speed, flight connection times, minimal connection time and the lower threshold to the minimal traveltime are defined in step 3. In addition, the same workflow can be also applied for all years where the NPTDR data are available (2004-2011).