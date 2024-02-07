import os

import autogen
import chainlit as cl
from dotenv import find_dotenv, load_dotenv

from agents.chainlit_agents import (ChainlitAssistantAgent,
                                    ChainlitUserProxyAgent)
from initiate_chat import initiate_chat
from prompt import get_assistant_prompt, get_manager_prompt

load_dotenv(find_dotenv())

# -------------------- GLOBAL VARIABLES AND AGENTS ----------------------------------- # 
USER_PROXY_NAME = "Query Agent"
ASSISTANT = "Assistant"

# -------------------- Config List. Edit to change your preferred model to use ----------------------------- # 
config_list = autogen.config_list_from_dotenv(
    dotenv_file_path = '.env',
    model_api_key_map={
        "gpt-3.5-turbo-1106": "OPENAI_API_KEY",
    },
    filter_dict={
        "model": {
            "gpt-3.5-turbo-1106",
        }
    }
)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
llm_config = {"config_list": config_list, "api_key": OPENAI_API_KEY, "cache_seed": 42}

# -------------------- Instantiate agents at the start of a new chat. Call functions and tools the agents will use. ---------------------------- #
@cl.on_chat_start
async def on_chat_start():
  try:
    assistant = ChainlitAssistantAgent(
        name="Assistant", llm_config=llm_config,
        system_message=get_assistant_prompt(),
        description="Assistant Agent"
    )
    
    user_proxy = ChainlitUserProxyAgent(
        name="User_Proxy",
        human_input_mode="ALWAYS",
        llm_config=llm_config,
        # max_consecutive_auto_reply=3,
        # is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        code_execution_config=False,
        system_message=get_manager_prompt(),
        description="User Proxy Agent"
    )
    print("Set agents.")

    cl.user_session.set(USER_PROXY_NAME, user_proxy)
    cl.user_session.set(ASSISTANT, assistant)
    
    msg = cl.Message(content=f"""こんにちは！何をお手伝いしましょう。      
                     """, 
                     author="User_Proxy")
    await msg.send()

    print("Message sent.")
    
  except Exception as e:
    print("Error: ", e)
    pass

# -------------------- Instantiate agents at the start of a new chat. Call functions and tools the agents will use. ---------------------------- #
@cl.on_message
async def run_conversation(message: cl.Message):
  #try:
    print("Running conversation")
    llm_config = {"config_list": config_list, "api_key": OPENAI_API_KEY, "cache_seed": 42}

    CONTEXT = message.content
    MAX_ITER = 10
    assistant = cl.user_session.get(ASSISTANT)
    user_proxy = cl.user_session.get(USER_PROXY_NAME)
    print("Setting grouipchat")
    groupchat = autogen.GroupChat(agents=[user_proxy, assistant], messages=[], max_round=MAX_ITER)
    manager = autogen.GroupChatManager(groupchat=groupchat,llm_config=llm_config)

# -------------------- Conversation Logic. Edit to change your first message based on the Task you want to get done. ----------------------------- # 
    if len(groupchat.messages) == 0:
      message = f"""Do the task based on the user input: {CONTEXT}."""
      # user_proxy.initiate_chat(manager, message=message)
      await cl.Message(content=f"""Starting agents on task...""").send()
      await cl.make_async(user_proxy.initiate_chat(manager, message=initiate_chat(message), config_list=config_list))( manager, message=message, )
    elif len(groupchat.messages) < MAX_ITER:
      await cl.make_async(user_proxy.send)( manager, message=CONTEXT, )
    elif len(groupchat.messages) == MAX_ITER:  
      await cl.make_async(user_proxy.send)( manager, message="exit", )
      
#   except Exception as e: 
#     print("Error: ", e)
#     pass