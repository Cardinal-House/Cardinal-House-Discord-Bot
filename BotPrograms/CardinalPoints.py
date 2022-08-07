import discord
import sys
import os
import json
import datetime

NUM_MINUTES_IN_EVENT_FOR_CARDINAL_POINTS = 10
NUM_CARDINAL_POINTS_FOR_EVENT = 3

async def setReactMessage(message):
    messageSplit = message.content.split(" ")

    if len(messageSplit) < 2:
        await message.channel.send("Incorrect format! To make a message give out Cardinal Points for being reacted to, copy the ID of the message then use the command $set-react-message [message ID]")
        return

    messageID = messageSplit[1]

    if not os.path.exists("data/reactMessages.json"):
        with open("data/reactMessages.json", 'w') as reactMessagesFile:
            json.dump({"messages": []}, reactMessagesFile)

    with open("data/reactMessages.json", 'r') as reactMessagesFile:
        reactMessages = json.load(reactMessagesFile)

    reactMessages["messages"].append(messageID)

    with open("data/reactMessages.json", 'w') as reactMessagesFile:
        json.dump(reactMessages, reactMessagesFile)

    await message.channel.send("Members will now earn Cardinal Points when reacting to the specified message.")

async def clearReactMessages(message):
    with open("data/reactMessages.json", 'r') as reactMessagesFile:
        reactMessages = json.load(reactMessagesFile)

    reactMessages["messages"] = []

    with open("data/reactMessages.json", 'w') as reactMessagesFile:
        json.dump(reactMessages, reactMessagesFile)

    await message.channel.send("The list of messages members can react to to earn Cardinal Points has been reset successfully.")

async def startEvent(message):
    userVoiceState = message.author.voice

    if not userVoiceState:
        await message.channel.send("You must join the voice channel for the event before using this command! Voice state not found.")
        return

    eventVoiceChannel = userVoiceState.channel

    if not eventVoiceChannel:
        await message.channel.send("You must join the voice channel for the event before using this command!")
        return

    with open("data/currentEvent.json", 'r') as eventFile:
        eventJson = json.load(eventFile)

    eventJson["eventVoiceChannelID"] = eventVoiceChannel.id
    eventJson["eventMembers"] = []

    with open("data/currentEvent.json", 'w') as eventFile:
        json.dump(eventJson, eventFile)

    currTime = datetime.datetime.now()
    currTimeStr = datetime.datetime.strftime(currTime, "%m/%d/%Y, %H:%M:%S")

    for currEventMember in eventVoiceChannel.members:
        print(f"{currEventMember} is in an active event.")

        with open(f"users/{currEventMember}.json", 'r') as userFile:
            userJson = json.load(userFile)

        userJson["joinedEventTimestamp"] = currTimeStr
        userJson["joinedChannelID"] = eventVoiceChannel.id

        with open(f"users/{currEventMember}.json", 'w') as userFile:
            json.dump(userJson, userFile)

    await message.channel.send("A new event has started! Everyone who attends the event for at least 10 minutes will receive Cardinal Points.")

async def endEvent(message):
    with open("data/currentEvent.json", 'r') as eventFile:
        eventJson = json.load(eventFile)

    eventJson["eventVoiceChannelID"] = ""
    eventJson["eventMembers"] = []

    with open("data/currentEvent.json", 'w') as eventFile:
        json.dump(eventJson, eventFile)

    await message.channel.send("The current event has ended! Everyone who attended the event for at least 10 minutes will be awarded Cardinal Points upon exiting!")

async def handleUserJoinedChannel(member, before, after):
    with open("data/currentEvent.json") as eventFile:
        eventJson = json.load(eventFile)

    if eventJson["eventVoiceChannelID"] == after.channel.id:
        print(f"{member} joined an active event.")

        with open(f"users/{member}.json", 'r') as userFile:
            userJson = json.load(userFile)

        currTime = datetime.datetime.now()
        currTimeStr = datetime.datetime.strftime(currTime, "%m/%d/%Y, %H:%M:%S")
        userJson["joinedEventTimestamp"] = currTimeStr
        userJson["joinedChannelID"] = after.channel.id

        with open(f"users/{member}.json", 'w') as userFile:
            json.dump(userJson, userFile)


