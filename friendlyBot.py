
import pyaudio
import wave
import openai
import time
import os
import keyboard as kb
import colorama

from threading import Thread, Lock
from pynput import keyboard
from pygame import mixer
from gtts import gTTS
from gtts.tokenizer.pre_processors import abbreviations, end_of_line
from playsound import playsound
from langdetect import detect
from boto3 import Session #if using Polly
from contextlib import closing
from colorama import init
init()
from colorama import Fore, Style

class player:
    def __init__(self, wavfile):
        self.wavfile = wavfile
        self.playing = 0 #flag so we don't try to record while the wav file is in use
        self.lock = Lock() #muutex so incrementing and decrementing self.playing is safe
    
    #contents of the run function are processed in another thread so we use the blocking
    # version of pyaudio play file example: http://people.csail.mit.edu/hubert/pyaudio/#play-wave-example
    def run(self):
        with self.lock:
            self.playing += 1
        with wave.open(self.wavfile, 'rb') as wf:
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            data = wf.readframes(8192)
            while data != b'':
                stream.write(data)
                data = wf.readframes(8192)

            stream.stop_stream()
            stream.close()
            p.terminate()
            wf.close()
        with self.lock:
            self.playing -= 1
        
    def start(self):
        Thread(target=self.run).start()
class recorder:
    def __init__(self, 
                 wavfile, 
                 chunksize=8192, 
                 dataformat=pyaudio.paInt16, 
                 channels=2, 
                 rate=44100):
        self.filename = wavfile
        self.chunksize = chunksize
        self.dataformat = dataformat
        self.channels = channels
        self.rate = rate
        self.recording = False
        self.pa = pyaudio.PyAudio()
        openai.api_key =  open('APIKEY/openaikey','r').read()

        # ChatGPT init
        self.MODEL_ENGINE = "text-davinci-003" #"text-curie-001" #
        self.USERNAME = "Christophe"
        self.AI_NAME = "Rose"
        self.INITIAL_PROMPT = self.AI_NAME + ': I am a friendly artificial intelligence.'
        self.conversation_history = self.INITIAL_PROMPT + "\n"
        

        # If using Polly only
        # Create a client using the credentials and region defined in the [adminuser]
        # section of the AWS credentials file (~/.aws/credentials).
        self.polly = Session(profile_name="default").client("polly")

    def start(self):
        #we call start and stop from the keyboard listener, so we use the asynchronous 
        # version of pyaudio streaming. The keyboard listener must regain control to 
        # begin listening again for the key release.
        if not self.recording:
            self.wf = wave.open(self.filename, 'wb')
            self.wf.setnchannels(self.channels)
            self.wf.setsampwidth(self.pa.get_sample_size(self.dataformat))
            self.wf.setframerate(self.rate)
            
            def callback(in_data, frame_count, time_info, status):
                #file write should be able to keep up with audio data stream (about 1378 Kbps)
                self.wf.writeframes(in_data) 
                return (in_data, pyaudio.paContinue)
            
            self.stream = self.pa.open(format = self.dataformat,
                                       channels = self.channels,
                                       rate = self.rate,
                                       input = True,
                                       stream_callback = callback)
            self.stream.start_stream()
            self.recording = True
            print('recording started')
    
    def stop(self):
        if self.recording:         
            self.stream.stop_stream()
            self.stream.close()
            self.wf.close()
            self.recording = False
            print('recording finished')

    def toText(self):
        if not self.recording:         
            file = open(self.filename, "rb")
            self.prompt = openai.Audio.transcribe("whisper-1", file)["text"]
            print(self.prompt)

    def sendToGPT(self):
        self.answer = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": self.prompt}]
        )["choices"][0]["message"]["content"]
        print(self.answer)

    def sendToGPT2(self):
        def get_response(prompt):
            """Returns the response for the given prompt using the OpenAI API."""
            completions = openai.Completion.create(
                     engine = self.MODEL_ENGINE,
                     prompt = prompt,
                 max_tokens = 1024,
                temperature = 0.7,
            )
            return completions.choices[0].text

        def handle_input(
                       input_str : str,
            conversation_history : str,
                        USERNAME : str,
                         AI_NAME : str,
                         ):
            """Updates the conversation history and generates a response using GPT-3."""
            # Update the conversation history
            conversation_history += f"{USERNAME}: {input_str}\n"

            # Generate a response using GPT-3
            message = get_response(conversation_history)
            self.answer = message[len(AI_NAME) + 2:]
            print(self.answer)

            # Update the conversation history
            # conversation_history += f"{AI_NAME}: {message}\n"
            conversation_history += f"{message}\n"

            return conversation_history

        self.conversation_history = handle_input(self.prompt, self.conversation_history, self.USERNAME, self.AI_NAME)      


    def toGoogleSpeech(self):
        self.language=detect(self.answer)
        print(self.language + " detected")
        file="data/output.mp3"
        tts = gTTS(self.answer, lang = self.language, slow=False, pre_processor_funcs = [abbreviations, end_of_line]) 
        tts.save(file)
        Thread(target=self.playMP3(file)).start()    

    def toPollySpeech(self):
        self.language=detect(self.answer)
        print(self.language + " detected")
        file="data/output.mp3"
        VoiceId = None

        if (self.language == 'fr'): VoiceId="Lea"
        if (self.language == 'en'): VoiceId="Amy"
        if (self.language == 'de'): VoiceId="Hannah"
        if (self.language == 'zh-cn'): VoiceId="Zhiyu"
        if (VoiceId is None): VoiceId="Amy"

        try:
            response = self.polly.synthesize_speech(Text=self.answer, OutputFormat="mp3", VoiceId=VoiceId, Engine="neural")
        except (BotoCoreError, ClientError) as error:
            print(error)
            sys.exit(-1)

        if "AudioStream" in response:
                with closing(response["AudioStream"]) as stream:
                   try:
                    # Open a file for writing the output as a binary stream
                        with open(file, "wb") as file1:
                           file1.write(stream.read())
                   except IOError as error:
                      # Could not write to file, exit gracefully
                      print(error)
                      sys.exit(-1)

        else:
            print("Could not stream audio")
            sys.exit(-1)

        Thread(target=self.playMP3(file)).start()    

    def playMP3(self, file):
        mixer.init()
        mixer.music.load(file)
        target=mixer.music.play()
        while mixer.music.get_busy(): # check if the file is playing
            if kb.is_pressed("s"): break
        mixer.music.unload()


