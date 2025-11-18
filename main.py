import os

from dotenv import load_dotenv
from argparse import ArgumentParser

from agent_analyst import Agent_Analyst




load_dotenv(".env")
API_KEY = os.getenv("GOOGLE_API", "")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", None)
assert PROJECT_ID is not None, "Provide Google Project ID"



def _parse_args():
    parser = ArgumentParser()
    parser.add_argument("--api", default="", type=str, help="Google API key for model running")
    parser.add_argument("--ollama", default="", type=str, help="Model name to run with ollama")

    return parser.parse_args()

def get_llm(local=""):
    """Create an LLM instance"""
    if len(local) == 0:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(google_api_key=API_KEY, model="gemini-2.5-flash")
    else:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=local, temperature=0.4, num_ctx="8192", num_predict="4096", keep_alive="5m")
    return llm






if __name__ == "__main__":
    args = _parse_args()

    if len(args.api) > 0:
        API_KEY = args.api
    assert len(API_KEY) > 0 or not args.ollama, "API key not provided"


    AA = Agent_Analyst(llm_txt=get_llm(local=args.ollama))

    user_msg = ""

    print("\tWelcome to chat with AI data analyst.\n\tWrite your message to AI assistant.\n\tto finish chatting write: '/exit' or '/quit'\n")
    while True:
        user_msg = input("\n\t\033[1;94mNatural intelligence:\033[00m\n")
        print(" -"* 40)

        if user_msg.lower() in ["/exit", "/quit"]:
            exit()

        print("\n\t\033[1;94mAI:\033[00m\n", "\033[92m" + AA.chat(user_msg) + "\033[00m", "\n", " -"* 40)