async def handleUserLeftChannel(member, before, after):
    with open(f"users/{member}.json", 'r') as userFile:
        userJson = json.load(userFile)

    if "joinedEventTimestamp" in userJson.keys() and userJson["joinedEventTimestamp"] != "" and userJson["joinedChannelID"] == before.channel.id:
        currTime = datetime.datetime.now()
        joinTime = datetime.datetime.strptime(userJson["joinedEventTimestamp"], "%m/%d/%Y, %H:%M:%S")

        userJson["joinedEventTimestamp"] = ""
        userJson["joinedChannelID"] = ""

        timeDiff = currTime - joinTime
        numMinutesJoined = timeDiff.seconds / 60

        with open("data/currentEvent.json") as eventFile:
            eventJson = json.load(eventFile)

        if numMinutesJoined > NUM_MINUTES_IN_EVENT_FOR_CARDINAL_POINTS and str(member) not in eventJson["eventMembers"]:
            print(f"{member} was in the channel {before.channel} for {numMinutesJoined} minutes.")
            if "cardinalPoints" not in userJson.keys():
                userJson["cardinalPoints"] = NUM_CARDINAL_POINTS_FOR_EVENT
            else:
                userJson["cardinalPoints"] += NUM_CARDINAL_POINTS_FOR_EVENT

        eventJson["eventMembers"].append(str(member))

        with open("data/currentEvent.json", 'w') as eventFile:
            json.dump(eventJson, eventFile)

        with open(f"users/{member}.json", 'w') as userFile:
            json.dump(userJson, userFile)

async def handleUserVoiceStateChange(member, before, after):
    if before.channel == None and after.channel != None:
        print(f"{member} joined the channel: {after.channel}")
        await handleUserJoinedChannel(member, before, after)
    elif before.channel != None and after.channel == None:
        print(f"{member} left the channel: {before.channel}")
        await handleUserLeftChannel(member, before, after)
    elif before.channel != None and after.channel != None and before.channel.id != after.channel.id:
        print(f"{member} left the channel {before.channel} and joined the channel {after.channel}")
        await handleUserJoinedChannel(member, before, after)
        await handleUserLeftChannel(member, before, after)

async def trackLevelUp(message):
    level = message.content.split("level ")[1].split("!")[0]
    user = message.mentions[0]

    with open(f"users/{user}.json", 'r') as userFile:
        userJson = json.load(userFile)

    if "cardinalPoints" not in userJson.keys():
        userJson["cardinalPoints"] = int(level)
    else:
        userJson["cardinalPoints"] += int(level)

    with open(f"users/{user}.json", 'w') as userFile:
        json.dump(userJson, userFile)

    newNumPoints = userJson["cardinalPoints"]

    await message.channel.send(f"{user}, you have been awarded {level} Cardinal Points for leveling up! You now have {newNumPoints} Cardinal Points.")

def isReactMessage(message):
    if os.path.exists("data/reactMessages.json"):
        with open("data/reactMessages.json", 'r') as reactMessagesFile:
            reactMessages = json.load(reactMessagesFile)

        if "messages" in reactMessages.keys() and str(message.id) in reactMessages["messages"]:
            return True

    return False