class listener(keyboard.Listener):
    def __init__(self, recorder, player):
        super().__init__(on_press = self.on_press, on_release = self.on_release)
        self.recorder = recorder
        self.player = player
    
    def on_press(self, key):
        if key is None: #unknown event
            pass
        elif isinstance(key, keyboard.Key): #special key event
            if key.ctrl and self.player.playing == 0:
                self.recorder.start()
        elif isinstance(key, keyboard.KeyCode): #alphanumeric key event
            if key.char == 'q': #press q to quit
                if self.recorder.recording:
                    self.recorder.stop()
                return False #this is how you stop the listener thread
            if key.char == 'p' and not self.recorder.recording:
                self.player.start()
                
    def on_release(self, key):
        if key is None: #unknown event
            pass
        elif isinstance(key, keyboard.Key): #special key event
            if key.ctrl:
                self.recorder.stop()
                self.recorder.toText()
                self.recorder.sendToGPT2()
                #self.recorder.toGoogleSpeech()
                self.recorder.toPollySpeech()
        elif isinstance(key, keyboard.KeyCode): #alphanumeric key event
            pass

if __name__ == '__main__':
    r = recorder("data/input.wav")
    p = player("data/input.wav")
    l = listener(r, p)
    print(Fore.RED + 'Welcome to friendlyBot, designed by CZhead.eth, under public license, free of use and modification')
    print('hold ctrl to record, press s to stop the bot talking, press q to quit')
    print(Style.RESET_ALL)
    l.start() #keyboard listener is a thread so we start it here
    l.join() #wait for the tread to terminate so the program doesn't instantly clos