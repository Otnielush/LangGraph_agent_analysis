from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

from langchain.tools import tool

import pandas as pd
import os
from dotenv import load_dotenv


from bq_client import BigQueryRunner


VERBOSE = 1


load_dotenv(".env")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", None)
BQ_runner = BigQueryRunner(PROJECT_ID)


class CurrentDataKeeper:
    data: pd.DataFrame = []


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    tasks: str
    last_sql_query: str


Current_data = CurrentDataKeeper()


class Agent_Analyst:
    def __init__(self, llm_txt):
        self.llm = llm_txt
        self.chat_messages = []
        self.bq_runner = BQ_runner
        self.bq_schema = BQ_runner.get_schema()
        self.current_data: pd.DataFrame = None
        self.last_sql_query = ""

        self.graph = self._build_graph()


    def chat(self, message):
        self.chat_messages.append(HumanMessage(content=message))
        state = self.graph.invoke({'messages': self.chat_messages})
        msg = state['messages'][-1].content.strip()
        self.chat_messages.append(AIMessage(content=msg))
        return msg


    def _build_graph(self):
        self.current_data = Current_data
        graph = StateGraph(GraphState)
        graph.add_node("chat", create_chat_node(self.llm,
                                           instruction="""You are data analyst assistant, making dialog with client. 
You database with all information you need about product sales, you can use tool 'get_analysis' to get all necessary data.""",
                                           tools=[get_analysis]))


        graph.add_node("sql", create_sql_node(self.llm))
        # graph.add_node("pandas", create_pandas_node(self.llm))


        graph.add_edge(START, "chat")
        graph.add_edge("chat", END)
        graph.add_edge("sql", END)
        # graph.add_edge("sql", "pandas")
        # graph.add_edge("pandas", END)
        graph.add_conditional_edges("chat", cond_chat_to_database, ["sql", "pandas", END])
        return graph.compile()




def create_chat_node(llm, instruction, tools=None):
    if tools:
        llm = llm.bind_tools(tools)
    def func(state):
        msgs = [SystemMessage(content=instruction)] + state['messages']
        output = llm.invoke(msgs)
        return {'messages': AIMessage(content=get_content(output), tool_calls=output.tool_calls)}

    return func



def create_sql_node(llm):
    llm = llm.bind_tools([query_database])

    def func(state):
        if VERBOSE > 0:
            print(" =" * 10, "SQL node")

        tasks = "\n".join([tc['args']['task'] for tc in state['messages'][-1].tool_calls])

        msgs = [SystemMessage(content=f"""You are a data analyst with expertise in gathering data from database.
Your work is to write workable sql queries to gather needed data from database and combine it into one table.
Do not write complicated queries to solve task immediately, just gather needed information to solve task.
Final analysis will be processed in next steps, you need just to provide table with useful information. 

You have:
* online database with SQL calling protocol (name: DATASET)

**Database schema:** (DATASET)
{BQ_runner.get_schema()}


All data located in `DATASET.name_of_table`

**Query example**
Task: 
    Show me 10 products generating best income
Query:
SELECT oi.product_id, SUM(oi.sale_price) AS total_revenue
FROM `bigquery-public-data.thelook_ecommerce.order_items` as oi
GROUP BY oi.product_id
ORDER BY total_sales DESC
LIMIT 10;

**How to act**:
- Describe your logic in steps how you gonna build sql query.
- Then call tool "query_database" and pass sql query.
- After receiving result from tool, you must observe them and decide is it was successful or not.
- If results not good you should fix sql query, simplify logic in query and call tool again.
- When you finished to query database write done. Do not write answer.
"""), HumanMessage(tasks)]

        calls_msgs = []
        observation = ""
        calling_tools = True
        max_tries = 3
        while calling_tools:
            max_tries -= 1
            output = llm.invoke(msgs + calls_msgs)
            if len(output.tool_calls) > 0 and max_tries > 0:
                calls_msgs.insert(0, output)
                for tool_call in output.tool_calls:
                    print("= = = = = sql_node:", output.content, "\n\n", tool_call)
                    data = query_database.invoke(tool_call["args"])
                    print("\n", data, "\n")
                    if isinstance(data, pd.DataFrame):
                        observation = f"data:\n{data}"
                    else:
                        observation = data
                    calls_msgs.insert(1, ToolMessage(content=observation, tool_call_id=tool_call["id"]))
                    calls_msgs = calls_msgs[:2]
            else:
                calling_tools = False

        Current_data.data = data

        return {"messages": observation + "\n\n" + get_content(output), "data": data}

    return func


def create_pandas_node(llm):

    def func(state):
        df = Current_data.data
        if VERBOSE > 0:
            print("= = = = = pandas_node", f"({len(df) = })")
        agent_executor = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)
        msgs = [SystemMessage(f"""You are a data analyst with expertise in processing analysis on pandas DataFrame table.
Your work is to give answers to user using information in pandas dataframe. You can manipulate and transform data as you wish while preparing answer.
Use tool 

**Current dataframe columns**:
{df.columns}

**Current dataframe size**:
{df.shape = }

"""), state["messages"][-1]]
        result = agent_executor.invoke({"input": msgs})
        if VERBOSE > 0:
            print("= = = = = = result:", result)
        return {"messages": get_content(result)}

    return func


def cond_chat_to_database(state):
    last_message = state["messages"][-1]
    if VERBOSE > 0:
        print(f'{last_message = }', f"\n{len(Current_data.data) = }")
        print('+ ' * 40)
    if len(last_message.tool_calls) > 0:

        old_data = bool(last_message.tool_calls[0]['args'].get('current_data', False))
        old_data = False
        if old_data and len(Current_data.data) > 0:
            return 'pandas'

        return "sql"

    return END




# ----- TOOLS

@tool("get_analysis")
def get_analysis(task: str, current_data: bool = False) -> str:
    """Get analysis from public economic commerce data. Gathering data from public database
and processing calculations and analysis needed to fulfill task. If you want to continue with current data pass current_data=True

   Args:
       task: A clear and detailed text description of the data or completed analysis you wish to receive.
       current_data: Proceed analysis on currently obtained data
    """
    return "None"


@tool("query_database")
def query_database(query: str):
    """Run SQL queries against a connected database, sending the query to the database server for processing.
Returns pandas Dataframe

    Args:
        query: Structured query language (SQL) to process information in a relational database.
    """
    query = query.replace("DATASET", "bigquery-public-data.thelook_ecommerce")
    if VERBOSE >0:
        print("- - - - query_database:", query)

    data = BQ_runner.execute_query(query)
    return data
def query_database_runner(query: str) -> pd.DataFrame:
    data = BQ_runner.execute_query(query)
    return data

@tool()
def python_code_executor(code: str) -> str:
    """executes Python code to perform complex calculations or interact with the 'df' pandas dataframe.
You will get output only from variable 'result', do not forget to add it in code.

    Args:
        code: python code to execute
    """
    try:
        variables = {"df": Current_data.data}
        exec(code, {}, variables)
        output = variables['result']
    except Exception as e:
        output = e
    return output


def get_content(message):
    content = message.content
    if isinstance(content, str):
        return content

    return content[0]['text']