async def userReactionAdd(reaction, user, client):
    if not isReactMessage(reaction.message):
        return

    userReactionCount = 0
    messageReactions = reaction.message.reactions
    for messageReaction in messageReactions:
        users = list(map(lambda u: str(u), await messageReaction.users().flatten()))
        if str(user) in users:
            userReactionCount += 1

            if userReactionCount > 1:
                # User has already reacted to this message so don't give them another Cardinal Point
                return

    with open(f"users/{user}.json", 'r') as userFile:
        userJson = json.load(userFile)

    if "cardinalPoints" not in userJson.keys():
        userJson["cardinalPoints"] = 1
    else:
        userJson["cardinalPoints"] += 1

    with open(f"users/{user}.json", 'w') as userFile:
        json.dump(userJson, userFile)

    newNumPoints = userJson["cardinalPoints"]

    await reaction.message.channel.send(f"{user.mention} You have earned a Cardinal Point for reacting to an event notifcation! You now have {newNumPoints} Cardinal Points.")

async def userReactionRemove(reaction, user, client):
    if not isReactMessage(reaction.message):
        return

    userReactionCount = 0
    messageReactions = reaction.message.reactions
    for messageReaction in messageReactions:
        users = list(map(lambda u: str(u), await messageReaction.users().flatten()))
        if str(user) in users:
            # User still has reactions to the message they didn't get Cardinal Points for, so don't take one away unless
            # they remove their last reaction to the mssage.
            return

    with open(f"users/{user}.json", 'r') as userFile:
        userJson = json.load(userFile)

    if "cardinalPoints" not in userJson.keys():
        userJson["cardinalPoints"] = 0
    else:
        userJson["cardinalPoints"] -= 1

    with open(f"users/{user}.json", 'w') as userFile:
        json.dump(userJson, userFile)

    newNumPoints = userJson["cardinalPoints"]

    await reaction.message.channel.send(f"{user.mention} You lost a Cardinal Point for removing your reaction from an event notification! You now have {newNumPoints} Cardinal Points.")

async def viewCardinalPoints(message):
    user = message.mentions
    messageSplit = message.content.split(" ")

    if len(user) > 0:
        user = user[0]
    elif len(messageSplit) > 1:
        user = messageSplit[1]
    else:
        user = message.author

    userCardinalPoints = 0
    if os.path.exists(f"users/{user}.json"):
        with open(f"users/{user}.json", 'r') as userFile:
            userJson = json.load(userFile)

        if "cardinalPoints" in userJson.keys():
            userCardinalPoints = userJson["cardinalPoints"]

        if type(user) == type(message.author):
            await message.channel.send(f"{user.mention} has {userCardinalPoints} Cardinal Points!")
        else:
            await message.channel.send(f"{user} has {userCardinalPoints} Cardinal Points!")
    else:
        await message.channel.send(f"{user} not found.")
    
async def viewCardinalPointScoreBoard(message):
    userCardinalPoints = []
    userFiles = os.listdir("users/")

    for userFilePath in userFiles:
        with open(f"users/{userFilePath}", 'r') as userFile:
            userJson = json.load(userFile)
            username = userFilePath.split(".json")[0]

            if "cardinalPoints" in userJson.keys():
                userCardinalPoints.append({"username": username, "cardinalPoints": userJson["cardinalPoints"]})
            else:
                userCardinalPoints.append({"username": username, "cardinalPoints": 0})

    userCardinalPoints.sort(key=lambda user: user["cardinalPoints"], reverse=True)
    
    messageContent = "Top Cardinal Point Holders:\n\n"
    for i in range(5):
        if len(userCardinalPoints) > i + 1:
            messageContent += f"#{i + 1}: {userCardinalPoints[i]['username']} - {userCardinalPoints[i]['cardinalPoints']} Cardinal Points\n"

    await message.channel.send(messageContent)

