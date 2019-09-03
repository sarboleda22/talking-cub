from __future__ import division

import os
import re
import sys
import time

import google.api_core.exceptions as google_exceptions
from google.cloud import texttospeech
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types

from six.moves import queue

import pyaudio
import simpleaudio as sa
import requests
import json
from fuzzywuzzy import fuzz

from constants import RATE, CHUNK, ACTIVATION_WORD, ANSWER_SVC_URL, ANSWER_SVC_TOKEN
from utils import internet_on

try:
    import RPi.GPIO as GPIO
    print("GPIO Module imported.")
except ImportError:
    from utils import GPIO


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()
        GPIOSetup.setup() # return to original state

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


class GPIOSetup(object):
    """Mostly for debugging porpuses in a x86 system and more modularization."""
    @staticmethod
    def setup():
        if GPIOSetup.is_armv7l:
            # Set Up output GPIO Pins and set Low
            GPIO.setmode(GPIO.BCM) # numerical mode
            GPIO.setup(17, GPIO.OUT) # white LED
            GPIO.setup(18, GPIO.OUT) # red LED
            GPIO.setup(27, GPIO.OUT) # green LED
            GPIO.output(17, GPIO.LOW)
            GPIO.output(18, GPIO.LOW)
            GPIO.output(27, GPIO.LOW)

    @staticmethod
    def is_armv7l():
        """Get the host's sys architecture"""
        return 'armv7l' in os.uname().machine
    
    @staticmethod
    def ready():
        """
        This is called when the system is ready to go.
        Green LED -> ON
        """
        GPIO.output(27, GPIO.HIGH)

    @staticmethod
    def no_internet():
        """
        In case of no internet connection, this funciton makes the GREEN LED blink.
        It just changes it's state once, so it depends on the function calling it."""
        if GPIO.input(27):
            GPIO.output(27, GPIO.LOW)
            return
        GPIO.output(27, GPIO.HIGH)

    @staticmethod
    def unactive():
        """
        State where the speaker is waiting for the activation word.
        | Green: ON | White: OFF | Red: OFF |
        """
        if GPIOSetup.is_armv7l:
            GPIO.output(27, GPIO.HIGH)
            GPIO.output(17, GPIO.LOW)
            GPIO.output(18, GPIO.LOW)

    @staticmethod
    def active():
        """
        State where the speaker is actively listening for a question after the activation word was heard.
        | Green: ON | White: ON | Red: OFF |
        """
        if GPIOSetup.is_armv7l:
            GPIO.output(27, GPIO.HIGH)
            GPIO.output(17, GPIO.HIGH)
            GPIO.output(18, GPIO.LOW)

    @staticmethod
    def processing():
        """
        State where the speaker is either processing or outputing something. Mainly audio.
        | Green: ON | White: OFF | Red: ON |
        """
        if GPIOSetup.is_armv7l:
            GPIO.output(27, GPIO.HIGH)
            GPIO.output(17, GPIO.LOW)
            GPIO.output(18, GPIO.HIGH)


def get_audio_from_string(answer, text_to_speech_client):
    """Uses GCloud Text to Speech API to generate an output.wav audio file with the response and plays it."""
    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    voice = texttospeech.types.VoiceSelectionParams(
        language_code='en-US',
        ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.LINEAR16)

    # Set the text input to be synthesized
    synthesis_input = texttospeech.types.SynthesisInput(text=answer)

    response = text_to_speech_client.synthesize_speech(synthesis_input, voice, audio_config)

    # The response's audio_content is binary.
    with open('output.wav', 'wb') as out:
        # Write the response to the output file.
        out.write(response.audio_content)
        print('Audio content written to file "output.wav"')


def get_answer_dict(question):
    """
    Performs a GET request with the given question to our API service.
    The app responds with the most similar question, and it's answer.
    Returns a dict of the form {question:str, answer:str, accuracy:int, times_asked:int}
    """
    params = {"question" : question}
    headers = {"Authorization" : ANSWER_SVC_TOKEN}
    r = requests.get(ANSWER_SVC_URL, params=params, headers=headers)
    answer_dict = json.loads(r.text)
    return answer_dict


def play_answer_audio():
    """Plays audio file using simpleaudio, assuming the file name is always output.wav"""
    filename = 'output.wav'
    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()
    # Wait an extra second so that the listening loop doesn't catch the audio.
    time.sleep(1)


def listening_loop(responses, text_to_speech_client):
    """Iterates through server responses and prints them.

    The responses passed is a generator that will block until a response
    is provided by the server.

    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.

    In this case, responses are provided for interim results as well. If the
    response is an interim one, print a line feed at the end of it, to allow
    the next result to overwrite it, until the response is a final one. For the
    final one, print a newline to preserve the finalized transcription.
    """

    activated = False
    recommended_question = None
    num_chars_printed = 0

    for response in responses:
        if not response.results:
            continue

        # We only care about the first result being considered.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            # First, clear Terminal
            #os.system('cls' if os.name == 'nt' else 'clear')
            print(transcript + overwrite_chars)

            # Exit recognition if told to do so.
            if re.search(r'\b(exit|quit)\b', transcript, re.I):
                print('Exiting..')
                break

            # Wait for activation word
            if not activated and fuzz.ratio(transcript.lower().strip(), ACTIVATION_WORD.lower()) >= 67:
                activated = True
                GPIOSetup.active()
                print("Activated = True")

            elif activated:
                # White LED goes OFF and Red ON to indicate that it's not listening anymore
                GPIOSetup.processing()
                print("In activated branch. Getting API response...")
                response = get_answer_dict(question=transcript)

                acc_ratio = response['accuracy']
                answer = response['answer']
                question = response['question']

                if acc_ratio >= 70:
                    get_audio_from_string(answer, text_to_speech_client)
                    play_answer_audio()
                else:
                    recommended_question = question
                    sorry_text = "Sorry, I did not get that. Did you mean to ask {}".format(recommended_question)
                    get_audio_from_string(sorry_text, text_to_speech_client)
                    play_answer_audio()
                GPIOSetup.unactive()
                activated = False
            num_chars_printed = 0


def stream_audio(tts_client, stt_client, streaming_config):
    """Audio streaming function. To be exited once we exceed google's max stream duration."""
    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)
        responses = stt_client.streaming_recognize(streaming_config, requests)
        try:
            listening_loop(responses, tts_client)
        except google_exceptions.OutOfRange:
            return


def wait_internet_conn():
    if internet_on():
        GPIOSetup.ready()
        return
    time.sleep(1)
    GPIOSetup.no_internet()
    wait_internet_conn()


def main():
    """The main event."""
    GPIOSetup.setup()

    language_code = 'en-US'  # a BCP-47 language tag
    dir_path = os.getcwd()
    gc_key_file = 'gc_private_key.json'
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '{}/{}'.format(dir_path, gc_key_file)

    # Speech-To-Text and Text-To-Speech clients config
    tts_client = texttospeech.TextToSpeechClient()
    stt_client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)
    
    # Wait for an internet connection.
    wait_internet_conn()
    stream_audio(tts_client, stt_client, streaming_config)
    main()

if __name__ == '__main__':
    try:
        main()
    except:
        GPIOSetup.setup() # Turn all LEDs OFF
