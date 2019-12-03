# Talking Cub
A Smart Speaker built for Eastern Nazarene College's fair.

## Installation and Initial Set Up
This software makes use of GCloud text-to-speech and speech-to-text APIs. Make sure you create an account and generate a private key to be used.

### Raspberry Pi - Speaker
1. Copy a valid GCloud private key as ```gc_private_key.json``` in this directory.

2. [Install](https://github.com/thomas-vl/GoogleSpeechRPi) Google Cloud SDK.
3. Install ```google-cloud-speech``` and ```google-cloud-texttospeech``` packages. 

```
sudo apt-get install portaudio19-dev python-pyaudio python3-pyaudio alsa-tools alsa-utils
```
4. Install PyAudio
```
pip3 install pyaudio
```

### Web App
The web server can either be run locally in the Raspberry Pi or in an external host using ```docker-compose``` for both cases. Take into account that in either case, you will have to edit *ANSWER_SVC_URL* in ```device/constants.py``` to match your endpoint's IP. That is ```ANSWER_SVC_URL = "http://localhost:8000/api/v1/answer/"``` for the Raspberry Pi, or ```ANSWER_SVC_URL = "http://{{YOUR HOST'S IP}}/api/v1/answer/"```.

**If running locally in the Pi:**
```
$ docker-compose -f web/docker-compose.pi.yml
```

**If installing in an external host:**
```
$ docker-compose -f web/docker-compose.yml
```

## Run
```
$ python3 device/app.py
```

## TODO
### Webapp
1. Add `last_edited` to the webapp's inquiry DB and make inquiries in dashboard ordered by date.
2. Make the PIN evaluation (authorization) better. Possibly taking it from an env_variable or docker secret.
### Speaker - Device
