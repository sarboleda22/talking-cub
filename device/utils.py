class GPIO(object):
    """Dummy GPIO class to be imported in case we are working on a x86 (non-RPi) machine."""
    @staticmethod
    def setmode(*args):
        pass
    
    @staticmethod
    def setup(*args):
        pass
    
    @staticmethod
    def input(*args):
        pass
    
    @staticmethod
    def output(*args):
        pass
    
    @staticmethod
    def BCM(*args):
        pass
    
    @staticmethod
    def OUT(*args):
        pass
    
    @staticmethod
    def LOW(*args):
        pass
    
    @staticmethod
    def HIGH(*args):
        pass

def internet_on():
    import requests
    try:
        requests.get('https://google.com', timeout=1)
        return True
    except requests.ConnectionError:
        return False
