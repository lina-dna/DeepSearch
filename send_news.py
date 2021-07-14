import requests
import datetime
import json
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname('DeepSearch'))))
from connector import es_connector
from github import Github


def get_github_repo(access_token, user_name, repository_name):
    """
    github repo object를 얻는 함수
    :param access_token: Github access token
    :param repository_name: repo 이름
    :return: repo object
    """
    g = Github(access_token)
    repo = g.get_user(user_name).get_repo(repository_name)
    return repo


def upload_github_issue(repo, title, body):
    """
    해당 repo에 title 이름으로 issue를 생성하고, 내용을 body로 채우는 함수
    :param repo: repo 이름
    :param title: issue title
    :param body: issue body
    :return: None
    """
    repo.create_issue(title=title, body=body)

    
es = es_connector.ES()
index_name = 'dailynews-naver'
#test index
#index_name = 'test_crawler'

# kst
yester_day = datetime.date.today() - datetime.timedelta(days=1)
# utc
#yester_day = datetime.date.today()
target_day = yester_day.strftime('%Y-%m-%d')
webhook_url = os.getenv('WEBHOOK')

issue_day = datetime.date.today() + datetime.timedelta(days=1)

query = '''
{"sort": [
    {
      "토픽": {
        "order": "asc"
      }
    }
  ],
  "query": {
    "match": {
      "작성일시": "%s"
    }
  },
  "_source": ["토픽", "제목", "URL", "댓글수"]
}
''' % (target_day)

res = es.searchFilter(index = index_name, body = query)


# slack webhook

webhook_payload = {'text':'Daily News Monitoring', 'blocks':[]}
info_section = {'type':'section', 'text': {'type':'mrkdwn','text':f"{issue_day}"}}
divider_section = {'type':'divider'}
webhook_payload['blocks'].append(info_section)
webhook_payload['blocks'].append(divider_section)

topic = res['hits']['hits'][0]['_source']['토픽']
topic_section = {'type':'section', 'text': {'type':'mrkdwn','text':f"*[{topic} 소식]*"}}
webhook_payload['blocks'].append(topic_section)

j=0
for i in range(len(res['hits']['hits'])):
    j += 1
    temp_topic = res['hits']['hits'][i]['_source']['토픽']
    title = res['hits']['hits'][i]['_source']['제목']
    url = res['hits']['hits'][i]['_source']['URL']
    n_com = res['hits']['hits'][i]['_source']['댓글수']

    if temp_topic == '삼성생명':
        temp_topic = '업계'
    elif temp_topic == '라이나생명':
        temp_topic = '당사'
            
    if topic != temp_topic:
        topic = temp_topic
        webhook_payload['blocks'].append(divider_section)
        j=1
        topic_section = {'type':'section', 'text': {'type':'mrkdwn','text':f"*[{topic} 소식]*"}}
        webhook_payload['blocks'].append(topic_section)
        
    news_section = {'type':'section', 'text' :{'type':'mrkdwn', 'text': f"{j}. {title} [{n_com}] (<{url}|Link>) "}}
    webhook_payload['blocks'].append(news_section)
    
#requests.post(url=webhook_url, json=webhook_payload)


#github readme

upload_contents = '## Daily News Monitoring \n\n'
upload_contents += f"{issue_day} \n\n"
upload_contents += "----------\n\n"
topic = res['hits']['hits'][0]['_source']['토픽']
upload_contents += f"*[{topic} 소식]*\n\n"
j=0
for i in range(len(res['hits']['hits'])):
    j += 1
    temp_topic = res['hits']['hits'][i]['_source']['토픽']
    title = res['hits']['hits'][i]['_source']['제목']
    url = res['hits']['hits'][i]['_source']['URL']
    n_com = res['hits']['hits'][i]['_source']['댓글수']
    if temp_topic == '삼성생명':
        temp_topic = '업계'
    elif temp_topic == '라이나생명':
        temp_topic = '당사'
    if topic != temp_topic:
        topic = temp_topic
        upload_contents += "----------\n\n"
        j=1
        upload_contents += f"*[{topic} 소식]*\n\n"
    upload_contents += f"{j}. {title} [{n_com}] ([Link]({url}))\n\n"
    
    
# os.environ["UPLOAD_CONTENTS"] = upload_contents

# generate result as github issue
issue_title = (
    f"{issue_day} Daily News Monitoring"
)
access_token = os.getenv('FULL_ACCESS_TOKEN')
user_name = "lina-dna"
repository_name = "DeepSearch"

repo = get_github_repo(access_token,user_name,repository_name)
upload_github_issue(repo, issue_title, upload_contents)
print("Upload Github Issue Success!")

with open("README.md", "w") as readmeFile:
    readmeFile.write(upload_contents)
