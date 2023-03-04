# FriendlyBot 
## Description
This is a conversational BOT for educational purpose.\
It can recognize which language is spoken and answer accordingly.\
This bot is using :\
Whisper API: to convert speech to text\
langdetect: to detect the language spoken\
ChatGPT: to answer the question/complete the conversation\

AWS Polly: to convert the answer from text to speech (AWS Cli installation and configuration required)\
You can alternativelw use Google TextToSpeech to convert the answer from text to speech. (and replace toGoogleSpeech by toPollySpeech)

## Installation
### Clone this repository: 
git clone https://github.com/CZhead/friendlendyBot.git\
### Install python dependencies:
pip install pynput, pygame, gtts, playsound, langdetect, pyaudio, wave, openai, boto3
### Create an API key 
Go to https://platform.openai.com/account/api-keys and create a key\
Create a file openaikey in APIKEY folder
Copy the value of the key in the file

## Launch bot
python .\friendlyBot.py
