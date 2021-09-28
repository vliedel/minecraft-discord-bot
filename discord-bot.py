#!/usr/bin/env python3

import requests
import subprocess
import re

filename = "/home/minecraft/mc/logs/latest.log"

f = subprocess.Popen(['tail', '-Fn1', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# [07:54:07] [Server thread/INFO]: 4poc joined the game
regexJoined = re.compile("\[\d+:\d+:\d+\] \[Server thread.INFO\]: (\S+ joined the game)")
regexLeft = re.compile("\[\d+:\d+:\d+\] \[Server thread.INFO\]: (\S+ left the game)")

while True:
	line = f.stdout.readline().decode('utf-8')
	print(line)
	match = regexJoined.match(line)
	if match:
		print("match:", match.group(1))
		r = requests.post('https://discord.com/api/webhooks/890145466682073118/Lv4JTiVZ1d-5ZEXMS2PT9_HLbinDZMun5DAGYTDnoyiLQgl38yJY4enlrvuKbuE17zmj', data={'content': match.group(1)})
		print(r)
	match = regexLeft.match(line)
	if match:
		print("match:", match.group(1))
		r = requests.post('https://discord.com/api/webhooks/890145466682073118/Lv4JTiVZ1d-5ZEXMS2PT9_HLbinDZMun5DAGYTDnoyiLQgl38yJY4enlrvuKbuE17zmj', data={'content': match.group(1)})
		print(r)
