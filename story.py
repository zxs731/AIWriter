from dotenv import load_dotenv  
import os
import json, ast
import requests
import openai
import streamlit as st
import time
import re
from datetime import datetime, timezone, timedelta  

# 加载.env文件  
load_dotenv("en1106.env")  

os.environ["OPENAI_API_TYPE"] = os.environ["Azure_OPENAI_API_TYPE1"]
os.environ["OPENAI_API_BASE"] = os.environ["Azure_OPENAI_API_BASE1"]
os.environ["OPENAI_API_KEY"] = st.secrets["key"]
os.environ["OPENAI_API_VERSION"] = os.environ["Azure_OPENAI_API_VERSION1"]
BASE_URL=os.environ["OPENAI_API_BASE"]
API_KEY=os.environ["OPENAI_API_KEY"]

CHAT_DEPLOYMENT_NAME=os.environ.get('AZURE_OPENAI_API_CHAT_DEPLOYMENT_NAME')
EMBEDDING_DEPLOYMENT_NAME=os.environ.get('AZURE_OPENAI_API_EMBEDDING_DEPLOYMENT_NAME')

openai.api_type = os.environ["OPENAI_API_TYPE"]
openai.api_base = os.environ["OPENAI_API_BASE"]
openai.api_version = "2023-07-01-preview"
openai.api_key = os.getenv("OPENAI_API_KEY")

getStoryElements = {
    'name': 'getStoryElements',
    'description': '专门用于根据提供的写作要求和背景，生成基本的故事元素，如：标题、背景、目录',
    'parameters': {
        'type': 'object',
        'properties': {
            'title': {
                'type': 'string',
                'description': '故事的标题'
            },
            'background': {
                'type': 'string',
                'description': '故事的背景'
            },
            'toc': {
                'type': 'string',
                'description': '故事的章节目录'
            },
            'count_of_chapter': {
                'type': 'string',
                'description': '故事的章节目录条数'
            }
        },
        'required': ['requirement','title','background','toc','count_of_chapter']
    }
}
tools = [
    {
        "type": "function",
        "function":getStoryElements
    }
]
def getLLMResponse(messages,tools=None,checkMinResponseLength=0):
    response = openai.ChatCompletion.create(
                engine="gpt-35-turbo-1106",
                #model="gpt-35-turbo-1106",
                messages=messages,
                tools=tools,
            )
    maxRetry=3
    curRetry=0
    while checkMinResponseLength>0 and 'tool_calls' not in response.choices[0].message and 'content' in response.choices[0].message  and len(response.choices[0].message.content)<checkMinResponseLength and curRetry<maxRetry:
        response = openai.ChatCompletion.create(
                engine="gpt-35-turbo-1106",
                #model="gpt-35-turbo-1106",
                messages=messages,
                tools=tools,
            )
        curRetry+=1
    return response
               
    

if "key" not in st.session_state:
    st.session_state.key = None

st.sidebar.markdown("# AI写作机器人🤖️⚡️💎")
key = st.sidebar.text_input("Your key", type="password")
model=st.sidebar.selectbox(
    'Model',
    ( "gpt-35-turbo-1106", "gpt-4"))
if not key:
    st.info("Please add your key to continue.")
    st.stop()
elif str(datetime.now(timezone(timedelta(hours=8))).hour)!=key:
    st.info("Please input valid key to continue.")
    st.stop()
else:
    st.session_state.key=key    



if not key:
    st.stop()
    
uploaded_files = st.sidebar.file_uploader("Choose upload files", accept_multiple_files=True)  
current_directory = os.getcwd()  
  
for uploaded_file in uploaded_files:  
    file_path = os.path.join(current_directory, uploaded_file.name)  
    with open(file_path, 'wb') as f:  
        f.write(uploaded_file.read())  
    st.write(f'Received your file {uploaded_file.name}!')  

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    print(message)
    if "role" in message and (message["role"]=="user" or message["role"]=="assistant" ) and message["content"] is not None:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
                   


def writeReply(cont,msg):
    #print(msg)
    cont.write(msg)
    print(msg)
    

if prompt := st.chat_input():
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown('Please waiting...')
        exp = st.expander("AI messages trace", expanded=False)
        requirement=prompt
        sys_msg={"role":"system","content":"你是一个虚拟写作助手。"}
        user_msg={"role":"user","content":f'根据写作要求：{requirement}，写一个虚拟小说的标题，背景，章节等。'}
        res=getLLMResponse([sys_msg,user_msg],tools=tools)
        print("elements creation done!")
        
        print(res.choices[0].message.tool_calls[0].function.arguments)
        j=json.loads(res.choices[0].message.tool_calls[0].function.arguments)
        assistant_response= f'''
写作要求:{requirement}\n
标题: {j["title"]}\n
背景: {j["background"]}\n
章节:\n{j["toc"]}\n'''
        full_response=''
        for chunk in re.split(r'(\s+)', assistant_response):
            full_response += chunk + " "
            time.sleep(0.01)

            # Add a blinking cursor to simulate typing
            message_placeholder.markdown(full_response + "▌")
            
        pre_msg=None
        for i in range(1, int(j["count_of_chapter"])+1):  
            user_msg={"role":"user","content":f'''按照如下信息写作指定章节。
标题:{j["title"]}
背景:{j["background"]}
章节列表:{j["toc"]}
选定的章节:第{i}章
按照上述要求编写选定章节内容。'''}
            if pre_msg is not None:
                res=getLLMResponse([sys_msg]+pre_msg+[user_msg],tools=None,checkMinResponseLength=100) 
            else:
                res=getLLMResponse([sys_msg,user_msg],tools=None,checkMinResponseLength=100) 
            print(res.choices[0].message.content)
            exp.write(pre_msg)
            assistant_response = f'\n\n{res.choices[0].message.content}'
            pre_msg=[user_msg,{"role":"assistant","content":assistant_response}]
            
            for chunk in re.split(r'(\s+)', assistant_response):
                full_response += chunk + " "
                time.sleep(0.01)
    
                # Add a blinking cursor to simulate typing
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content":full_response})
        #st.session_state.messages.append({"role": "assistant", "content": re})
