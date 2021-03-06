#! /usr/local/bin/python

# TODO: handle incompleteness in data --- missing *off* if double *on*

import sys
import time, datetime
from pprint import pprint
import operator # for sorting

# generator flags
DOARFF = False
DOFN   = False

# time window length in microsecond (10^-6): 5 seconds
WINDOWLENGTH = 5 * 1000000

# Prolog ground truth
activityRule = "activity"

# Weka ground truth
atRelation = "@RELATION smartHouse\n"
atAttribute = "@ATTRIBUTE "
atributeTF = " {true, false}"
atributeN  = " numeric"
atributeD  = " \"yyyy-MM-dd HH:mm:ss.SSS\""
atClass = "\n@ATTRIBUTE class "
atData = "\n@DATA"

# Data format: 2008-03-28 13:42:40.467418 M18 ON
def convertDataEntry( sequenced, line ):
  entities = line.split()

  # get date
  date = " ".join(entities[0:2])
  # some readings does not have milliseconds
  try:
    stamp = time.mktime(datetime.datetime.strptime( date, "%Y-%m-%d %H:%M:%S.%f" ).timetuple())
    # #
    dot = entities[1].find('.')
    msec = float( entities[1][dot:] )
    # #
    stamp += msec
  except:
    stamp = time.mktime(datetime.datetime.strptime( date, "%Y-%m-%d %H:%M:%S" ).timetuple())

  # get date in Weka format
  dateFormat = datetime.datetime.fromtimestamp(round(stamp, 3)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

  # Convert timestamp to integer
  stamp *= 1000000
  stamp = int(stamp)
  ##############################################################################

  # get sensor ID
  sensor = entities[2].lower()
  ##############################################################################

  # get signal value
  signal = entities[3]
  # check if can be parsed
  try:
    numericValue = float(signal)
  except:
    numericValue = None

  # output variable
  uniformSignal = None
  if   signal == "ON":
    uniformSignal = "true"
  elif signal == "OFF":
    uniformSignal = "false"
  elif signal == "START":
    uniformSignal = "true"
  elif signal == "END":
    uniformSignal = "false"
  elif signal == "PRESENT":
    uniformSignal = "true"
  elif signal == "ABSENT":
    uniformSignal = "false"
  elif signal == "OPEN":
    uniformSignal = "true"
  elif signal == "CLOSE":
    uniformSignal = "false"
  elif signal == "START_INSTRUCT":
    uniformSignal = "true"
  elif signal == "STOP_INSTRUCT":
    uniformSignal = "false"
  elif signal == "true":
    uniformSignal = "true"
  elif signal == "false":
    uniformSignal = "false"
  elif signal == str(numericValue):
    uniformSignal = numericValue
  else:
    print "Unrecognised signal: ", signal
    sys.exit(1)
  ##############################################################################


  # Action begins & ends here
  action = []
  if len(entities) > 4:
    actions = entities[4:]

    # the length should be even
    if len(actions) % 2 != 0:
      print "Action beging and end wrongly encoded!"
      print ' '.join(entities)
      sys.exit(1)

    for a in range(0, len(actions), 2):
      apID = actions[a]
      # if possible split action ID on: person and action
      pid = apID.find('_')
      if pid == -1:
        actionID = apID.lower()
        personID = ""
      else:
        actionID = apID[pid+1:].lower()
        personID = apID[:pid][0].lower() + apID[:pid][1:]

      aD = actions[a+1].lower()
      actionDescription = None
      if   aD == 'begin':
        actionDescription = 'true'
      elif aD == 'end':
        actionDescription = 'false'
      else:
        print "Unknown block description!"
        print ' '.join(entities)
        sys.exit(1)
      action.append( (actionID, actionDescription, [stamp, sequenced], personID) )

  ##############################################################################

  return (stamp, sensor, uniformSignal, dateFormat, action)

# Construct sensor knowledge
def sensor_data(sensorID, sensorStatus, timeType, time):
  rule = "sensor("
  # get sensor ID
  rule += sensorID + ", "
  # get sensor status
  rule += sensorStatus + ", "
  #
  # get type of time
  rule += timeType + ", "
  # get time
  rule += time + " "
  # end rule
  rule += ").\n"

  return rule

# get time window of event
def get_window( initTime, currentTime ):
  diff = currentTime - initTime
  # check for negativity
  if diff < 0:
    print "Negative time in get_window()!"
    sys.exit(1)
  # get window: 0--WINDOWLENGTH is 0
  return int(diff/WINDOWLENGTH)

# check whether ground truth is multi-label
def checkLabel(dictionary):
  onLabels = 0
  curretnLabel = 'none'
  for i in dictionary:
    if dictionary[i]:
      onLabels += 1
      curretnLabel = i
  if onLabels > 1:
    print "Multi-label sets not supported at the moment!"
    sys.exit(1)
  return curretnLabel

# get boolean
def getBool(s):
  if s.lower() == 'true':
    return True
  elif s.lower() == 'false':
    return False
  else:
    print "unknown Bool type: ", s, "!"
    sys.exit(1)

# update sensor status based on current entry
def updateSensor(f, sensorStatus):
  if type(f[1]) == str:
    if f[1].lower() != 'true' and f[1].lower() != 'false':
      print "Unknown sensor status (true/false): *", f[1], "*!"
      sys.exit(1)
    sensorStatus[f[0].lower()] = getBool(f[1])
  elif type(f[1]) == float:
    sensorStatus[f[0].lower()] = f[1]
  else:
    print "Unknown sensor status type: *", f[1], "*!"
    sys.exit(1)
  return sensorStatus

# get signals
def getSignals(sensorNames, sensorStatus, groundTruth, arffGroundTruth, i):
  racwd = ""
  for j in sensorNames:
    if j[1] == atributeTF:
      racwd += str(sensorStatus[j[0]]).lower() + ','
    elif j[1] == atributeN:
      if sensorStatus[j[0]] == False:
        racwd += str(-1).lower() + ','
      elif type(sensorStatus[j[0]]) == float:
        racwd += str(sensorStatus[j[0]]).lower() + ','
      else:
        print "Unknown number type of sensor ", j, " of type ", str(type(sensorStatus[j[0]])), " valued: ", sensorStatus[j[0]]
        sys.exit(1)
    else:
      print "Unknown attribute type!"
      sys.exit(1)
  # update label record
  for j in groundTruth:
    # for each range
    groundTruth[j] = False
    for k in range(len(arffGroundTruth[j])):
      beg = arffGroundTruth[j][k][0][2]
      end = arffGroundTruth[j][k][1][2]
      if i in range(beg, end):
        # print "i: ", i, " - ", j
        groundTruth[j] = True
        break
  return (racwd, groundTruth)


if __name__ == '__main__':
  # Check whether file is given as argument
  args = sys.argv
  if len(args) != 2:
    # Fail
    print "No file specified.\nUsage: formatData.py path/to/file"
    sys.exit(1)

  # Initialise matrix
  data = []
  groundFacts = []

  with open(args[1], 'r') as f:
    for i, line in enumerate(f):
      out = convertDataEntry(i, line)
      data.append( out[0:4] )
      groundFacts += out[4]

  # check dataset for multiple residents
  multipleResidents = False
  for i in groundFacts:
    if i[3] != "":
      multipleResidents = True
      break

  # Get name of file without subdirectories
  slashInd = args[1][::-1].find('/')
  name = args[1][::-1][:slashInd][::-1] if slashInd!=-1 else args[1]
  # Get the name without extension
  dotInd = name[::-1].find('.')
  if dotInd != -1 and name[-dotInd:] == "txt":
    name = name[::-1][dotInd+1:][::-1]

  # and create local name
  record = name + ".pl" #background

  # Convert to Aleph format
  ## sort before converting as some datasets(Washington) are not ordered
  data.sort(key=operator.itemgetter(0))

  # normalise time so that each activity starts at 0 - memorise first time-stamp
  init = data[0][0]

  # Open record file and append to it
  with open(record, 'a') as f:
    for i, e in enumerate(data):
      f.write("\n")

      # relative time knowledge
      rule = sensor_data( e[1].lower(), str(e[2]).lower(), "relative", str(e[0] - init) )
      f.write(rule)
      # absolute time knowledge
      rule = sensor_data( e[1].lower(), str(e[2]).lower(), "absolute", str(e[0]) )
      f.write(rule)
      # absolute time knowledge
      rule = sensor_data( e[1].lower(), str(e[2]).lower(), "sequence", str(i) )
      f.write(rule)
      # windowed time knowledge
      rule = sensor_data( e[1].lower(), str(e[2]).lower(), "windowed", str(get_window( init, e[0] )) )
      f.write(rule)

      f.write("\n")

  # write down ground truth and ground false
  recordf = name + ".pl.f"
  recordn = name + ".pl.n"

  # add two time representations to ground facts
  for i in range(len(groundFacts)):
    rel = groundFacts[i][2][0]-init
    win = get_window( init, groundFacts[i][2][0] )
    groundFacts[i][2].insert(0, rel)
    groundFacts[i][2].append(win)

  # generate positives and negatives - generate only for *sequence* - PROLOG
  ## and memorise activity rules for WEKA
  arffGroundTruth = {}
  arffGroundFacts = groundFacts[:]
  pos = []
  neg = []
  farEnd = len(data)
  while len(groundFacts) != 0:
    # get first
    a = []
    a += [groundFacts.pop(-1)]
    # find all the rest of the activity
    for i in range(len(groundFacts))[::-1]:
      # find same activity for same person
      if groundFacts[i][0] == a[0][0] and groundFacts[i][3] == a[0][3]:
        a.append( groundFacts.pop(i) )
    a.reverse()

    # or the list does not start with *{* and finishes with *}*
    ## some activity is not closed
    if len(a)%2 != 0:
      print "One of the activity blocks is not closed!"
      sys.exit(1)
    ## check for exact closure
    for ai in range(0, len(a), 2):
      if a[ai][1] != 'true' or a[ai+1][1] != 'false' or a[ai][2][2] > a[ai+1][2][2]:
        # print "The same block name used more than once: *", a[0][0], "* !"
        print "Block not closed: *", a[ai][0], "* !"
        print "or"
        print "Wrong block structure!"
        print ">\n", a
        sys.exit(1)
      if ai >= 1:
        if a[ai][2][2] < a[ai-1][2][2]:
          print "Blocks are overlapping!"
          sys.exit(1)

    # get ground true/false for each block
    bottom = 0
    for bn in range(0, len(a), 2):
      # use only *sequence*
      beginning = a[bn][2][2]
      end = a[bn+1][2][2] + 1 # !!!CHANGE!!!: include last command

      # memorise beginning and end for WEKA
      if a[bn][0] in arffGroundTruth:
        arffGroundTruth[a[bn][0]].append( (a[bn][2], a[bn+1][2]) )
      else:
        arffGroundTruth[a[bn][0]] = [(a[bn][2], a[bn+1][2])]

      # check for multiple people
      if multipleResidents:
        PID = ", " + a[bn][3]
      else:
        PID = ""

      # generate for all the events
      for i in range(bottom, beginning):
        neg.append( activityRule + "(" + a[bn][0] + ", " + str(i) + PID + ")." )
      for i in range(beginning, end):
        pos.append( activityRule + "(" + a[bn][0] + ", " + str(i) + PID + ")." )
      # neg.append( activityRule + "(" + a[0][0] + ", " + str(0) + ", " + str(beginning-1) + ")." )
      # pos.append( activityRule + "(" + a[0][0] + ", " + str(beginning) + ", " + str(end-1) + ")." )
      bottom = end

    # finish off
    for i in range(bottom, farEnd):
      neg.append( activityRule + "(" + a[bn][0] + ", " + str(i) + PID + ")." )
    ## generate for one event with range
    # neg.append( activityRule + "(" + a[0][0] + ", " + str(end) + ", " + str(farEnd) + ")." )

  # Write positive and negative examples
  if DOFN:
    with open(recordf, 'wb') as pf:
        pf.write( '\n'.join(pos) )
        pf.write('\n')
    with open(recordn, 'wb') as nf:
        nf.write( '\n'.join(neg) )
        nf.write('\n')


  # code below is just ARFF generation
  if DOARFF:
    if multipleResidents:
      print "ARFF generation for multiple residents (multi-label data) is not supported."
      sys.exit(0)

    # write ARFF file for Weka
    ## relative
    recordRarff = name + ".R.arff"
    ## absolute
    recordAarff = name + ".A.arff"
    ## sequenced
    recordSarff = name + ".S.arff"
    ## windowed
    recordWarff = name + ".W.arff"
    ## date
    recordDarff = name + ".D.arff"
    # prepare data to write & # append time
    Rarff = [atRelation, atAttribute+"time"+atributeN]
    Aarff = [atRelation, atAttribute+"time"+atributeN]
    Sarff = [atRelation, atAttribute+"time"+atributeN]
    Warff = [atRelation, atAttribute+"time"+atributeN]
    Darff = [atRelation, atAttribute+"time DATE"+atributeD]
    # get all sensor names
    sensorNames = []
    for e in data:
      f = e[1].lower()
      ft = atributeTF if type(e[2])==str else atributeN
      if (f, ft) not in sensorNames:
        sensorNames.append( (f, ft) )
    # append attributes
    for e in sensorNames:
      Rarff.append(atAttribute + e[0] + e[1])
      Aarff.append(atAttribute + e[0] + e[1])
      Sarff.append(atAttribute + e[0] + e[1])
      Warff.append(atAttribute + e[0] + e[1])
      Darff.append(atAttribute + e[0] + e[1])
    # prepare classes
    classes = []
    for e in arffGroundFacts:
      if e[0] not in classes:
        classes.append(e[0])
    classesArff = "{"
    for e in classes:
      classesArff += e + ','
    classesArff += 'none}'
    # append target class attribute
    Rarff.append(atClass + classesArff)
    Aarff.append(atClass + classesArff)
    Sarff.append(atClass + classesArff)
    Warff.append(atClass + classesArff)
    Darff.append(atClass + classesArff)
    # include DATA marker
    Rarff.append(atData)
    Aarff.append(atData)
    Sarff.append(atData)
    Warff.append(atData)
    Darff.append(atData)
    # generate data
    ## keep track of current sensors status to generate data
    sensorStatus = {}
    for e in sensorNames:
      sensorStatus[e[0]] = False
    ## keep track of current activity to mark ground truth
    groundTruth = {}
    for e in classes:
      groundTruth[e] = False


    # create common data type
    cdt = []
    for d in data:
      if cdt == []:
        cdt.append( (d[0], d[3], [(d[1], d[2])]) )
      elif d[0] in cdt[-1]:
        cdt[-1][-1].append( (d[1], d[2]) )
      else:
        cdt.append( (d[0], d[3], [(d[1], d[2])]) )

    ## generate data
    i = 0
    currentWindow = None
    for e in cdt:
      for f in e[2]:
        # update sensor status based on current entry
        sensorStatus = updateSensor(f, sensorStatus)

        # get features status
        (racwd, groundTruth) = getSignals(sensorNames, sensorStatus, groundTruth, arffGroundTruth, i)

        # check current class if none give 'none' # detect multi-label issue and report it
        cc = checkLabel(groundTruth)

        # remember that time/date goes first # update sequence
        Sarff.append(str(i) + ',' + racwd + cc)
        # update i
        i += 1

      # update common time-points for Date,
      Darff.append("\"" + e[1] + "\"," + racwd + cc)
      Rarff.append(str(e[0] - init) + "," + racwd + cc)
      Aarff.append(str(e[0]) + ',' + racwd + cc)

      # handle separately windowed case
      if currentWindow != get_window( init, e[0] ):
        currentWindow = get_window( init, e[0] )
        Warff.append(str(currentWindow) + ',' + racwd + cc)


    # write the files
    with open(recordRarff, 'wb') as pf:
      pf.write( '\n'.join(Rarff) )
      pf.write('\n')
    with open(recordAarff, 'wb') as pf:
      pf.write( '\n'.join(Aarff) )
      pf.write('\n')
    with open(recordSarff, 'wb') as pf:
      pf.write( '\n'.join(Sarff) )
      pf.write('\n')
    with open(recordWarff, 'wb') as pf:
      pf.write( '\n'.join(Warff) )
      pf.write('\n')
    with open(recordDarff, 'wb') as pf:
      pf.write( '\n'.join(Darff) )
      pf.write('\n')
