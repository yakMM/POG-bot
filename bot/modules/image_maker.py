# @CHECK 2.0 features OK

from PIL import Image, ImageDraw, ImageFont
from asyncio import get_event_loop
from display.strings import AllStrings as display
from display.classes import ContextWrapper
from modules.enumerations import MatchStatus
import modules.config as cfg
from datetime import datetime as dt

big_font = ImageFont.truetype("../fonts/OpenSans2.ttf", 100)
font = ImageFont.truetype("../fonts/OpenSans2.ttf", 80)
small_font = ImageFont.truetype("../fonts/OpenSans2.ttf", 60)
white = (255,255,255)
yellow = (254, 227, 76)
grey1 = (219,219,219)
grey2 = (178,178,178)
yellow_light = (254,244,186)
Y_SPACING = 120
Y_BIG_SPACE = 150

X_OFFSET=100


def _draw_score_line(draw, x_start, y, values, font, fill):
    for i in range(len(values)):
        draw.text((x_start + 300 * i, y), values[i], font=font, fill=fill)

def _cut_off_string(string, font, treshold):
    def _binary_search(base, i):
        size = font.getsize(string[:base+i]+"...")[0]
        size1 = font.getsize(string[:base+i+1]+"...")[0]
        if size <= treshold and size1 >= treshold:
            return base+i
        if i==1:
            return base+i+1
        if size >= treshold:
            return _binary_search(base,i//2)
        if size <= treshold:
            return  _binary_search(base+i,i//2)
    if font.getsize(string)[0] <= treshold:
        return string
    res = _binary_search(0,len(string))
    return string[:res]+"..."

def _team_display(draw, team, y_offset):

    # Titles:
    _draw_score_line(draw, X_OFFSET+2200, y_offset, ["Score","Net","Kills","Deaths"], font, yellow)

    # Team scores:
    scores = [str(team.score), str(team.net), str(team.kills), str(team.deaths)]
    _draw_score_line(draw, X_OFFSET+2200, Y_SPACING+y_offset, scores, big_font, white)

    # Team name:
    draw.text((X_OFFSET,Y_SPACING+y_offset),
    f'{team.name} ({cfg.factions[team.faction]})', font=big_font, fill=white)

    # Players:
    color = [white, white]
    for i in range(len(team.players)):
        a_player = team.players[i]

        # Scores:
        scores = [str(a_player.score), str(a_player.net), str(a_player.kills), str(a_player.deaths)]
        _draw_score_line(draw, X_OFFSET+2200, Y_BIG_SPACE*2+Y_SPACING*i+y_offset, scores,
        font, color[i%2])

        # Names:
        name = _cut_off_string(a_player.name, font, 1000)
        ig_name = _cut_off_string(a_player.ig_name, font, 1000)


        draw.text((X_OFFSET,Y_BIG_SPACE*2+Y_SPACING*i+y_offset), name, font=font, fill=color[i%2])
        draw.text((X_OFFSET+1100,Y_BIG_SPACE*2+Y_SPACING*i+y_offset), ig_name, font=font, fill=color[i%2])





def _make_image(match):
    img = Image.new('RGB', (3600, 3100), color = (17, 0, 68))
    logo = Image.open("../logos/bot.png")
    logo = logo.resize((600,600))
    img.paste(logo, (300,100), logo)
    #img = Image.open("score_template.png")
    y_off = lambda t_id : 325+Y_SPACING*4+1200*t_id
    draw = ImageDraw.Draw(img)
    x = X_OFFSET+1100
    x_title = (3600-big_font.getsize(f"Planetside Open Games - Match {match.number}")[0])//2
    draw.text((x_title,100), f"Planetside Open Games - Match {match.number}", font=big_font, fill=white)
    draw.text((x,200+100), f"Base: {match.map.name}", font=small_font, fill=white)
    for i in range(len(match.round_stamps)):
        rs = match.round_stamps[i]
        text = dt.utcfromtimestamp(rs).strftime("%Y-%m-%d %H:%M")
        draw.text((x,200+100*(2+i)), f"Round {i+1}: {text}", font=small_font, fill=white)
    if len(match.round_stamps) < 2:
        draw.text((x,200+100*3), f"Round 2: ", font=small_font, fill=white)
        draw.text((x+small_font.getsize("Round 2: ")[0],200+100*3), f"In progress...", font=small_font, fill=yellow)
    draw.text((x,200+100*4), f"Round length: {cfg.general['round_length']} minutes", font=small_font, fill=white)

    hal_size = 25
    x_max=3600
    y_max=3100
    draw.line([hal_size, 0, hal_size,y_max], fill =(0,0,0), width = hal_size*2)
    draw.line([0, hal_size, x_max,hal_size], fill =(0,0,0), width = hal_size*2)
    draw.line([0, y_max-hal_size, x_max,y_max-hal_size], fill =(0,0,0), width = hal_size*2)
    draw.line([x_max-hal_size, 0, x_max-hal_size,y_max], fill =(0,0,0), width = hal_size*2)
    for tm in match.teams:
        y_offset = y_off(tm.id)
        draw.line([hal_size*2, y_offset-20, x_max-hal_size*2,y_offset-20], fill =white, width = 10)
        draw.line([100, y_offset+Y_BIG_SPACE*2-20, x_max-100,y_offset+Y_BIG_SPACE*2-20],
        fill =yellow, width = 10)

    draw.text((X_OFFSET+2200,200+100), f"Captures:", font=small_font, fill=white)
    for tm in match.teams:
        draw.text((X_OFFSET+2200,200+100*(tm.id+2)), f"{tm.name}: {tm.cap} points", font=small_font, white=white)
        _team_display(draw, tm, y_off(tm.id))
    img.save(f'../../POG-data/matches/match_{match.number}.png')


async def publish_match_image(match):
    loop = get_event_loop()
    await loop.run_in_executor(None, _make_image, match)

    msg = match.msg
    if msg is not None:
        await msg.delete()
    
    if match.status is MatchStatus.IS_RESULT:
        msg = await display.SC_RESULT.imageSend(ContextWrapper.channel(cfg.channels["results"]),
                f'../../POG-data/matches/match_{match.number}.png', match.number)
    else:
        msg = await display.SC_RESULT_HALF.imageSend(ContextWrapper.channel(cfg.channels["results"]),
                                          f'../../POG-data/matches/match_{match.number}.png', match.number)
    return msg

