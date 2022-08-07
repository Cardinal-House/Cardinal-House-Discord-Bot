import discord
import sys
import os
import json
import datetime

from BotPrograms.TokenStatistics import *
from BotPrograms.CardinalPoints import *

intents = discord.Intents.all()
client = discord.Client(intents=intents)

adminUsersDefault = ["colepm#6118", "Zachlm#3699"]
levelBot = "THE CARDINAL#6089"
# levelBot = "colepm#6118"
levelMessageFull = "GG @user, you just advanced to level [level]!"
levelMessage = "you just advanced to level"

@client.event
async def on_ready():
    print(f'Cardinal House bot is logged in as {client.user}')

    # print("Generating token statistics.")
    # await callGenerateTokenStatistics()

def isAdmin(user):
    if os.path.exists("data/admins.json"):
        with open("data/admins.json", 'r') as adminFile:
            adminJson = json.load(adminFile)

        adminUsers = adminJson["admins"]

        if user in adminUsers:
            return True
    else:
        with open("data/admins.json", 'w') as adminFile:
            json.dump({"admins": adminUsersDefault}, adminFile)
        
        if user in adminUsersDefault:
            return True
    
    return False

# Stops users from sending too many messages.
# No more than 2 messages per 10 seconds.
# No more than 10 messages per minute.
async def rateLimit(message, userJson):
    # First time this user has messaged, so they're good to go and add the current time as their last message.
    currTime = datetime.datetime.now()
    currTimeStr = datetime.datetime.strftime(currTime, "%m/%d/%Y, %H:%M:%S")
    if "lastMessageTenSec" not in userJson.keys():
        userJson["lastMessageTenSec"] = currTimeStr
        userJson["lastMessageMinute"] = currTimeStr
        userJson["numMessagesInTenSec"] = 1
        userJson["numMessagesInMinute"] = 1
        return False

    # Otherwise, this user has messaged before so make sure they shouldn't be rate limited.
    lastMessageTenSec = userJson["lastMessageTenSec"]
    lastMessageMinute = userJson["lastMessageMinute"]
    lastMessageTenSec = datetime.datetime.strptime(lastMessageTenSec, "%m/%d/%Y, %H:%M:%S")
    lastMessageMinute = datetime.datetime.strptime(lastMessageMinute, "%m/%d/%Y, %H:%M:%S")

    # Make sure the user hasn't sent more than 10 messages in a minute.
    if currTime >= lastMessageMinute + datetime.timedelta(minutes=1):
        userJson["lastMessageTenSec"] = currTimeStr
        userJson["lastMessageMinute"] = currTimeStr
        userJson["numMessagesInTenSec"] = 1
        userJson["numMessagesInMinute"] = 1
        return False
    else:
        userJson["numMessagesInMinute"] += 1
        if userJson["numMessagesInMinute"] > 10:
            await message.channel.send(f"{message.author.mention}: You are sending too many messages at once. Please wait a bit and try again.")
            return True
        
        if currTime >= lastMessageTenSec + datetime.timedelta(seconds=10):
            userJson["lastMessageTenSec"] = currTimeStr
            userJson["numMessagesInTenSec"] = 1
            return False
        else:
            userJson["numMessagesInTenSec"] += 1
            if userJson["numMessagesInTenSec"] > 2:
                await message.channel.send(f"{message.author.mention}: You are sending too many messages at once. Please wait a bit and try again.")
                return True

@client.event
async def on_reaction_add(reaction, user):
    await userReactionAdd(reaction, user, client)

@client.event
async def on_reaction_remove(reaction, user):
    await userReactionRemove(reaction, user, client)

