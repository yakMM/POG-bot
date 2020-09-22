from PIL import Image, ImageDraw, ImageFont
from asyncio import get_event_loop
from modules.display import imageSend
from modules.enumerations import MatchStatus
import modules.config as cfg
from datetime import datetime as dt

bigFont = ImageFont.truetype("../fonts/OpenSans2.ttf", 100)
font = ImageFont.truetype("../fonts/OpenSans2.ttf", 80)
smallFont = ImageFont.truetype("../fonts/OpenSans2.ttf", 60)
white = (255,255,255)
yellow = (254, 227, 76)
grey1 = (219,219,219)
grey2 = (178,178,178)
yellow_light = (254,244,186)
Y_SPACING = 120
Y_BIG_SPACE = 150

X_OFFSET=100


def _drawScoreLine(draw, xStart, y, values, font, fill):
    for i in range(len(values)):
        draw.text((xStart + 300 * i, y), values[i], font=font, fill=fill)

def _cutOffString(string, font, treshold):
    def _binarySearch(base, i):
        size = font.getsize(string[:base+i]+"...")[0]
        size1 = font.getsize(string[:base+i+1]+"...")[0]
        if size <= treshold and size1 >= treshold:
            return base+i
        if i==1:
            return base+i+1
        if size >= treshold:
            return _binarySearch(base,i//2)
        if size <= treshold:
            return  _binarySearch(base+i,i//2)
    if font.getsize(string)[0] <= treshold:
        return string
    res = _binarySearch(0,len(string))
    return string[:res]+"..."

def _teamDisplay(draw, team, yOffset):

    # Titles:
    _drawScoreLine(draw, X_OFFSET+2200, yOffset, ["Score","Net","Kills","Deaths"], font, yellow)

    # Team scores:
    scores = [str(team.score), str(team.net), str(team.kills), str(team.deaths)]
    _drawScoreLine(draw, X_OFFSET+2200, Y_SPACING+yOffset, scores, bigFont, white)

    # Team name:
    draw.text((X_OFFSET,Y_SPACING+yOffset),
    f'{team.name} ({cfg.factions[team.faction]})', font=bigFont, fill=white)

    # Players:
    color = [white, white]
    for i in range(len(team.players)):
        aPlayer = team.players[i]

        # Scores:
        scores = [str(aPlayer.score), str(aPlayer.net), str(aPlayer.kills), str(aPlayer.deaths)]
        _drawScoreLine(draw, X_OFFSET+2200, Y_BIG_SPACE*2+Y_SPACING*i+yOffset, scores,
        font, color[i%2])

        # Names:
        name = _cutOffString(aPlayer.name, font, 1000)
        igName = _cutOffString(aPlayer.igName, font, 1000)


        draw.text((X_OFFSET,Y_BIG_SPACE*2+Y_SPACING*i+yOffset), name, font=font, fill=color[i%2])
        draw.text((X_OFFSET+1100,Y_BIG_SPACE*2+Y_SPACING*i+yOffset), igName, font=font, fill=color[i%2])





def _makeImage(match):
    img = Image.new('RGB', (3600, 3100), color = (17, 0, 68))
    logo = Image.open("../logos/bot.png")
    logo = logo.resize((600,600))
    img.paste(logo, (300,100), logo)
    #img = Image.open("score_template.png")
    yOff = lambda tId : 325+Y_SPACING*4+1200*tId
    draw = ImageDraw.Draw(img)
    x = X_OFFSET+1100
    xTitle = (3600-bigFont.getsize(f"Planetside Open Games - Match {match.number}")[0])//2
    draw.text((xTitle,100), f"Planetside Open Games - Match {match.number}", font=bigFont, fill=white)
    draw.text((x,200+100), f"Base: {match.map.name}", font=smallFont, fill=white)
    for i in range(len(match.roundStamps)):
        rs = match.roundStamps[i]
        text = dt.utcfromtimestamp(rs).strftime("%Y-%m-%d %H:%M")
        draw.text((x,200+100*(2+i)), f"Round {i+1}: {text}", font=smallFont, fill=white)
    if len(match.roundStamps) < 2:
        draw.text((x,200+100*3), f"Round 2: ", font=smallFont, fill=white)
        draw.text((x+smallFont.getsize("Round 2: ")[0],200+100*3), f"In progress...", font=smallFont, fill=yellow)
    draw.text((x,200+100*4), f"Round length: {cfg.ROUND_LENGTH} minutes", font=smallFont, fill=white)

    halSize = 25
    xMax=3600
    yMax=3100
    draw.line([halSize, 0, halSize,yMax], fill =(0,0,0), width = halSize*2)
    draw.line([0, halSize, xMax,halSize], fill =(0,0,0), width = halSize*2)
    draw.line([0, yMax-halSize, xMax,yMax-halSize], fill =(0,0,0), width = halSize*2)
    draw.line([xMax-halSize, 0, xMax-halSize,yMax], fill =(0,0,0), width = halSize*2)
    for tm in match.teams:
        yOffset = yOff(tm.id)
        draw.line([halSize*2, yOffset-20, xMax-halSize*2,yOffset-20], fill =white, width = 10)
        draw.line([100, yOffset+Y_BIG_SPACE*2-20, xMax-100,yOffset+Y_BIG_SPACE*2-20],
        fill =yellow, width = 10)

    draw.text((X_OFFSET+2200,200+100), f"Captures:", font=smallFont, fill=white)
    for tm in match.teams:
        draw.text((X_OFFSET+2200,200+100*(tm.id+2)), f"{tm.name}: {tm.cap} points", font=smallFont, white=white)
        _teamDisplay(draw, tm, yOff(tm.id))
    img.save(f'../matches/match_{match.number}.png')


async def publishMatchImage(match):
    loop = get_event_loop()
    await loop.run_in_executor(None, _makeImage, match)

    msg = match.msg
    if msg is not None:
        await msg.delete()
    
    if match.status is MatchStatus.IS_RESULT:
        string = "SC_RESULT"
    else:
        string = "SC_RESULT_HALF"
    msg = await imageSend(string, cfg.channels["results"], f'../matches/match_{match.number}.png', match.number)
    return msg

