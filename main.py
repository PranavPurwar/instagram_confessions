import os
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from PIL import Image, ImageFont
from textwrap import wrap
from flask import Flask
from waitress import serve
from threading import Thread
from pilmoji import Pilmoji
from pilmoji.source import GoogleEmojiSource

# Load credentials from .env file
load_dotenv()

app = Flask("Anonymous Confessions")

@app.route('/')
def index():
    return "Hello World!"

thread = Thread(target=serve, kwargs={"app": app, "host": "0.0.0.0"})

if os.path.exists('output.jpg'):
    os.remove('output.jpg')


username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")

client = Client()

def login_user():
    """
    Attempts to login to Instagram using either the provided session information
    or the provided username and password.
    """

    session = None

    login_via_session = False
    login_via_pw = False
    
    client.set_locale('en_IN')
    client.set_timezone_offset(5 * 60 * 60 + 30 * 60)
    
    user_agent = "Instagram 165.1.0.29.119 Android (27/8.1.0; 480dpi; 1080x1776; motorola; Moto G (5S); montana; qcom; ru_RU; 253447809)"
    
    client.set_user_agent(user_agent)
    client.set_country_code(91)
    client.set_country("IN")

    if session:
        try:
            client.set_settings(session)
            client.relogin()
            client.login(username, password)

            # check if session is valid
            try:
                client.get_timeline_feed()
            except LoginRequired:
                print("Session is invalid, need to login via username and password")

                old_session = client.get_settings()

                # use the same device uuids across logins
                client.set_settings({})
                client.set_uuids(old_session["uuids"])

                client.login(username, password)
            login_via_session = True
        except Exception as e:
            print("Couldn't login user using session information: %s" % e)

    if not login_via_session:
        try:
            print("Attempting to login via username and password. username: %s" % username)
            if client.login(username, password):
                login_via_pw = True
        except Exception as e:
            print("Couldn't login user using username and password: %s" % e)

    if not login_via_pw and not login_via_session:
        raise Exception("Couldn't login user with either password or session")

def draw_paragraph_on_image(image_path, paragraph, position=(10, 10), font_size=32, text_color=(255, 255, 255),
                             font_path=None, max_width=800):
    image = Image.open(image_path)
    draw = Pilmoji(image, source=GoogleEmojiSource)

    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default(font_size)

    words = paragraph.split()
    lines = []
    current_line = words[0]

    for word in words[1:]:
        test_line = current_line + " " + word
        width = draw.getsize(test_line, font=font)[0]
        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)

    # Calculate total height of the text block
    total_height = sum(8 * (n + 1) for n, line in enumerate(lines))

    # Calculate the starting vertical position to center the text
    y = (image.size[1] - total_height) // 2

    for n, line in enumerate(lines):
        # Calculate the starting horizontal position to center the text
        x = (image.size[0] - draw.getsize(line, font=font)[0]) // 2
        draw.text((x, y), line, font=font, fill=text_color)
        y += 36

    image.save("output.jpg")

login_user()

requests = client.direct_pending_inbox()

for pending in requests:
    client.direct_pending_approve(pending.id)
    print(f"Approved {pending.users[0].username}")

    client.direct_send("Hello, this is an automated message. Please enter your confession below in a single message. If you want your name to be shown, mention it in the message and you can mention others in the confession.", [pending.users[0].pk])

direct = client.direct_threads()

for dm in direct:
    confession = dm.messages[0]

    if confession.user_id == client.user_id:
        continue

    if confession.text is None:
        continue

    user = client.username_from_user_id(confession.user_id)

    print(f"New Input from {username}: {confession.text}")

    W, H = (1080, 720)

    image = Image.new('RGB', (W, H), color = (33, 33, 33))

    image.save('colored.jpg')

    draw_paragraph_on_image('colored.jpg', confession.text, font_path='noto.ttf', font_size=24)

    client.photo_upload("output.jpg", caption=confession.text)

    client.direct_send("Thank you for your confession. It has been posted anonymously.", [confession.user_id])

client.logout()
