# QIC - Quick Interface Checker

Have you ever used [STG](http://leonidvm.chat.ru/) to graph the interface utilization of a device? And maybe you were also using [Getif](http://www.wtcs.org/snmp4tpc/getif.htm) to get the specific interface OID to feed STG with? If so, you'll quickly understand why I've wrote this app: to combine the two!

Well, to be honest I've also done to overcome what seems to be a limitation of STG, that supposedly is capable of using SNMP v2c but apparently it doesn't.

However, this is a simple tool to get a graph out of the traffic entering and leaving a specific interface on an SNMP device: enter the ip and the v1/v2c community, click "Scan" to get a list of the available interfaces (it's up to you if you want to have also the status and the description of each one) and then select the one you are looking for from the list. Tadah!
