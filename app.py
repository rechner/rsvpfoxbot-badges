from flask import Flask, request, render_template, abort, redirect, url_for, flash
from io import BytesIO
import requests
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster

from default_badge import DefaultBadgeTemplate

KEY = "881cf175e1b45db3f773b86bb7d0c3bc"
API_URL = "http://docker1.lan.knot.space:5001/"
CHAT_ID = "-1001285653547"  # Gender reveal

PRINTER = {
  'MODEL' : 'QL-800',
  'BACKEND' : 'pyusb',
  'PRINTER' : 'usb://0x04f9:0x209b',
  'LABEL' : '62red',
}

app = Flask(__name__)
app.secret_key = "super secret"

@app.route("/")
def index():
  r = requests.get("{0}/rsvps/{1}?auth={2}".format(API_URL, CHAT_ID, KEY))
  if r.ok:
    rsvps = r.json()
  else:
    app.logger.error(r)
    abort(500)

  return render_template("index.html", rsvps=rsvps)


@app.route("/edit/<int:id>")
def edit(id):
  r = requests.get("{0}/rsvps/{1}?auth={2}".format(API_URL, CHAT_ID, KEY))
  if r.ok:
    rsvps = r.json()
  else:
    abort(500)

  person = None
  for s in rsvps:
    if s["id"] == id:
      person = dict(s)

  person["profile_photo"] = "{0}/photo/{1}?auth={2}".format(API_URL, person["user_id"], KEY)

  return render_template("edit.html", person=person)


@app.route("/custom")
def custom():
  return render_template("custom.html", person=None)

@app.route("/checkin", methods=['POST'])
def checkin():
  id = request.form.get("id")
  user_id = request.form.get("user_id")
  line1 = request.form.get("line1")
  line2 = request.form.get("line2")

  if id is not None:
    r = requests.post("{0}/checkin/{1}?auth={2}".format(API_URL, id, KEY))
    if not r.ok:
      flash("Problem while updating the check-in time", "danger")

  icon = None
  if user_id is not None:
    photo_url = "{0}/photo/{1}?auth={2}".format(API_URL, user_id, KEY)
    r = requests.get(photo_url)
    if r.ok:
      icon = BytesIO()
      icon.write(r.content)
      icon.seek(0)

  badge = DefaultBadgeTemplate(default_font="DejaVuSans")
  data = {
    'line1' : line1,
    'line2' : line2,
    'icon' : icon,
  }

  badge.render(data, 'tmp.png', background='gender.png')

  qlr = BrotherQLRaster(PRINTER["MODEL"])
  qlr.exception_on_warning = True
  kwargs = {
    'label' : PRINTER['LABEL'],
    'red' : True,
    'rotate' : '90',
    'images' : {
      open('tmp.png', 'rb'),
    },
    'cut' : True,
  }

  instructions = convert(qlr=qlr, **kwargs)
  send(instructions=instructions, printer_identifier=PRINTER["PRINTER"], backend_identifier=PRINTER["BACKEND"], blocking=False)

  flash('Printing nametag for {0}...'.format(line1), 'info')

  return redirect(url_for('index'))


if __name__ == "__main__":
  app.run(port=8000, host='0.0.0.0')

