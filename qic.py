import PySimpleGUI as sg
from pysnmp.hlapi import *
import re
import time
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import sys

# Settings

matplotlib.use("TkAgg")
sg.theme('GrayGrayGray')
progressBarLimit = 1000
format_string = '{:9} {:20} {:8} {}'

# Functions

def snmpWalk(host, community, oid, progressSteps):
    results = []
    i = 1
    step = int(progressBarLimit) / int(progressSteps)
    for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(SnmpEngine(), CommunityData(community), UdpTransportTarget((host, 161), timeout = 5.0), ContextData(), ObjectType(ObjectIdentity(oid)), lexicographicMode = False):
        if errorIndication:
            print(errorIndication, file = sys.stderr)
            break
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'), file = sys.stderr)
            break
        else:
            for varBind in varBinds:
                i = i + step
                progress_bar.UpdateBar(i)
                results.append(varBind)
    progress_bar.UpdateBar(0)
    return results

def snmpGet(host, community, oid):
    results = []
    iterator = getCmd(SnmpEngine(), CommunityData(community, mpModel = 0), UdpTransportTarget((host, 161), timeout = 5.0), ContextData(), ObjectType(ObjectIdentity(oid)))
    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            results.append(varBind)
    return results

def drawFigure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side = "top", fill = "both", expand = 1)
    return figure_canvas_agg

def getMePoints(data):
    lenght = len(data)
    if lenght > 1:
        diff = 0
        distance = 1
        while diff == 0:
            step = 1+distance
            if step < lenght:
                diff = int(data[lenght-1]) - int(data[lenght-(step)])
                if diff == 0:
                    distance = distance + 1
                    window["-MISS-"].update('Missed a reading. Maybe you should increase the frequency.')
                else:
                    window["-MISS-"].update('')
                    if diff < 0:
                        diff = 4294967295 - int(data[lenght-(step)]) + int(data[lenght-1])
                    return diff
            else:
                break

# Window layout

layout = [
    [sg.Text('Target IP address:'), sg.InputText('', size = (20, 1)), sg.Text('SNMP community:'), sg.InputText('', size = (20, 1)), sg.Checkbox('Get status'), sg.Checkbox('Get description'), sg.Button('Scan'), sg.Text('Hostname: '), sg.Text(key = "-HOSTNAME-"), sg.Text(text_color = "red", key = "-ACTION-")],
    [sg.ProgressBar(progressBarLimit, orientation = 'h', size = (101, 20), key = '-PROGRESSBAR-')],
    [sg.Listbox(font = ("Courier New", 9), values = [], enable_events = True, size = (185, 10), key = "-INTERFACE LIST-")],
    [sg.Text('Frequency (sec):'), sg.InputText('2', size = (5, 1)), sg.Text('History (steps):'), sg.InputText('50', size = (5, 1)), sg.Text('Unit:'), sg.Spin(['Kilo','Mega','Giga'], initial_value = 'Kilo'), sg.Button('Update'), sg.Text(key = "-LOADING-"), sg.Text(key = "-MISS-")],
    [sg.Canvas(key = "-CANVAS 1-"), sg.Canvas(key = "-CANVAS 2-")]
]

window = sg.Window('QIC - Quick Interface Checker (Alpha)', layout, finalize = True, resizable = True, location = (0, 0))
progress_bar = window['-PROGRESSBAR-']

# Incoming traffic graph

figIn = plt.figure(figsize = (6.5, 4))
axIn = figIn.add_subplot(111)
figIn_agg = drawFigure(window['-CANVAS 1-'].TKCanvas, figIn)

# Outgoing traffic graph

figOut = plt.figure(figsize = (6.5, 4))
axOut = figOut.add_subplot(111)
figOut_agg = drawFigure(window['-CANVAS 2-'].TKCanvas, figOut)

# Variables initialization

timeToRunAgain = 0
host = ''
community = ''
ifOid = ''
dataIn = []
dataOut = []
tempIn = []
tempOut = []
dataInPoints = []
dataOutPoints = []

# Main loop

