# FriendlendyBot 
## Description
This is a conversational BOT for educational purpose.\
It can recognize which language is spoken and answer accordingly.\
This bot is using :\
Whisper API: to convert speech to text\
langdetect: to detect the language spoken\
ChatGPT: to answer the question/complete the conversation\
Google TextToSpeech: to convert the answer from text to speech.

## Installation
### Clone this repository: 
git clone https://github.com/CZhead/friendlendyBot.git\
### Install python dependencies:\
pip install pyput pygame, gtts, playsound, langdetect, pyaudio, wave, openai, time, os\
### Create an API key 
Go to https://platform.openai.com/account/api-keys and create a key\
Create a file openaikey in APIKEY folder
Copy the value of the key in the file

## Launch bot
python .\friendlyBot.py
