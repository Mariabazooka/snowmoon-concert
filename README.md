# Snowmoon - "The Concert" (Chapter 1 adaptation)

A 47-second audiovisual adaptation of the concert-escape scene from Chapter 1 of Snowmoon by Vitalik Buterin (https://vitalik.eth.limo/snowmoon/), made for the poidh "Bring Snowmoon to Life" bounty.

Video: https://x.com/mariabazooka/status/2105765980597354936?s=46

## How it was made
Everything is generated from code. No AI-generated images, audio or video.
- render.py draws every frame with Python + Pillow (1280x720, 24 fps).
- The soundtrack is synthesized in the same script with numpy/scipy.
- ffmpeg encodes frames and audio into snowmoon-concert.mp4.
- The script was written with Claude (Anthropic) from the text of Chapter 1.

## Run it
pip install pillow numpy scipy
(ffmpeg must be installed)
python render.py

## License
GPL v3. Source text by Vitalik Buterin.