while True:
    event, values = window.read(timeout = 20)
    
    if event == sg.WIN_CLOSED: # If the user closes the window
        break
    
    elif event == "Scan": # If a scan is initiated
        
        # Check if the fields are ok.
        if values[0] == '':
            sg.popup('Missing target!')
        else:
            host = values[0]
        if values[1] == '':
            sg.popup('Missing community!')
        else:
            community = values[1]
        
        # If everything is ok, then get data
        if host != '' and community != '':
            try:
                hostname = str(snmpGet(host,community,'1.3.6.1.2.1.1.5.0')[0]).split(' = ')[1].strip() # Get the hostname
                window["-HOSTNAME-"].update(hostname)
                interfaceCount = int(str(snmpGet(host,community,'1.3.6.1.2.1.2.1.0')[0]).split(' ')[-1]) # Get the number of interfaces
                window["-ACTION-"].update("Loading interface list...")
                interfaces = snmpWalk(host,community,'1.3.6.1.2.1.2.2.1.2',interfaceCount) # Get the interfaces names
                if values[2] == True:
                    window["-ACTION-"].update("Loading interface status...")
                    status = snmpWalk(host,community,'1.3.6.1.2.1.2.2.1.8',interfaceCount) # Get the interfaces statuses
                if values[3] == True:
                    window["-ACTION-"].update("Loading interface description...")
                    descriptions = snmpWalk(host,community,'1.3.6.1.2.1.31.1.1.1.18',interfaceCount) # Get the interfaces descriptions
                window["-ACTION-"].update("")
                
                # Create the list to display
                listList = []
                for i in range(0, len(interfaces)):
                    intOid = str(interfaces[i][0]).split('.')[-1]
                    intName = str(interfaces[i][1])
                    if values[2] == True:
                        rawStatus = str(status[i][1])
                        if rawStatus == '1':
                            intStatus = 'UP'
                        else:
                            intStatus = 'DOWN'
                    else:
                        intStatus = ''
                    if values[3] == True:
                        intDesc = str(descriptions[i][1])
                    else:
                        intDesc = ''
                    
                    listElement = format_string.format(str(intOid), intName, str(intStatus), intDesc)
                    listList.append(listElement)
                
                # Display the interfaces
                window["-INTERFACE LIST-"].update(listList)

            except Exception as message: # If something goes wrong, display a popup message
                sg.popup("ERROR: Unable to connect to " + str(host) + ". Error message: "+ str(message))
            
    elif event == "-INTERFACE LIST-" or event == "Update": # If an interface is chosen from the listbox or the user changed settings
        ifData = values["-INTERFACE LIST-"]
        ifOid = str(ifData[0]).split(' ')[0]
        frequency = values[4]
        steps = values[5]
        unit = values[6]
        dataIn = []
        dataOut = []
        tempIn = []
        tempOut = []
        dataInPoints = []
        dataOutPoints = []
        axIn.clear()
        figIn_agg.draw()
        axOut.clear()
        figOut_agg.draw()
        timeToRunAgain = int(time.time())
    
    elif host != '' and ifOid != '': # The real main loop that updates the graphs
        now = int(time.time())
        if now > timeToRunAgain:
            try:
                inSnmpData = snmpGet(host,community,'1.3.6.1.2.1.2.2.1.10.' + ifOid)
                outSnmpData = snmpGet(host,community,'1.3.6.1.2.1.2.2.1.16.' + ifOid)
                ifBandwidth = re.sub(' = ','', str(re.findall(' = .*', str(snmpGet(host,community,'1.3.6.1.2.1.2.2.1.5.' + ifOid)[0]))[0]))
                
                ifInOctets = 0
                if len(inSnmpData) > 0:
                    inResults = re.findall(' = .*', str(inSnmpData[0]))
                    if len(inResults) > 0:
                        ifInOctets = re.sub(' = ','', str(inResults[0]))
                ifOutOctets = 0
                
                if len(outSnmpData) > 0:
                    outResults = re.findall(' = .*', str(outSnmpData[0]))
                    if len(outResults) > 0:
                        ifOutOctets = re.sub(' = ','', str(outResults[0]))
                
                timeToRunAgain = int(time.time()) + int(frequency)
                dataIn.append(ifInOctets)
                dataOut.append(ifOutOctets)
            except Exception as message:
                timeToRunAgain = now * 2
                        
            d = 1
            if unit == 'Kilo':
                d = 1000
            elif unit == 'Mega':
                d = 1000000
            elif unit == 'Giga':
                d = 1000000000
                       
            inUsage = 0
            datapointIn = getMePoints(dataIn)
            if datapointIn != None:
                tempIn.append(datapointIn/d)
                inUsage = (datapointIn / int(ifBandwidth))*100
            
            outUsage = 0
            datapointOut = getMePoints(dataOut)
            if datapointOut != None:
                tempOut.append(datapointOut/d)
                outUsage = (datapointOut / int(ifBandwidth))*100
            
            dataInPoints = tempIn[-(int(steps)):]
            dataOutPoints = tempOut[-(int(steps)):]

            if len(dataInPoints) > 0:
                if dataInPoints[0] > 0:
                    window["-LOADING-"].update('Done')
            elif len(dataOutPoints) > 0:
                if dataOutPoints[0] > 0:
                    window["-LOADING-"].update('Done')
            else:
                window["-LOADING-"].update('Loading...')

            ind = np.arange(len(dataInPoints))
            axIn.clear()
            axIn.bar(ind, dataInPoints, color = 'green', width = 1, align = 'edge')
            axIn.set_title("Incoming " + unit + "bytes (Utilization: " + str(int(inUsage)) + "%)")
            axIn.set_xlim(0, int(steps))
            figIn_agg.draw()
            
            ind = np.arange(len(dataOutPoints))
            axOut.clear()
            axOut.set_title("Outgoing " + unit + "bytes (Utilization: " + str(int(outUsage)) + "%)")
            axOut.set_xlim(0, int(steps))
            axOut.bar(ind, dataOutPoints, color = 'green', width = 1, align = 'edge')
            
            figOut_agg.draw()

window.close()