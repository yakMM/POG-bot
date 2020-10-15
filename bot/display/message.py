from discord import File

class Message:
    """ Class for the enum to use
    """
    def __init__(self, string, ping=True, embed=None):
        self.__str = string
        self.__embed_fct = embed
        self.__ping = ping


    def get_embed(self, ctx, elements, kwargs):
        if self.__embed_fct:
            embed = self.__embed_fct(ctx, **kwargs)
            # Fixes the embed mobile bug:
            embed.set_author(name="Planetside Open Games",
            url="https://docs.google.com/document/d/13rsrWA4r16gpB-F3gvx5HWf2T974mdHLraPSjh5DO1Q/",
            icon_url = "https://media.discordapp.net/attachments/739231714554937455/739522071423614996/logo_png.png")

            elements["embed"] = embed


    def get_string(self, ctx, elements, args):
        if self.__str:
            # Format the string to be sent with added args
            string = self.__str.format(*args)

            if self.__ping:
                try:
                    mention = ctx.author.mention
                    string = f'{mention} {string}'
                except AttributeError:
                    pass

            elements["content"] = string


    def get_image(self, ctx, elements, image_path):
        if image_path:
            elements["file"] = File(image_path)


    def get_elements(self, ctx, **kwargs):

        elements = dict()
        self.get_string(ctx, elements, kwargs.get("string"))
        self.get_embed(ctx, elements, kwargs.get("embed"))
        self.get_image(ctx, elements, kwargs.get("image"))

        return elements

