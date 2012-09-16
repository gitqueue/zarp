import os, sys, gc
sys.path[:0] = [str(os.getcwd()) + '/modules/sniffer/', str(os.getcwd()) + '/modules/dos/', 
				str(os.getcwd()) + '/modules/poison/', str(os.getcwd())+'/modules/scanner/',
				str(os.getcwd()) + '/modules/parameter/'] 
from arp import ARPSpoof
from dns import DNSSpoof
from dhcp import DHCPSpoof
from password_sniffer import PasswordSniffer
from http_sniffer import HTTPSniffer
from net_map import NetMap
from wep_crack import WEPCrack
import dhcp, ndp_dos, nestea_dos, land_dos, smb2_dos,dhcp_starvation,service_scan
import ap_scan

#
# Main data bus for interacting with the various modules.  Dumps information, initializes objects,
# and houses all of the objects necessary to create/get/dump/stop the sniffers/poisoners.
#
# All around boss.
#

arp_sessions = {}
http_sniffers = {}
password_sniffers = {}
global netscan,rogue_dhcp	#dont manage 'many' of these; just overwrite the history of one
netscan = rogue_dhcp = None

#
# Initialize a poisoner and/or DoS attack and store the object
# TODO rework this so it doesn't turn into a HUGE if/elif/elif/elif...
#
def initialize(module):
	global netscan,rogue_dhcp
	print '[dbg] Received module start for: ', module
	if module == 'arp':
		tmp = ARPSpoof() 
		to_ip = tmp.initialize()
		if not to_ip is None:
			print '[dbg] Storing session for ', to_ip
			arp_sessions[to_ip] = tmp
			print '[dbg] is running: ',arp_sessions[to_ip].isRunning()
		del(tmp)
	elif module == 'dns':
		dump_module_sessions('arp')
		(module, number) = get_session_input()
		ip = get_key(module,number)
		if not ip is None:
			arp_sessions[ip].init_dns_spoof()
	elif module == 'dhcp':
		tmp = DHCPSpoof()
		if tmp.initialize():
			rogue_dhcp = tmp
	elif module == 'ndp':
		ndp_dos.initialize()	
	elif module == 'http_sniffer':
		tmp = HTTPSniffer()
		to_ip = tmp.initialize()
		if not to_ip is None:
			print '[dbg] Storing sniffer for ', to_ip
			http_sniffers[to_ip] = tmp
	elif module == 'password_sniffer':
		tmp = PasswordSniffer()
		to_ip = tmp.initialize()
		if not to_ip is None:
			print '[dbg] Storing session for ', to_ip
			password_sniffers[to_ip] = tmp
	elif module == 'nestea':
		nestea_dos.initialize()
	elif module == 'land':
		land_dos.initialize()
	elif module == 'smb2':
		smb2_dos.initialize()
	elif module == 'net_map':
		netscan = NetMap()
		netscan.initialize()
	elif module == 'service_scan':
		service_scan.initialize()
	elif module == 'dhcp_starv':
		dhcp_starvation.initialize()
	elif module == 'ap_scan':
		ap_scan.initialize()	
	elif module == 'wep_crack':
		tmp = WEPCrack()
		tmp.initialize()
	else:
		print '[-] Module \'%s\' does not exist.'%module

#
# Dump running sessions
#
def dump_sessions():
	global arp_sessions, dns_sessions, rogue_dhcp, netscan
	print '\n\t[Running sessions]'
	if len(arp_sessions) > 0: print '[!] ARP POISONS [arp]:'
	for (counter, session) in enumerate(arp_sessions):
		print '\t[%d] %s'%(counter, session)
		if arp_sessions[session].dns_spoof:
			print '\t|-> [!] DNS POISONS [dns]:'
			for (counter,key) in enumerate(arp_sessions[session].dns_spoofed_pair):
				print '\t|--> [%d] %s -> %s'%(counter,key,arp_sessions[session].dns_spoofed_pair[key])
	if len (http_sniffers) > 0: print '[!] HTTP SNIFFERS [http]:'
	for (counter, session) in enumerate(http_sniffers):
		print '\t[%d] %s'%(counter, session)
	if len(password_sniffers) > 0: print '[!] PASSWORD SNIFFERS [pass]:'
	for (counter, session) in enumerate(password_sniffers):
		print '\t[%d] %s'%(counter, session)
	if not netscan is None:
		# we dont save a history of scans; just the last one
		print '\n[0] NetMap Scan [netmap]'
	if not rogue_dhcp is None:
		print '\n[1] Rogue DHCP [dhcp]'
	print '\n'

#
# Dump the sessions for a specific module
#
def dump_module_sessions(module):
	global arp_sessions, dns_sessions, dhcp_sessions, dhcp_spoof
	if module == 'arp':
		print '\n\t[Running ARP sessions]'
		for (counter, session) in enumerate(arp_sessions):
			print '\t[%d] %s'%(counter, session)
	elif module == 'dns':
		print '\n\t[Running DNS sessions]'
		for (counter, session) in enumerate(arp_sessions):
			if session.dns_spoof:
				print '\t[%d] %s'%(counter, session)
	elif module == 'dhcp':
		if not rogue_dhcp is None and rogue_dhcp.running:
			print '[-] not yet'
