from PIL import Image, ImageDraw, ImageFont
from asyncio import get_event_loop
from modules.display import imageSend
from modules.enumerations import MatchStatus
import modules.config as cfg

bigFont = ImageFont.truetype("../fonts/OpenSans2.ttf", 50)
font = ImageFont.truetype("../fonts/OpenSans2.ttf", 40)
fill = (255,255,255)

X_OFFSET=300


def _drawScoreLine(draw, xStart, y, values, font):
    for i in range(len(values)):
        draw.text((xStart+300*i,y), values[i], font=font, fill=fill)

def _findCutOffSize(string, font, treshold):
    def _binarySearch(i):
        iHalf = i//2
        half = font.getsize(string[:iHalf])[0]
        half1 = font.getsize(string[:iHalf+1])[0]
        if half <= treshold and half1 >= treshold:
            return iHalf
        if half >= treshold:
            return _binarySearch(half)
    _binarySearch(treshold)



def _teamDisplay(draw, team, yOffset):

    # Team name:
    draw.text((X_OFFSET,100+yOffset), team.name, font=bigFont, fill=fill)

    # Titles:
    _drawScoreLine(draw, X_OFFSET+1000, yOffset, ["SCORE","NET","KILLS","DEATHS"], font)

    # Team scores:
    scores = [str(team.score), str(team.net), str(team.kills), str(team.deaths)]
    _drawScoreLine(draw, X_OFFSET+1000, 100+yOffset, scores, bigFont)

    # Cap
    draw.text((X_OFFSET+500,800+yOffset), "CAP", font=font, fill=fill)
    draw.text((X_OFFSET+1000,800+yOffset), str(team.cap), font=font, fill=fill)

    # Players:
    for i in range(len(team.players)):
        aPlayer = team.players[i]

        # Scores:
        scores = [str(aPlayer.score), str(aPlayer.net), str(aPlayer.kills), str(aPlayer.deaths)]
        _drawScoreLine(draw, X_OFFSET+1000, 200+100*i+yOffset, scores, font)

        # Names:
        name = aPlayer.name
        igName = aPlayer.igName
        print(font.getsize(name))
        if len(name) > 20:
            name = name[:20] + "..."

        if len(igName) > 20:
            igName = igName[:20] + "..."

        draw.text((X_OFFSET,200+100*i+yOffset), name, font=font, fill=fill)
        draw.text((X_OFFSET+500,200+100*i+yOffset), igName, font=font, fill=fill)





def _makeImage(match):
    img = Image.new('RGB', (2600, 2500), color = (17, 0, 68))
    #img = Image.open("pil_template.png")
    draw = ImageDraw.Draw(img)
    draw.text((1150,150), f"MATCH {match.number}", font=bigFont, fill=fill)
    if match.status is not MatchStatus.IS_RESULT:
        draw.text((1150,250), f"Halftime", font=bigFont, fill=fill)
    for tm in match.teams:
        _teamDisplay(draw, tm, 400+1100*tm.id)
    img.save(f'../matches/match_{match.number}.png')


async def publishMatchImage(match):
    loop = get_event_loop()
    await loop.run_in_executor(None, _makeImage, match)
    
    msg = match.msg
    if msg is not None:
        await msg.delete()
    msg = await imageSend(cfg.channels["results"], f'../matches/match_{match.number}.png')
    return msg

