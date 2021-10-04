#!/usr/bin/env python3

import requests
import subprocess
import re
import argparse
import logging

argParser = argparse.ArgumentParser(description="Relays minecraft messages to discord.")
argParser.add_argument('--minecraft_log_file',
                       '-f',
                       dest = 'minecraft_log_filename',
                       metavar = 'filename',
                       type = str,
                       required = True,
                       help = 'The file that holds the latest minecraft logs.')
argParser.add_argument('--webhook',
                       '-w',
                       dest = 'webhook',
                       metavar = 'link',
                       type = str,
                       required = True,
                       help = 'The webhook link given by discord. For example: https://discord.com/api/webhooks/890145466682073118/Lv4JTiVZ1d-5ZEXMS2PT9_HLbinDZMun5DAGYTDnoyiLQgl38yJY4enlrvuKbuE17zmj')
argParser.add_argument('--verbose',
                       '-v',
                       dest = 'verbose',
                       action = 'store_true',
                       help = 'Verbose output.')
args = argParser.parse_args()


########## Prepare logger ##########

log_format = '[%(asctime)s.%(msecs)03d] [%(filename)-20.20s:%(lineno)3d] %(levelname)-1.1s %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'

log_level = logging.INFO
if args.verbose:
	log_level = logging.DEBUG

logging.basicConfig(format=log_format, level=log_level, datefmt=log_date_format)

########## Prepare regexes ##########

# [07:54:07] [Server thread/INFO]: 4poc joined the game
# match.group(1) will be the part after the prefix "[07:54:07] [Server thread/INFO]: "
regex_log_line = re.compile("\[\d+:\d+:\d+\] \[Server thread.INFO\]: (.+)")

# [07:54:07] [Server thread/INFO]: 4poc joined the game
# match.group(1) will be the player name
regex_joined = re.compile("(\S+) joined the game")
regex_left = re.compile("(\S+) left the game")

# [11:00:01] [Server thread/INFO]: There are 0 of a max of 20 players online:
# [15:00:01] [Server thread/INFO]: There are 1 of a max of 20 players online: hysterina
# [22:00:01] [Server thread/INFO]: There are 2 of a max of 20 players online: 4poc, TheFlyingCorpse
# match.group(1) will be the player count
# match.group(2) will be the max player count
# match.group(3) will be the player names
regex_player_count = re.compile("There are (\d+) of a max of (\d+) players online:(.*)")

# [05:44:02] [Server thread/INFO]: Starting minecraft server version 1.17.1
# [05:44:07] [Server thread/INFO]: Time elapsed: 4380 ms
# [05:44:07] [Server thread/INFO]: Done (4.511s)! For help, type "help"
regex_server_start = re.compile("Starting minecraft server version .*")

# [05:35:21] [Server thread/INFO]: Stopping the server
# [05:35:21] [Server thread/INFO]: Stopping server
regex_server_stop = re.compile("Stopping the server")