async def setCardinalPoints(message, operation):
    user = message.mentions
    messageSplit = message.content.split(" ")

    if len(messageSplit) != 3:
        if operation == "set":
            await message.channel.send("Incorrect format! The format for setting a user's Cardinal Points is $set-cardinal-points [@carlthecardinal or carlthecardinal#1234] [points]")
        elif operation == "increase":
            await message.channel.send("Incorrect format! The format for giving Cardinal Points to a user is $increase-cardinal-points [@carlthecardinal or carlthecardinal#1234] [points]")
        elif operation == "decrease":
            await message.channel.send("Incorrect format! The format for taking away Cardinal Points from a user is $decrease-cardinal-points [@carlthecardinal or carlthecardinal#1234] [points]")
        else:
            await message.channel.send("Invalid command.")
        return

    if len(user) > 0:
        user = user[0]
    else:
        user = messageSplit[1]

    numPoints = messageSplit[2]

    userJson = {"cardinalPoints": 0}
    if os.path.exists(f"users/{user}.json"):
        with open(f"users/{user}.json", 'r') as userFile:
            userJson = json.load(userFile)

    try:
        if operation == "set":
            userJson["cardinalPoints"] = int(numPoints)
        elif operation == "increase":
            userJson["cardinalPoints"] += int(numPoints)
        elif operation == "decrease":
            userJson["cardinalPoints"] -= int(numPoints)
    except:
        await message.channel.send("Invalid point value. Must been a whole number.")
        return

    with open(f"users/{user}.json", 'w') as userFile:
        json.dump(userJson, userFile)

    newNumPoints = userJson["cardinalPoints"]

    if type(user) == type(message.author):
        await message.channel.send(f"{user.mention} now has {newNumPoints} Cardinal Points.")
    else:
        await message.channel.send(f"{user} now has {newNumPoints} Cardinal Points.")

async def addOrRemoveAdminUser(message):
    messageSplit = message.content.split(" ")
    command = messageSplit[0].split("-")[1]
    user = message.mentions

    if len(messageSplit) < 2:
        await message.channel.send("Incorrect command format. The format is $[add or remove]-admin [@carlthecardinal or carlthecardinal#1234]")
        return

    if len(user) > 0:
        user = user[0]
    else:
        user = messageSplit[1]

    with open("data/admins.json", 'r') as adminFile:
        adminJson = json.load(adminFile)

    if command == "add":
        adminJson["admins"].append(str(user))

        if type(user) == type(message.author):
            await message.channel.send(f"{user.mention} has been added as a Cardinal House bot admin.")
        else:
            await message.channel.send(f"{user} has been added as a Cardinal House bot admin.")
    elif command == "remove" and user in adminJson["admins"]:
        adminJson = adminJson.remove(user)

        if type(user) == type(message.author):
            await message.channel.send(f"{user.mention} is no longer a Cardinal House bot admin.")
        else:
            await message.channel.send(f"{user} is no longer a Cardinal House bot admin.")

    with open("data/admins.json", 'w') as adminFile:
        json.dump(adminJson, adminFile)

async def getUserReport(message):
    userCardinalPoints = []
    userFiles = os.listdir("users/")

    for userFilePath in userFiles:
        with open(f"users/{userFilePath}", 'r') as userFile:
            userJson = json.load(userFile)
            username = userFilePath.split(".json")[0]

            if "cardinalPoints" in userJson.keys():
                userCardinalPoints.append({"username": username, "cardinalPoints": userJson["cardinalPoints"]})
            else:
                userCardinalPoints.append({"username": username, "cardinalPoints": 0})

    userCardinalPoints.sort(key=lambda user: user["cardinalPoints"], reverse=True)
    
    csvLines = ["Discord User,Cardinal Points\n"]
    for user in userCardinalPoints:
        csvLines.append(f"{user['username']},{user['cardinalPoints']}\n")

    currTime = datetime.datetime.now()
    currTimeStr = datetime.datetime.strftime(currTime, "%m-%d-%Y")

    with open(f"data/cardinal-points-{currTimeStr}.csv", 'w') as csvFile:
        csvFile.writelines(csvLines)

    await message.channel.send(file=discord.File(f"data/cardinal-points-{currTimeStr}.csv"))