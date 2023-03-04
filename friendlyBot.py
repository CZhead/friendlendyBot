from threading import Thread, Lock
from pynput import keyboard
from pygame import mixer
from gtts import gTTS
from gtts.tokenizer.pre_processors import abbreviations, end_of_line
from playsound import playsound
from langdetect import detect

import pyaudio
import wave
import openai
import time
import os


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
            self.language=detect(self.prompt)
            print(self.language + " detected")
            print(self.prompt)

    def sendToGPT(self):
        self.answer = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": self.prompt}]
        )["choices"][0]["message"]["content"]
        print(self.answer)

    def toSpeech(self):
        
        file="data/output.mp3"
        tts = gTTS( self.answer, lang = self.language, slow=False, pre_processor_funcs = [abbreviations, end_of_line]) 
        tts.save(file)
        Thread(target=self.playMP3(file)).start()    

    def playMP3(self, file):
        mixer.init()
        mixer.music.load(file)
        target=mixer.music.play()
        while mixer.music.get_busy(): # check if the file is playing
            continue
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
                self.recorder.sendToGPT()
                self.recorder.toSpeech()
        elif isinstance(key, keyboard.KeyCode): #alphanumeric key event
            pass

if __name__ == '__main__':
    r = recorder("data/input.wav")
    p = player("data/input.wav")
    l = listener(r, p)
    print('hold ctrl to record, press p to playback, press q to quit')
    l.start() #keyboard listener is a thread so we start it here
    l.join() #wait for the tread to terminate so the program doesn't instantly clos