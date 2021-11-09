from discord import ui, SelectOption, ButtonStyle
import operator


def selected_bases(ctx, bases_list):
    """ Returns a list of bases currently selected
    """

    options = list()

    bases_list = sorted(bases_list, key=operator.itemgetter('name'))

    for base in bases_list:
        description_args = list()
        emoji = '🟩'
        if base['was_played_recently']:
            emoji = '🟦'
            description_args.append("Recently played!")
        if base['is_booked']:
            emoji = '🟥'
            description_args.append("Currently booked!")

        if description_args:
            description = " ".join(description_args[::-1])
        else:
            description = None

        options.append(SelectOption(label=base['name'], description=description, emoji=emoji, value=base['id']))

    select = ui.Select(placeholder='Choose a base...', options=options, custom_id='base_selector')
    select.callback = ctx.callback
    # select.disabled = True
    view = ui.View(timeout=None)

    view.add_item(select)

    return view


def validation_view(ctx):
    decline = ui.Button(label="Decline", style=ButtonStyle.red, custom_id='decline')
    accept = ui.Button(label="Accept", style=ButtonStyle.green, custom_id='accept')

    decline.callback = ctx.callback
    accept.callback = ctx.callback

    view = ui.View(timeout=None)

    view.add_item(accept)
    view.add_item(decline)

    return view


def player_view(ctx, match):
    players = match.get_left_players()
    if players:
        view = ui.View(timeout=None)
        for p in match.get_left_players():
            button = ui.Button(label=p.name, style=ButtonStyle.gray, custom_id=str(p.id))
            button.callback = ctx.callback
            view.add_item(button)
        return view


def volunteer_view(ctx, match):
    volunteer = ui.Button(label="Volunteer", style=ButtonStyle.gray, custom_id='volunteer', emoji="🖐️")
    volunteer.callback = ctx.callback
    view = ui.View(timeout=None)
    view.add_item(volunteer)
    return view
