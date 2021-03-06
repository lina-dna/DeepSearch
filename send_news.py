import requests
import datetime
import json
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname('DeepSearch'))))
from connector import es_connector,strapi_connector
from github import Github
from wordcloud import WordCloud
import matplotlib.pyplot as plt 

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
# yester_day = datetime.date.today() - datetime.timedelta(days=1)
# utc
yester_day = datetime.date.today()

target_day = yester_day.strftime('%Y-%m-%d')
webhook_url = os.getenv('WEBHOOK')

issue_date = datetime.date.today() + datetime.timedelta(days=1)

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
  "_source": ["토픽", "제목", "URL", "본문", "댓글수"]
}
''' % (target_day)

res = es.searchFilter(index = index_name, body = query)


# filter keywords

strapi = strapi_connector.Strapi()
keywords_db = strapi.get_db(collection = 'crawler-keywords')
filter_keywords = [K['Keywords'] for K in keywords_db if K['type'] == 'filter']

# slack webhook

webhook_payload = {'text':'Daily News Monitoring', 'blocks':[]}
info_section = {'type':'section', 'text': {'type':'mrkdwn','text':f"{issue_date}"}}
divider_section = {'type':'divider'}
webhook_payload['blocks'].append(info_section)
webhook_payload['blocks'].append(divider_section)

topic = res['hits']['hits'][0]['_source']['토픽']
topic_section = {'type':'section', 'text': {'type':'mrkdwn','text':f"*[{topic} 소식]*"}}
webhook_payload['blocks'].append(topic_section)

j=0
for i in range(len(res['hits']['hits'])):
    #filtering news
    if any(word in res['hits']['hits'][i]['_source']['본문'] for word in filter_keywords):
        continue
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
    
requests.post(url=webhook_url, json=webhook_payload)
    

# word cloud

tagging_url = os.getenv('SEQUENCE_TAGGING')
pos_url = tagging_url + 'sequence_tagging/pos/'

def get_nouns(body: str):
    nouns = [word[0] for word in requests.get(pos_url + f"{body}").json() if word[1] == 'NNG']
    return nouns

nouns_list = []
for i in range(len(res['hits']['hits'])):
    if any(word in res['hits']['hits'][i]['_source']['본문'] for word in filter_keywords):
        continue
    body = res['hits']['hits'][i]['_source']['본문']
    split_body = body.split('\n')
    split_body = list(filter(None, split_body))
    nouns_list += (list(map(lambda x : get_nouns(x),split_body)))
    
nouns_list = list(map(' '.join, nouns_list))
nouns_list = ' '.join(nouns_list)
                     
f = open("etc/stopwords_korean.txt", "rt", encoding="utf-8")
lines = f.readlines()
stop_words = []
for line in lines:
    line = line.replace('\n', '')
    stop_words.append(line)
                    
font_path = "etc/NanumGothic.ttf"
wordcloud = WordCloud(font_path=font_path, background_color='white', colormap='winter', stopwords=stop_words).generate(nouns_list)
plt.imshow(wordcloud, interpolation='lanczos')
plt.axis('off')
plt.savefig(f'image/{issue_date}_word_cloud.png')




#github readme

upload_contents = '## Daily News Monitoring \n\n'
upload_contents += f"{issue_date} \n\n"
upload_contents += "----------\n\n"
upload_contents += '### Daily Hot Keywords \n\n'
upload_contents += f"![word_cloud](image/{issue_date}_word_cloud.png)\n\n"
upload_contents += "----------\n\n"
topic = res['hits']['hits'][0]['_source']['토픽']
upload_contents += f"*[{topic} 소식]*\n\n"
j=0
for i in range(len(res['hits']['hits'])):
    #filtering news
    if any(word in res['hits']['hits'][i]['_source']['본문'] for word in filter_keywords):
        continue
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

# generate result as github issue
issue_title = (
    f"{issue_date} Daily News Monitoring"
)
access_token = os.getenv('FULL_ACCESS_TOKEN')
user_name = "lina-dna"
repository_name = "DeepSearch"

repo = get_github_repo(access_token,user_name,repository_name)
upload_github_issue(repo, issue_title, upload_contents)
print("Upload Github Issue Success!")

with open("README.md", "w") as readmeFile:
    readmeFile.write(upload_contents)
