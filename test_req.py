import urllib.request
import json
try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/api/v1/banners').read().decode()
    print("Banners response:", response)
except Exception as e:
    print("Error:", e)
