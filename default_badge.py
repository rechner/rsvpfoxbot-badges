from PIL import Image
from badges import make_template, MODE_COLOR

@make_template(4, 2.4, image_mode=MODE_COLOR)
def DefaultBadgeTemplate(badge, data):
    bg = Image.open("template.png")
    #badge.draw.bitmap((0, 0), bg)

    badge.register_font('line1', 0.35)
    badge.register_font('line2', 0.35)
    badge.register_font('line3', 0.35)

    line1 = data["line1"]
    line2 = " "
    if len(line1) > 10 and ' ' in line1:
        line1 = data["line1"].split()[0]
        line2 = "".join(data["line1"].split()[1:])

    badge.draw.centertext((badge.width / 2, 1.6), line1, font=badge.font('line1'), v_align='top', max_width=2.5)
    badge.draw.centertext((badge.width / 2, 2.2), line2, font=badge.font('line2'), valign='top', max_width=2.5)
    badge.draw.centertext((badge.width / 2, 3.0), data["line2"], font=badge.font('line3'), valign='top', max_width=2.5)

    # scale image
    icon_size = (1.2*300, 1.2*300)
    try:
        icon = Image.open(data["icon"]).convert("RGBA")
        icon.thumbnail(icon_size, Image.ANTIALIAS)
        badge.image.paste(icon, (4, 4))
    except:
        pass

    # (1.2 x 1.2) @ 0.027, 0.027
    #import pdb; pdb.set_trace()

