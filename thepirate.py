#!/usr/bin/env python

"""
The Pirate Bay scraper - This is the client

Uses 3 external libraries for scraping HTML elements from ThePirateBay and interacting with transmission-daemon.
Asks user for a search selection, offers a list of choices, and grabs the magnet link for the selection in a menu style fashion.

"""

__author__ = 'LANCE - https://github.com/lalanza808'

##################################################
# Libraries

# Built-in libraries
from os import path
import argparse

# 3rd party libraries
import requests
import bs4
import transmissionrpc

##################################################
# Variables

# Dictionaries/Arrays for storing search results
tpb_search_results = {}
tpb_torrent_links = []
user_torrent_selection = ""

# Current/working PirateBay URL
tpb = "https://thepiratebay.se"

# Torrent server IP; can be any machine running transmission-daemon 
# with a firewall inbound allowed to TCP/9091 (transmissionrpc)
rpcserver = []

# Squelch HTTPS insecure warnings
requests.packages.urllib3.disable_warnings()

##################################################
# Parsing and Arguments

parser = argparse.ArgumentParser(description='Scrape The Pirate Bay for torrents.')
parser.add_argument('--query', '-q', dest='arg_search_string', help='The query string to search for on TPB', required=False)
parser.add_argument('--top', '-t', dest='arg_take_top', action='store_true', help='Automatically grab the torrent with most seeds', required=False)
parser.add_argument('--file', '-f', dest='arg_magnet_link', help='Direct link to magnet link or torrent file', required=False)
parser.add_argument('--url', '-u', dest='arg_torrent_page', help='URL of the torrent on TPB', required=False)
parser.add_argument('--server', '-s', dest='arg_server_host', help='IP/hostname of the Transmission server', required=False)

args = parser.parse_args()

##################################################
# Functions

#1
def Check_Transmission_Listener():
	"""
	Checks to see if transmission-daemon is listening on rpcserver
	and initiates the function to ask user for input
	"""
	if not rpcserver and not args.arg_server_host:
		print "No Transmission server specified! Quitting!"
		exit(9)
	elif args.arg_server_host:
		rpcserver.append(args.arg_server_host)
	try:
		transmissionrpc.Client(rpcserver[0], port=9091)
		Get_Search_URL()
	except KeyboardInterrupt:
		print "\n\nBye."
		exit(1)
	except transmissionrpc.error.TransmissionError:
		print "[!] Transmission-daemon not listening on {}!".format(rpcserver[0])
		exit(2)

#2	
def Get_Search_URL():
	"""
	Takes input string to search for on TPB.
	Formats string into proper url
	Gets HTML source of search page for use in the next function
	"""
	#If magnet link supplied, directly add to queue, exit script
	if args.arg_magnet_link:
		transmissionrpc.Client(rpcserver[0]).add_torrent(args.arg_magnet_link)
		exit(0)
	#If URL supplied, skip to Download_Torrent_From_URL function
	elif args.arg_torrent_page:
		Download_Torrent_From_URL(args.arg_torrent_page)
		exit(0)
	#If search string provided, use it for Get_Torrent_Links function
	elif args.arg_search_string:
		tpb_search_string = args.arg_search_string
	#If nothing supplied, ask user for search string
	else:
		tpb_search_string = raw_input("[+] What would you like to search?\n>>> ")

	tpb_search_url = "{}/search/{}/0/7/0".format(tpb, tpb_search_string) #/0/7/0 tells TPB to sort descending by seeds
	tpb_torrent_page_source = requests.get(tpb_search_url, verify=False).text #Use requests lib to fetch page source for bs4 parsing

	Get_Torrent_Links(tpb_torrent_page_source) #Run Get_Torrent_Links function, passing page source for BS4 parsing
	
#3
def Get_Torrent_Links(source):
	"""
	Takes the page source and parses it with BeautifulSoup.
	Finds all anchor elements on the page, pre-sorted by seeders
	Enumerates list of elements, and adds them to tpb_search_results dictionary
	"""
	print "\n"
	global tpb_torrent_links, tpb_search_results

	#Update the tpb_torrent_links array with the returned torrents
	tpb_torrent_page_soup = bs4.BeautifulSoup(source, "html.parser") #Create Beautiful Soup object
	for link in tpb_torrent_page_soup.find_all('a'): #Find all anchor elements in page source
		if link.get('href').startswith('/torrent'): #Only get links with /torrent as they're valid torrent pages
			tpb_torrent_links.append(link.get('href')) #Set the results to tpb_torrent_links array
	
	#If -t is supplied, bypass this section of code and go on to download the top torrent
	if args.arg_take_top and tpb_torrent_links:
		Download_Torrent_From_URL("{}/{}".format(tpb, tpb_torrent_links[0]))
	#Print links in numeric order to the user
	else:
		for number,link in enumerate(tpb_torrent_links): #Enumerate the array so the numbers start at 0
			tpb_search_results.update({number:link}) #Append results to tpb_search_results dictionary
			print "({}) {}".format(number, path.basename(link))
		if tpb_search_results: #If dict is not empty, continue with script
			print "\n(98) Search again"
			print "(99) Exit"
			Get_User_Selection()
		else: #If dict is empty (no results from search) re-run script
			print "\nNo results found. Try again."
			tpb_search_results = {}
			tpb_torrent_links = []
			args.arg_search_string = ''
			Get_Search_URL() #Loop back to script start

#4	
def Get_User_Selection():
	"""
	Asks for selection of torrent
	"""
	global tpb_torrent_links, tpb_search_results

	#Ask user for numeric selection
	try:
		selection = int(raw_input("\n[+] Enter the number of the torrent to download.\n>>> "))
		#Zeroize variables, loop back to script start
		if selection == 98:
			print "\nStarting over"
			tpb_search_results = {}
			tpb_torrent_links = []
			args.arg_search_string = ''
			Get_Search_URL()
		#Exit script
		elif selection == 99:
			print "\nBye.\n"
			exit() 
		#If valid number, move to next function to add to queue
		elif selection in tpb_search_results: 
			user_torrent_selection = tpb_search_results[selection] #Updates variable based on key provided above, matches it with tpb_search_results dict
			Download_Torrent_From_URL("{}/{}".format(tpb, user_torrent_selection))
		#If anything other than 98, 99, or valid key number entered, loop back to selection input
		else: 
			print "\nNot a valid number"
			Get_User_Selection()
	#If number isn't used, loop back to selection input
	except ValueError:
		print "\nThat is not a digit."
		Get_User_Selection()
	
#5
def Download_Torrent_From_URL(tpb_torrent_url):
	"""
	Grabs the first magnet link and adds it to the queue via RPC to rpcserver
	"""
	tpb_magnet_links = []
	tpb_torrent_page = requests.get(tpb_torrent_url, verify=False)
	tpb_torrent_page_soup = bs4.BeautifulSoup(tpb_torrent_page.content, "html.parser")

	for link in tpb_torrent_page_soup.find_all('a'):
		if str(link.get('href')).startswith('magnet:?xt'):
			tpb_magnet_links.append(link.get('href'))

	tpb_magnet_link = tpb_magnet_links[0]
	print "\n[+] Adding magnet link for torrent:\n\n{}".format(tpb_torrent_url)
	transmissionrpc.Client(rpcserver[0]).add_torrent(tpb_magnet_link)
	print "\n[.] Done!\n"
	exit(0)	
	
if __name__ == "__main__":
	Check_Transmission_Listener()
