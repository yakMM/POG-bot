from PIL import Image, ImageDraw, ImageFont
from asyncio import get_event_loop
from modules.display import imageSend
import modules.config as cfg

img = Image.new('RGB', (2600, 2500), color=(255, 255, 255))
# img = Image.open("pil_template.png")
draw = ImageDraw.Draw(img)
# font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", fontsize, encoding="unic")
bigFont = ImageFont.truetype("../fonts/PlanetSide2.ttf", 50)
font = ImageFont.truetype("../fonts/PlanetSide2.ttf", 40)
fill = (0, 0, 0)

X_OFFSET = 300


def _drawScoreLine(draw, xStart, y, values, font):
    for i in range(len(values)):
        draw.text((xStart + 300 * i, y), values[i], font=font, fill=fill)


def _teamDisplay(draw, team, yOffset):
    # Team name:
    draw.text((X_OFFSET, 100 + yOffset), team.name, font=bigFont, fill=fill)

    # Titles:
    _drawScoreLine(draw, X_OFFSET + 1000, yOffset, ["SCORE", "NET", "KILLS", "DEATHS"], font)

    # Team scores:
    scores = [str(team.score), "0", str(team.kills), str(team.deaths)]
    _drawScoreLine(draw, X_OFFSET + 1000, 100 + yOffset, scores, bigFont)

    # Cap
    draw.text((X_OFFSET + 500, 800 + yOffset), "CAP", font=font, fill=fill)
    draw.text((X_OFFSET + 1000, 800 + yOffset), str(team.cap), font=font, fill=fill)

    # Players:
    for i in range(len(team.players)):
        aPlayer = team.players[i]

        # Scores:
        scores = [str(aPlayer.score), str(aPlayer.net), str(aPlayer.kills), str(aPlayer.deaths)]
        _drawScoreLine(draw, X_OFFSET + 1000, 200 + 100 * i + yOffset, scores, font)

        # Names:
        # TODO: WIP
        draw.text((X_OFFSET, 200 + 100 * i + yOffset), aPlayer.name, font=font, fill=fill)
        draw.text((X_OFFSET + 500, 200 + 100 * i + yOffset), aPlayer.igName, font=font, fill=fill)


def _makeImage(match):
    draw.text((1150, 150), f"MATCH {match.number}", font=bigFont, fill=fill)
    for tm in match.teams:
        _teamDisplay(draw, tm, 400 + 1100 * tm.id)
    img.save(f'../matches/match_{match.number}.png')


async def publishMatchImage(match):
    loop = get_event_loop()
    await loop.run_in_executor(None, _makeImage, match)
    await imageSend(cfg.channels["staff"], f'../matches/match_{match.number}.png')
