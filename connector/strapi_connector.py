import requests
import json
import os

class Strapi:
    def __init__(self):
        self.hosts = os.getenv('STRAPI_HOSTS')
    
    def get_db(self,collection: str = 'crawler-keywords'):
        response = requests.get(self.hosts + collection,
                      headers={
                        'Content-Type': 'application/json'
                      })
        data = json.loads(response.text)
        
        return data 