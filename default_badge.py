from PIL import Image
from badges import make_template, MODE_COLOR

@make_template(4, 2.4, image_mode=MODE_COLOR)
def DefaultBadgeTemplate(badge, data):
    bg = Image.open("template.png")
    #badge.draw.bitmap((0, 0), bg)

    badge.register_font('line1', 0.4)
    badge.register_font('line2', 0.35)

    badge.draw.centertext((badge.width / 2, 1.3), data["line1"], font=badge.font('line1'), v_align='top', max_width=3.75)
    badge.draw.centertext((badge.width / 2, 2.1), data["line2"], font=badge.font('line2'), valign='top', max_width=3.75)

    # scale image
    icon_size = (1.2*300, 1.2*300)
    icon_place = (0.027, 0.027)
    try:
        icon = Image.open(data["icon"]).convert("RGBA")
        icon.thumbnail(icon_size, Image.ANTIALIAS)
    except:
        pass

    # (1.2 x 1.2) @ 0.027, 0.027


    badge.image.paste(icon, (4, 4))

    #import pdb; pdb.set_trace()