@client.event
async def on_voice_state_update(member, before, after):
    if not os.path.isfile(f"users/{member}.json"):
        userFile = open(f"users/{member}.json", 'w')
        userFile.write("{}")
        userFile.close()

    await handleUserVoiceStateChange(member, before, after)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Creates the userfile if necessary.
    messageAuthor = str(message.author).strip("<>:\"/\\|?*")
    if not os.path.isfile(f"users/{messageAuthor}.json"):
        if not os.path.exists("users"):
            os.mkdir("users")

        if not os.path.exists("data"):
            os.mkdir("data")

        userFile = open(f"users/{messageAuthor}.json", 'w')
        userFile.write("{}")
        userFile.close()

    if not os.path.exists("data/currentEvent.json"):
        with open("data/currentEvent.json", 'w') as eventFile:
            json.dump({}, eventFile)

    if str(message.author) == levelBot and levelMessage in message.content:
        await trackLevelUp(message)
        return

    # Makes sure the user isn't sending too many messages.
    if message.content.startswith("$"):
        # Gets the data for the user.
        with open(f"users/{messageAuthor}.json", 'r') as userFile:
            userJson = json.load(userFile)

        rateLimited = await rateLimit(message, userJson)

        # Saves the rate limit data to the user's JSON file.
        with open(f"users/{messageAuthor}.json", 'w') as userFile:
            json.dump(userJson, userFile)

        if rateLimited:
            return

    if message.content.startswith('$react-set'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await setReactMessage(message)

    if message.content.startswith('$react-clear'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await clearReactMessages(message)

    if message.content.startswith('$event-start'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await startEvent(message)

    if message.content.startswith('$event-end'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await endEvent(message)

    if message.content.startswith('$cardinal-points') or message.content.startswith('$points') or message.content.startswith('$cardinalpoints'):
        await viewCardinalPoints(message)

    if message.content.startswith('$top-points') or message.content.startswith('$cardinal-point-scoreboard') or message.content.startswith('$point-scoreboard') or message.content.startswith('$scoreboard'):
        await viewCardinalPointScoreBoard(message)

    if message.content.startswith('$cardinal-points-set') or message.content.startswith('$points-set'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
            return

        await setCardinalPoints(message, "set")

    if message.content.startswith('$cardinal-points-increase') or message.content.startswith('$points-increase'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
            return

        await setCardinalPoints(message, "increase")

    if message.content.startswith('$cardinal-points-decrease') or message.content.startswith('$points-decrease'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
            return

        await setCardinalPoints(message, "decrease")

    if message.content.startswith('$admin-add') or message.content.startswith('$admin-remove'):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
            return

        await addOrRemoveAdminUser(message)
    
    if message.content.startswith("$get-report"):
        if not isAdmin(str(message.author)):
            await message.channel.send("Only Cardinal House admins can use this command.")
            return

        await getUserReport(message)

    if message.content.startswith("$help") and not message.content.startswith("$help-admin"):
        messageStr = "Cardinal Points Bot Commands:\n\n"
        messageStr += "$points - see how many Cardinal Points you have\n"
        messageStr += "$points [@user or user#1234] - see how many Cardinal Points someone else has\n"
        messageStr += "$scoreboard - see the Cardinal Points scoreboard\n"
        messageStr += "$help-admin - for Cardinal House admins to see their extended list of commands\n"

        await message.channel.send(messageStr)

    if message.content.startswith("$help-admin"):
        messageStr = "Cardinal Points Bot Commands for Admins (see $help for non-admin commands):\n\n"
        messageStr += "$admin-add [@user or user#1234] - Adds a user as a Cardinal House admin for executing admin commands\n"
        messageStr += "$admin-remove [@user or user#1234] - Removes a user from the list of Cardinal House admins for executing admin commands\n"
        messageStr += "$event-start - Starts an event in your current voice/stage channel where Cardinal Points are given to those who attend\n"
        messageStr += "$event-end - Ends the current event\n"
        messageStr += "$get-report - Generates a CSV file with all the Cardinal Point data for all members\n"
        messageStr += "$points-set [@user or user#1234] [number of points] - Sets the number of Cardinal Points a user has\n"
        messageStr += "$points-increase [@user or user#1234] [number of points] - Increases the number of Cardinal Points a user has\n"
        messageStr += "$points-decrease [@user or user#1234] [number of points] - Decreases the number of Cardinal Points a user has\n"
        messageStr += "$react-set - Tags a message so that members who react to it get a Cardinal Point\n"
        messageStr += "$react-clear - Empties the list of messages members can react to to earn Cardinal Points\n"

        await message.channel.send(messageStr)

    if message.content.startswith('$hello'):
        await message.channel.send('Greetings from the Cardinal House bot!')

    if message.content.startswith('$getChannelId'):
        await message.channel.send(message.channel.id)

    # Command to set the contract address, time between stat generations, time between stat messages, and the channel ID to message
    '''
    if message.content.startswith('$setConfig'):
        if str(message.author) not in adminUsers:
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await setConfig(message)

    if message.content.startswith('resetStats'):
        if str(message.author) not in adminUsers:
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await resetStats(message)

    if message.content.startswith('$message-stats'):
        if str(message.author) not in adminUsers:
            await message.channel.send("Only Cardinal House admins can use this command.")
        else:
            await callMessageTokenStatistics(client)
    '''


client.run(os.environ["CardinalHouseBotToken"])