#
# Return the total number of running sessions
#
def get_session_count():
	return len(arp_sessions) + len(http_sniffers)+ len(password_sniffers)

#
# Stop a specific session; this calls the .shutdown() method for the given object.
# All modules are required to implement this method.
# @param module is the module
# @param number is the session number (beginning with 0)
#
def stop_session(module, number):
	global rogue_dhcp
	ip = get_key(module, number)
	if not ip is None:
		if module == 'arp':
			print '[dbg] killing ARP session for ip ', ip
			if arp_sessions[ip].shutdown():
				del(arp_sessions[ip])
		elif module == 'dns':
			print '[dbg] killing DNS sessions for ip ', ip
			arp_sessions[ip].stop_dns_spoof()
			print '[dbg] is dns running anymore: ',arp_sessions[ip].dns_spoof
		elif module == 'ndp':
			print '[-] Not implemented'
		elif module == 'http':
			print '[dbg] killing HTTP sniffer for ip ', ip
			if http_sniffers[ip].shutdown():
				del(http_sniffers[ip])
		elif module == 'pass':
			print '[dbg] killing password sniffer for ip ', ip
			if password_sniffers[ip].shutdown():
				del(password_sniffers[ip])
	elif module == 'all' and number == -1:
		# this is the PANIC KILL ALL signal
		print '[!] Shutting all sessions down...'
		for i in arp_sessions:
			arp_sessions[i].shutdown()
		for i in http_sniffers:
			http_sniffers[i].shutdown()
		for i in password_sniffers:
			password_sniffers[i].shutdown()
	elif module == 'dhcp':
		# dhcp is a different story
		if not rogue_dhcp is None:
			rogue_dhcp.shutdown()
			rogue_dhcp = None
	else:
		print '[-] Module could not be stopped.'
	gc.collect()

#
# Some sniffers have information to dump, so for those applicable, this'll initiate it.
# Module should implement the .view() method for dumping information to.
#
def view_session(module, number):
	global netscan
	ip = get_key(module, number)
	if module == 'netmap':
		print '[dbg] dumping netmap scan'
		netscan.view()
	elif not ip is None:
		if module == 'http':
			print '[dbg] beginning HTTP dump for ip ', ip
			http_sniffers[ip].view()
		elif module == 'pass':
			print '[dbg] beginning password dump for ip ', ip
			password_sniffers[ip].view()
		elif module == 'arp' or module == 'dns':
			print '[dbg] beginning ARP/DNS dump for ',ip
			arp_sessions[ip].view()
	else:
		return

#
# Start logging a session
#
def start_log_session(module, number, file_location):
	ip = get_key(module, number)
	if not ip is None:
		if module == 'http':
			print '[dbg] Starting http logger..'
			http_sniffers[ip].log(True, file_location)
		elif module == 'pass':
			print '[dbg] Starting password logger..'
			password_sniffers[ip].log(True, file_location)
		else:
			print '[-] Module \'%s\' does not have a logger.'%module
	else:
		print '[-] %s session \'%s\' could not be found.'%(module, number)
		print '[-] Logging canceled.'

#
# Stop logging a session 
#
def stop_log_session(module, number):
	ip = get_key(module, number)
	if not ip is None:
		if module == 'http':
			print '[dbg] Stopping http logger..'
			http_sniffers[ip].log(False, None)
		elif module == 'pass':
			print '[dbg] Stopping pass logger..'
			password_sniffers[ip].log(False, None)
		else:
			print '[-] Module \'%s\' does not have a logger.'%module 
	else:
		print '[-] %s session \'%s\' could not be found.'%(module, number)
		print '[-] Logging could not be stopped.'
#
# Internal function for grabbing IP address from a module/index
#
def get_key(module, number):
	if module == 'http':
		if len(http_sniffers) <= number:
			print '[-] Invalid session number (0-%d)'%len(http_sniffers)
			return None
		return http_sniffers.keys()[number]
	elif module == 'pass':
		if len(password_sniffers) <= number:
			print '[-] Invalid session number (0-%d)'%len(password_sniffers)
			return None
		return password_sniffers.keys()[number]
	elif module == 'arp' or module == 'dns':
		if len(arp_sessions) <= number:
			print '[-] Invalid session number (0-%d)'%len(arp_sessions)
			return None
		return arp_sessions.keys()[number]
	elif module == 'none' and number == -1:
		return None
	return None

#
#
#
def get_session_input():
	try:
		tmp = raw_input('[module] [number]> ')
		(module, number) = tmp.split(' ')
		print '[dbg] got: %s and %s'%(module, number)
		if not module is None and not number is None:
			return (str(module), int(number))
	except Exception: 
		print '[-] Error: Must specify [module] followed by [number]\n'
		return (None, None)

#
#
#
def view_info (module):
	if module == 'http':
		HTTPSniffer().info()	
