# Talking Cub
A Smart Speaker built for Eastern Nazarene College's fair.

## Installation
1. Copy a valid GCloud private key as ```gc_private_key.json``` in this directory.

2. [Install](https://github.com/thomas-vl/GoogleSpeechRPi) Google Cloud SDK.
3. Install the following packages. 

```
sudo apt-get install portaudio19-dev python-pyaudio python3-pyaudio
```
4. Install PyAudio
```
pip install pyaudio
```

## TODO
### Webapp
1. Add `last_edited` to the webapp's inquiry DB and make inquiries in dashboard ordered by date.
2. Make the PIN evaluation (authorization) better. Possibly taking it from an env_variable or docker secret.
### Speaker - Device