# [11:19:10] [Server thread/INFO]: 4poc was slain by Zombie
# [00:02:43] [Server thread/INFO]: 4poc fell from a high place
# [00:03:29] [Server thread/INFO]: 4poc fell from a high place
# [00:04:44] [Server thread/INFO]: 4poc was slain by Piglin
# See https://minecraft-archive.fandom.com/wiki/Death_Message
regexes_death_message = []
# Arrows
regexes_death_message.append(re.compile("was shot by .*"))
# Snowballs
regexes_death_message.append(re.compile("was pummeled by .*"))
# Cactus
regexes_death_message.append(re.compile("was pricked to death"))
regexes_death_message.append(re.compile("walked into a cactus whilst trying to escape .*"))
# Drowning
regexes_death_message.append(re.compile("drowned.*"))
# Elytra
regexes_death_message.append(re.compile("experienced kinetic energy.*"))
# Explosions
regexes_death_message.append(re.compile("blew up"))
regexes_death_message.append(re.compile("was blown up by .*"))
regexes_death_message.append(re.compile("was killed by.*"))
# Falling
regexes_death_message.append(re.compile("hit the ground too hard.*"))
regexes_death_message.append(re.compile("fell.*"))
regexes_death_message.append(re.compile("was impaled on .*"))
# Falling blocks
regexes_death_message.append(re.compile("was squashed by .*"))
# Fire
regexes_death_message.append(re.compile("went up in flames"))
regexes_death_message.append(re.compile("walked into fire.*"))
regexes_death_message.append(re.compile("burned to death"))
regexes_death_message.append(re.compile("was burnt to a crisp.*"))
# Firework rockets
regexes_death_message.append(re.compile("went off with a bang.*"))
# Lava
regexes_death_message.append(re.compile("tried to swim in lava.*"))
# Lightning
regexes_death_message.append(re.compile("was struck by lightning.*"))
# Magma block
regexes_death_message.append(re.compile("discovered the floor was lava"))
regexes_death_message.append(re.compile("walked into danger zone due to .*"))
# Magic
regexes_death_message.append(re.compile("was killed by .*"))
# Powder snow
regexes_death_message.append(re.compile("froze to death.*"))
# Players and mobs
regexes_death_message.append(re.compile("was slain by .*"))
regexes_death_message.append(re.compile("was fireballed by .*"))
regexes_death_message.append(re.compile("was stung to death"))
regexes_death_message.append(re.compile("was shot by a skull from .*"))
# Starving
regexes_death_message.append(re.compile("starved to death.*"))
# Suffocation
regexes_death_message.append(re.compile("suffocated in a wall.*"))
regexes_death_message.append(re.compile("was squished too much"))
regexes_death_message.append(re.compile("was squashed by .*"))
# Sweet Berry Bushes
regexes_death_message.append(re.compile("was poked to death by a sweet berry bush.*"))
# Thorns enchantment
regexes_death_message.append(re.compile("was killed (by .*)? trying to hurt .*"))
# Trident
regexes_death_message.append(re.compile("was impaled by .*"))
# Void
regexes_death_message.append(re.compile("fell out of the world"))
regexes_death_message.append(re.compile("didn't want to live in the same world as .*"))
# Wither effect
regexes_death_message.append(re.compile("withered away.*"))



########## Main ##########

players_online = set()
max_player_count = 20

f = subprocess.Popen(['tail', '-Fn1', args.minecraft_log_filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def send_discord_msg(text: str):
	logging.debug(f"send discord msg: {text}")
	reply = requests.post(args.webhook, data={'content': text})
	logging.debug(reply)

def get_player_names() -> str:
	player_names = ""
	for p in players_online:
		player_names += f"{p}, "
	return player_names[0:-2]

def get_online_msg() -> str:
	msg = f"[{len(players_online)} / {max_player_count}] online"
	if len(players_online):
		return f"{msg}: {get_player_names()}"
	else:
		return msg


while True:
	line = f.stdout.readline().decode('utf-8')
	line = line.rstrip()
	logging.debug(f"log: {line}")
	match = regex_log_line.match(line)
	if not match:
		continue

	line = match.group(1)
	logging.debug(f"line: {line}")


	match = regex_server_start.match(line)
	if match:
		send_discord_msg(line)
		players_online.clear()

	match = regex_server_stop.match(line)
	if match:
		send_discord_msg(line)
		players_online.clear()


	match = regex_joined.match(line)
	if match:
		player_name = match.group(1)
		players_online.add(player_name)
		logging.debug(f"joined: {player_name}, online: {players_online}")
		send_discord_msg(f"{player_name} joined. {get_online_msg()}")

	match = regex_left.match(line)
	if match:
		player_name = match.group(1)
		players_online.discard(player_name)
		logging.debug(f"left: {player_name}, online: {players_online}")
		send_discord_msg(f"{player_name} left. {get_online_msg()}")

	match = regex_player_count.match(line)
	if match:
		logging.debug(f"players: count={match.group(1)} max={match.group(2)} players={match.group(3)}.")
		player_count = match.group(1)
		max_player_count = match.group(2)
		players = match.group(3).strip()

		players_online.clear()
		if len(players):
			players = players.split(',')
			for p in players:
				players_online.add(p.strip())
		logging.debug(f"online: {players_online}")

	split = line.split(' ', 1)
	if len(split) == 2:
		for p in players_online:
			if split[0] == p:
				found = False
				for r in regexes_death_message:
					if r.match(split[1]):
						send_discord_msg(line)
						found = True
						break
				if not found:
					logging.debug(f"death message?? {line}")
				break

