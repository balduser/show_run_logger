# show_run_logger
The tool for making a backup of 'show running' configuration for a list of Eltex commutators and finding changes in it

## Requires  
Excsript  
`pip install Exscript`

## Tested on  
Windows, Eltex MES2324

### How it works:
Creates a folder and consequently requests `show run` from a list of commutators (ips.txt should be placed in the folder of script) into distinct files. Then compares these files with previous versions to find changes in them. Example of comparison:

```
Previous:
interface gigabitethernet1/0/4
loopback-detection enable
no shutdown
description internet_office
snmp trap link-status
mtu 0
spanning-tree disable
spanning-tree bpdu filtering
switchport access vlan 111
exit

Current:
interface gigabitethernet1/0/4
loopback-detection enable
no shutdown
description internet_office
snmp trap link-status
mtu 0
spanning-tree bpdu filtering
switchport access vlan 111
exit
```

Writes changes to a log file.
