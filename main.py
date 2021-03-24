import discord
import requests
import json
import MySQLdb
import csv
import datetime
from PIL import Image, ImageDraw, ImageFont
from csv import writer

client = discord.Client()
db = MySQLdb.connect("localhost","root","root","ChessBot")
cursor = db.cursor()

async def registerMember(discordId, smuId, email):
  if (len(smuId) != 8) or (email.find("@smu.edu") == -1):
    print("bad")
    return False
  sql = "INSERT INTO Members (DiscordID, SMUID, Email) VALUES ('%s','%s','%s')" % (discordId, smuId, email)
  try:
    tempSql = "DELETE FROM Members WHERE DiscordID='%s'" % discordId
    cursor.execute(tempSql)
    cursor.execute(sql)
    db.commit()
    return True
  except:
    print("bad")
    db.rollback()
    return False

async def isLinked(discordId, chessUsername):
  sql = "SELECT * FROM ChessUsernames WHERE DiscordID='%s'" % (discordId)
  try:
    cursor.execute(sql)
    results = cursor.fetchall()
    if(len(results) == 0):
      return False
    else:
      print(results[0][1])
      print(chessUsername)
      if(results[0][1] != chessUsername):
        cursor.execute("UPDATE ChessUsernames SET Username='%s' WHERE DiscordID='%s'" % (chessUsername, discordId))
        db.commit()
      return True
  except:
    db.rollback()
    print("bad")

async def link(discordId, chessUsername):
  if(await isLinked(discordId, chessUsername) == False):
    sql = "INSERT INTO ChessUsernames (DiscordID, Username) VALUES ('%s','%s')" % (discordId, chessUsername)
    try:
      cursor.execute(sql)
      db.commit()
    except:
      db.rollback()
  else:
    print("already registered")

def sortFunc(e):
  return int(e[2])

async def getLeaderBoard():
  players = []
  leaderBoard = []
  try:
    cursor.execute("SELECT * FROM ChessUsernames")
    players = cursor.fetchall()
  except:
    print("bad")
  
  print(players)
  max = 0
  for player in players:
    response = requests.get("https://api.chess.com/pub/player/"+ player[1] +"/stats")
    stats = json.loads(response.text)
    temp = [player[0], player[1], str(stats["chess_rapid"]["last"]["rating"])]
    leaderBoard.append(temp)
    if(len(player[1]) > max):
      print("new max " + str(len(player[1])))
      max = len(player[1])
  leaderBoard.sort(reverse=True, key=sortFunc)
  leaderBoard.append(max)
  return leaderBoard
  

def getStats(username):
  response = requests.get("https://api.chess.com/pub/player/"+ username +"/stats")
  json_data = json.loads(response.text)
  return(json_data)

def getProfile(username):
  response = requests.get("https://api.chess.com/pub/player/"+ username)
  json_data = json.loads(response.text)
  return(json_data)

async def getChessUsername(discordId):
  sql = "SELECT Username FROM ChessUsernames WHERE DiscordID='%s'" % (discordId)
  try:
    cursor.execute(sql)
    results = cursor.fetchall()
    return results[0][0]
  except:
    print("bad")


    
@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

@client.event
async def on_member_join(member):
    print(member)
    role = discord.utils.get(member.server.roles, name="Visitors")
    await member.add_roles(role)

@client.event
async def on_message(message):
  if message.author == client.user:
    return

  if message.content.startswith('$link'):
    chessUsername = message.content.split("$link ",1)[1]
    await link(message.author.id, chessUsername)

  if message.content.startswith('$join'):
    args = message.content.split(' ')
    if(len(args) >= 3):
      res = await registerMember(message.author.id, args[1], args[2])
      if(res):
        member = message.author
        var = discord.utils.get(message.guild.roles, name = "Members")
        await member.add_roles(var)
      else:
        await message.channel.send("Failed to register " + message.author.name +" as member, please check credentials")
    else:
      await message.channel.send("Failed to register " + message.author.name +" as member, please check credentials")

  if message.content.startswith('$leaderboard'):
    leaderBoard = await getLeaderBoard()
    i = 0
    temp = ""
    max = leaderBoard.pop()
    for score in leaderBoard:
      i = i + 1
      string = str(i) + '. '
      for x in range(0, len(str(len(leaderBoard))) - len(str(i))):
        string = string + ' '
      string = string + score[1]
      for x in range(0, max - len(score[1])):
        print("adding space to " + score[1])
        string = string + ' '
      string = string + " : " + score[2]
      temp = temp + string + "\n"
    print(temp)
    embed=discord.Embed(title="LeaderBoard", description=" ")
    embed.add_field(name="username : rating", value=temp, inline=False)
    await message.channel.send(embed=embed)

  if message.content.startswith('$stats'):
    userId = message.content.split("$stats ",1)[1][3:-1]
    chessUsername = await getChessUsername(userId)
    print(chessUsername)
    stats = getStats(chessUsername)
    profile = getProfile(chessUsername)
    print(stats)

    print(profile)
    
    embededResponse = discord.Embed(title="title",
    description="this")

    try:
      embededResponse.set_author(name=chessUsername,
        url=profile["url"],
        icon_url=profile["avatar"])
    except:
      embededResponse.set_author(name=chessUsername,
        url=profile["url"],
        icon_url="http://images.chesscomfiles.com/uploads/images/noavatar_l.gif")
    
    embededResponse.timestamp = datetime.datetime.now()
    embededResponse.set_footer(text='footer')
    try:
      embededResponse.add_field(name=":alarm_clock: Rapid", value="Curr Rating: "+str(stats["chess_rapid"]["last"]["rating"])
      +"\nBest Rating: "+str(stats["chess_rapid"]["best"]["rating"])
      +"\nw|L|d :  "+str(stats["chess_rapid"]["record"]["win"])+"/"+str(stats["chess_rapid"]["record"]["loss"])+"/"+str(stats["chess_rapid"]["record"]["draw"]), inline=True)
    except:
      embededResponse.add_field(name=":alarm_clock: Rapid", value="Curr Rating: Na\nBest Rating: Na\nw|L|d : 0/0/0", inline=True)
    try:
      embededResponse.add_field(name=":cloud_lightning: Blitz", value="Curr Rating: "+str(stats["chess_blitz"]["last"]["rating"])
      +"\nBest Rating: "+str(stats["chess_blitz"]["best"]["rating"])
      +"\nw|L|d :  "+str(stats["chess_blitz"]["record"]["win"])+"/"+str(stats["chess_blitz"]["record"]["loss"])+"/"+str(stats["chess_blitz"]["record"]["draw"]), inline=True)
    except:
      embededResponse.add_field(name=":cloud_lightning: Blitz", value="Curr Rating: Na\nBest Rating: Na\nw|L|d : 0/0/0", inline=True)
    try:
      embededResponse.add_field(name=":rocket: Bullet", value="Curr Rating: "+str(stats["chess_bullet"]["last"]["rating"])
      +"\nBest Rating: "+str(stats["chess_bullet"]["best"]["rating"])
      +"\nw|L|d :  "+str(stats["chess_bullet"]["record"]["win"])+"/"+str(stats["chess_bullet"]["record"]["loss"])+"/"+str(stats["chess_bullet"]["record"]["draw"]), inline=True)
    except:
      embededResponse.add_field(name=":rocket: Bullet", value="Curr Rating: Na\nBest Rating: Na\nw|L|d : 0/0/0", inline=True)
    await message.channel.send(embed=embededResponse)


client.run('ODA2MjM5MTc0MTIxODgxNjgx.YBmivg.GUd5J7pPEaB3q2AFYgv8IfL59nI')