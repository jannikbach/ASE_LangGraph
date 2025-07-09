import os
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict, Literal
from tools import read_tools, read_write_tools
from typing import Annotated
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv()
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def run_agents(index, problem_statement, name, url, key):

    def planner_prompt(index, problem_statement, name):
        return f"""You are the Planner in a team of agents working collaboratively to fix a software issue. Your job is to analyze the provided problem description and create an actionable, step-by-step blueprint for the Coder to implement.

                - Use the available file inspection tools to read and understand the relevant source files in `repo_{index}/{name}` before planning.
                - Use the list_files_in_repository tool only once!
                - Identify the root cause of the test failures or bug described below.
                - For each coding task, specify:
                  1. The objective of the change.
                  2. The exact file path(s) to modify.
                  3. The tool calls or commands needed to inspect or open those files.
                  4. The precise edits or additions (e.g., function names, lines to insert or update).
                - Ensure changes are minimal and scoped only to what is necessary.
                - Call the appropriate file-reading tool whenever you refer to a file, e.g., `read_file("path/to/file")`.
                - List any edge cases or test scenarios that must be covered.
                - Use the 'list_files_in_repository' tool only once!
                
                Your output should be a numbered list of instructions the Coder can follow in sequence.
                
                Problem description:
                {problem_statement}
                
                USE THE 'list_files_in_repository' TOOL ONLY ONCE!!!!
                """


    def coder_prompt(index, problem_statement, name, planner_result):

        return f"""You are the Coder in a team of agents working collaboratively to fix a software issue. Your role is to implement the code changes based on the plan provided by the Planner. 
        
        You are working in the Git repository directory: `repo_{index}/{name}`.
        
        When using the tools always use the 'repo=repo_{index}/{name}' flag to specify the repository.


        **Task:**
        Your job is to:
        - Modify only the necessary files by using the tools that are provided to you.
        - Ensure all changes are minimal and scoped to what is strictly required to resolve the failing tests.
        - Save all changes to the appropriate files so that they appear in the `git diff`.
        - Follow good coding practices and maintain consistency with the surrounding code.

        **Additional Rules:**
        - NEVER Execute two tools at once. Always in Sequence
        - Use the tools provided to you to inspect the files and understand the code.
        - Use the 'list_files_in_repository' tool only once!
        - Use the 'find_and_replace' tool to update the files

        Do not make unrelated changes or refactor parts of the code not involved in this fix. Once changes are made, hand off the task to the Tester for validation.

        Problem description:
        {problem_statement}
        
        Planner Instrucitons:
        {planner_result}
        
        USE THE 'list_files_in_repository' TOOL ONLY ONCE!!!!
        """


    # Initialize the LLM with read tools
    llm_read = ChatOpenAI(model="gpt-4o-mini",api_key=OPENAI_API_KEY)
    llm_with_read_tools = llm_read.bind_tools(read_tools)

    # Initialize the LLM with read/write tools
    llm_read_write = ChatOpenAI(model="gpt-4o-mini",api_key=OPENAI_API_KEY)
    llm_with_read_write_tools = llm_read_write.bind_tools(read_write_tools)

    # Graph state
    class State(TypedDict):
        # messages: Annotated[list, add_messages]
        planner_messages: Annotated[list, add_messages]
        coder_messages: Annotated[list, add_messages]
        index: str
        problem_statement: str
        planner_result: str
        coder_result: str
        tester_result: str

    # Nodes
    def planner(state: State) -> Command[Literal["tool_node_planner", "coder"]]:

        print(f"Planner working...")
        msg = llm_with_read_tools.invoke(state["planner_messages"])
        print(f"Planner recieved message")

        # record assistant response
        # state["messages"].append(msg)
        state["planner_messages"].append(msg)

        # if message is tool call command to go to tool
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("planner_messages", []):
            ai_message = messages[-1]
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return Command(
                goto="tool_node_planner",
            )
        else:
            # if message is no tool command to go to coder
            # append coder message and go to coder

            coder = coder_prompt(index, problem_statement, name, msg.content)
            print(f"Coder Prompt: {coder}")
            return Command(
                update={
                    "planner_result": msg.content,
                    "coder_messages": [HumanMessage(content=coder)],
                    # "messages": state["messages"] +
                    #             [HumanMessage(content=coder_prompt(index, problem_statement, name, msg.content))]
                                },
                goto="coder",
            )

    tool_node_planner = ToolNode(tools=read_tools, messages_key="planner_messages")
    tool_node_coder = ToolNode(tools=read_write_tools, messages_key="coder_messages")

    def coder(state: State) -> Command[Literal["tool_node_coder", END]]:
        print(f"Coder working...")
        msg = llm_with_read_write_tools.invoke(state["coder_messages"])
        print(f"Coder recieved message")
        # state["messages"].append(msg)
        state["coder_messages"].append(msg)

        # if message is tool call command to go to tool
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("coder_messages", []):
            ai_message = messages[-1]
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return Command(
                goto="tool_node_coder",
            )

        # if message is no tool command to go to end
        print(f"Coder result: {msg.content}")
        return Command(
            update={"coder_result": msg.content},
            goto=END,
        )



    graph_builder = StateGraph(State)

    graph_builder.add_node("planner", planner)
    graph_builder.add_node("coder", coder)
    # graph_builder.add_node("tester", tester)
    graph_builder.add_node("tool_node_planner", tool_node_planner)
    graph_builder.add_node("tool_node_coder", tool_node_coder)


    # Any time a tool is called, we return to the chatbot to decide the next step
    graph_builder.add_edge(START, "planner")


    graph_builder.add_edge("tool_node_planner", "planner")
    graph_builder.add_edge("tool_node_coder", "coder")


    # Compile
    graph = graph_builder.compile()

    # Invoke
    state = graph.invoke({"index": index,
                          "problem_statement": problem_statement,
                          "planner_messages": [HumanMessage(content=planner_prompt(index, problem_statement, name))],
                          # "messages": [HumanMessage(content=planner_prompt(index, problem_statement, name))]
                          },
                         {"recursion_limit": 100})
