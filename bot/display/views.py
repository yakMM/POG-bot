from discord import ui, SelectOption, ButtonStyle
import operator


def _view(func):
    def view_func(ctx, **kwargs):
        ui_elements = func(ctx, **kwargs)
        if not isinstance(ui_elements, list):
            ui_elements = [ui_elements]
        ui_view = ui.View(timeout=None)
        for ui_element in ui_elements:
            ui_element.callback = ctx.interaction_payload.callback
            ui_view.add_item(ui_element)
        return ui_view
    return view_func


@_view
def bases_selection(ctx, bases_list):
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

    return ui.Select(placeholder='Choose a base...', options=options, custom_id='base_selector')


@_view
def validation_buttons(ctx):
    decline = ui.Button(label="Decline", style=ButtonStyle.red, custom_id='decline')
    accept = ui.Button(label="Accept", style=ButtonStyle.green, custom_id='accept')

    return [decline, accept]


@_view
def players_buttons(ctx, match):
    players = match.get_left_players()
    if players:
        return [ui.Button(label=p.name, style=ButtonStyle.gray, custom_id=str(p.id)) for p in players]


@_view
def volunteer_button(ctx, match):
    return ui.Button(label="Volunteer", style=ButtonStyle.gray, custom_id='volunteer', emoji="🖐️")
