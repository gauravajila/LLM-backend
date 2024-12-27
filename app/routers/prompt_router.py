# app/routers/prompt_router.py
import copy
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import List
from app.repositories.prompt_repository import PromptRepository, PromptResponseRepository
from app.models.prompt import Prompt, PromptCreate
from app.instructions import get_query_instruction, get_graph_instruction, get_planner_instruction, get_planner_instruction_with_data
from io import BytesIO
from fastapi.responses import JSONResponse

import os
import re
import pandas as pd
from datetime import datetime

#Pandas AI Implementation
from pandasai import SmartDatalake
from pandasai import Agent, SmartDataframe

from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_csv_agent, create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI, OpenAI

from types import FrameType
from loguru import logger


from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import pandas as pd
import numpy as np
import re
import json
from typing import Any, Dict, Union
from pydantic import BaseModel

import json
from datetime import datetime, date
from typing import Any
import pandas as pd
import numpy as np
from multiprocessing import Pool

router = APIRouter(prefix="/prompts", tags=["Prompts"])

prompt_repository = PromptRepository()
prompt_response_repository = PromptResponseRepository()

@router.post("/", response_model=Prompt)
def create_prompt_route(prompt_create: Prompt):
    new_prompt = prompt_repository.create_prompt(prompt_create)
    return new_prompt

@router.get("/boards/{board_id}", response_model=List[Prompt])
def get_prompts_for_board_route(board_id: int):
    prompts = prompt_repository.get_prompts_for_board(board_id)
    return prompts

@router.get("/{prompt_id}", response_model=Prompt)
def get_prompt_route(prompt_id: int):
    prompt = prompt_repository.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@router.put("/{prompt_id}", response_model=Prompt)
def update_prompt_route(prompt_id: int, prompt: Prompt):
    updated_prompt = prompt_repository.update_prompt(prompt_id, prompt)
    if not updated_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated_prompt

@router.delete("/{prompt_id}", response_model=Prompt)
def delete_prompt_route(prompt_id: int):
    deleted_prompt = prompt_repository.delete_prompt(prompt_id)
    if not deleted_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return deleted_prompt

@router.get("/{main_board_id}/{board_id}/prompts", response_model=List[Prompt])
async def get_prompts_for_board_in_main_board(main_board_id: int, board_id: int):
    prompts = prompt_repository.get_prompts_for_board_in_main_board(main_board_id, board_id)
    return prompts

@router.post("/run_prompt")
async def run_prompt(input_text: str, board_id: str, file: UploadFile):
    try:
        response_content = "Please review and modify the prompt with more specifics."
        start_time = datetime.now()

        # Read and process the uploaded file
        contents = await file.read()
        buffer = BytesIO(contents)
        df = pd.read_csv(buffer)
        buffer.close()
        file.file.close()

        # Generate hash key based on CSV file content and input text
        hash_key = prompt_response_repository.generate_hash_key(contents, input_text)

        # Check if the response is already present in the Prompt_response table
        existing_response = await prompt_response_repository.check_existing_response(hash_key)

        if existing_response:
            # If response is already present, return the existing response
            return JSONResponse(content=existing_response[3])

        llm = ChatOpenAI(temperature=0, model="gpt-4")

        # Initiate a LangChain's Pandas Agent with the LLM from Azure OpenAI Service to interact with the dataframe.
        agent = create_pandas_dataframe_agent(
            llm, df, 
            verbose=True, agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION, 
            handle_parsing_errors=True, number_of_head_rows=0
        )

        # Define the preinstruction for the query.
        instruction = get_query_instruction()

        prompt = instruction + input_text 
        response_content = agent.run(prompt)

        #Remove special character
        response_content = re.sub(r"```|python|json", "",response_content, 0, re.MULTILINE)
        
        response_content = eval(response_content)

        end_time = datetime.now()
        duration = end_time - start_time

        result = {
            "status_code": 200,
            "detail": "Prompt Run Successfully",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "board_id": board_id,
            "prompt_text":input_text,
            **response_content,
        }
        
        # Save the response to the Prompt_response table
        prompt_response_repository.save_response_to_database(hash_key, result)
        
        return JSONResponse(content=result)
    except Exception as e:
        # Handle exceptions and return an error response if needed
        print(e)
        return JSONResponse(content={"error": "Prompt Error","detail":response_content}, status_code=500)
    
def convert_table_to_dataframe(table):
    if "columns" in table and "data" in table:
        # Assuming that "columns" and "data" keys are present in the table
        columns = table["columns"]
        data = table["data"]

        # Create a Pandas DataFrame
        df = pd.DataFrame(data, columns=columns)

        return df
    else:
        # Handle the case where "columns" or "data" is missing
        print("Invalid table structure. Unable to convert to DataFrame.")
        return None
        
def create_csv_langchain_agent(input_text, data, llm):
        agent = create_pandas_dataframe_agent(
            llm, data, 
            verbose=True, 
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION, 
            handle_parsing_errors=True, 
            number_of_head_rows=0
        )

        # Define the preinstruction for the query.
        instruction = get_query_instruction()

        prompt = instruction + input_text 
        response_content = agent.run(prompt)

        #Remove special character
        response_content = re.sub(r"```|python|json", "",response_content, 0, re.MULTILINE)
        
        try:
            response_content = eval(response_content)
        except Exception as ex:
            # Format output as per our structure
            if isinstance(response_content, int):
                response_content = {"message": [str(response_content)], "table": {}}
        return response_content

def convert_timestamps_to_strings(df):
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')
    return df


class RePromptService:
    def __init__(self, prompt_repository: PromptRepository, llm_service: ChatOpenAI):
        self.prompt_repository = prompt_repository
        self.llm_service = llm_service

    @staticmethod
    def extract_text_between_double_quotes(text):
        #['sample', 'multiple', 'strings']
        pattern = r'"([^"]*)"'
        matches = re.findall(pattern, text)
        return matches
    
    

    def run_re_prompt(self, input_text: str, board_id: str):
        try:
            combined_contents, dataframes_list, table_name_list = self.prompt_repository.get_file_download_links_by_board_id(board_id)

            markdown_data = '\n'.join([df.head(5).to_markdown() for df in dataframes_list])
            input_text = get_planner_instruction_with_data(input_text, markdown_data)
            llm_output = self.llm_service.invoke(input_text)
            pattern = re.compile(r"[\s\S]*?Output:\s*.*", re.DOTALL)
            match = pattern.search(llm_output.content)
            
            if match:
                return match.group()
            
            return llm_output.content
        
        except Exception as e:
            # Handle exceptions and return appropriate HTTP error response
            raise HTTPException(status_code=500, detail=f"Error processing re-prompt: {str(e)}")


@router.post("/re_prompt")
async def run_re_prompt(input_text: str, board_id: str):
    re_prompt_service = RePromptService(prompt_repository, ChatOpenAI(temperature=0, model="gpt-3.5-turbo"))
    return re_prompt_service.run_re_prompt(input_text, board_id)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (pd.Timestamp, pd.Period)):
            return str(obj)
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def generate_chart_json(df):
    # Ensure the first column is the index (Row Labels)
    df.set_index(df.columns[0], inplace=True)
    # Labels for the charts (index of the DataFrame)
    labels = df.index.tolist()
    # Categories (columns of the DataFrame)
    categories = df.columns.tolist()
    # Values for the bar and line charts
    values = df.values.tolist()
    # Values for the pie chart (using the last column)
    pie_values = df.iloc[:, -1].tolist()

    # JSON structure
    chart_data = {
        "charts": [
            {
                "chart_type": "bar",
                "data_format": {
                    "labels": labels,
                    "categories": categories,
                    "values": values,
                    "isStacked": True
                },
                "insight": [
                    "Bar chart showing the distribution of values across different labels."
                ]
            },
            {
                "chart_type": "pie",
                "data_format": {
                    "labels": labels,
                    "categories": [categories[-1]],  # The last column is used for the pie chart
                    "values": pie_values,
                    "isStacked": False
                },
                "insight": [
                    "Pie chart showing the proportion of the last column values across different labels."
                ]
            },
            {
                "chart_type": "line",
                "data_format": {
                    "labels": labels,
                    "categories": categories,
                    "values": values,
                    "isStacked": False
                },
                "insight": [
                    "Line chart showing the trend of values across different labels."
                ]
            }
        ]
    }

    # Convert to JSON
    #json_output = json.dumps(chart_data, indent=4)
    
    return chart_data


class ResponseContent(BaseModel):
    message: list[str] = []
    table: Dict[str, Union[list, dict]] = {}


@router.post("/run_prompt_v1")
async def run_prompt_v1(input_text: str, board_id: str, use_cache: bool = True) -> JSONResponse:
    """
    Run the prompt v2 pipeline.

    Args:
        input_text (str): The input prompt text.
        board_id (str): The ID of the board for which the prompt is being run.
        use_cache (bool, optional): Whether to use cached responses or not. Defaults to True.

    Returns:
        JSONResponse: The response containing the result of the prompt run.
    """
    try:
        start_time = datetime.now()

        combined_contents, dataframes_list, table_name_list = prompt_repository.get_file_download_links_by_board_id(board_id)
        hash_key = prompt_response_repository.generate_hash_key(combined_contents, input_text)

        existing_response = await prompt_response_repository.check_existing_response(hash_key)
        if existing_response and use_cache:
            logger.info("Using the existing response")
            return JSONResponse(content=existing_response[3])

        llm = ChatOpenAI(temperature=0, model="gpt-4")
        agent = Agent(dataframes_list, config={"llm": llm, "verbose": True, "enable_cache": False, "max_retries": 10})
        rephrased_query = agent.rephrase_query(input_text)
        response_content = agent.chat(rephrased_query)

        response_content = handle_response_content(response_content, input_text, llm)
        graph_output_json = generate_graph_json(response_content, llm)

        end_time = datetime.now()
        duration = end_time - start_time

        result = {
            "status_code": 200,
            "detail": "Prompt Run Successfully",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "board_id": board_id,
            "prompt_text": input_text,
            **response_content.dict(),
            **graph_output_json
        }

        logger.info(f"Result: {result}")
        return JSONResponse(content=json.loads(json.dumps(result, cls=CustomJSONEncoder)))

    except Exception as e:
        logger.error(f"Error in run_prompt_v2: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def handle_response_content(response_content, input_text, llm):
    """
    Handle and format the response content based on the type of response.

    Args:
        response_content (Any): The response content returned by the agent.
        input_text (str): The input prompt text.
        llm (ChatOpenAI): The language model instance.

    Returns:
        ResponseContent: The formatted response content.
    """
    if isinstance(response_content, (int, float)):
        #To do convert this in sentence format
        return {"message":[str(response_content)]}

    elif any(pattern in response_content for pattern in ("Unfortunately", ".png", "No data available")):
        try:
            logger.info("Running Pandasai Agent 2nd time with Planner")
            input_text = get_planner_instruction(input_text)
            rephrased_query = llm.rephrase_query(input_text)
            response_content = llm.chat(rephrased_query)
            return handle_response_content(response_content, input_text, llm)
        except Exception as ex:
            logger.error(f"2nd Time After planning also : {ex}")
            return {"message":["Please review and modify the prompt with more specifics."]}

    elif isinstance(response_content, pd.DataFrame):
        response_content = response_content.fillna(0).round(2)
        ou = SmartDataframe(response_content, config={"llm": llm, "verbose": True, "enable_cache": False, "max_retries": 10})
        response_content = ou.chat('''Sort the data on date column. After this format the date column as %b-%Y format''')
        response_content = convert_timestamps_to_strings(response_content)
        response_content = {
            "message": [],
            "table": {
                "columns": response_content.columns.tolist(),
                "data": response_content.values.tolist()
            }
        }
    else:
        return {"message":[str(response_content)]}


def generate_graph_json(response_content: ResponseContent, llm) -> dict:
    """
    Generate the graph JSON output from the response content.

    Args:
        response_content (ResponseContent): The formatted response content.
        llm (ChatOpenAI): The language model instance.

    Returns:
        dict: The graph JSON output.
    """
    try:
        if "columns" in response_content["table"] and len(response_content["table"]['data']):
            llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            graph_df = convert_table_to_dataframe(response_content["table"])
            graph_instruction = get_graph_instruction()
            graph_output = llm.invoke(graph_instruction + graph_df.to_markdown())
            graph_output = re.sub(r'\bfalse\b', 'False', re.sub(r'\btrue\b', 'True', graph_output.content, flags=re.IGNORECASE), flags=re.IGNORECASE)
            graph_output = re.sub(r"```|python|json", "", graph_output, 0, re.MULTILINE)
            graph_output_json = eval(graph_output)
            logger.info("Graph Generation Success")
            return graph_output_json
    except Exception as ex:
        logger.error(f"Graph generation failed: {ex}")
        return {}

class DataFrameProcessor:
    def __init__(self, llm_model: str) -> None:
        self.llm = ChatOpenAI(temperature=0, model=llm_model)

    @staticmethod
    def convert_timestamps_to_strings(df: pd.DataFrame) -> pd.DataFrame:
        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')
        return df

    def sort_and_format_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        ou = SmartDataframe(df, config={"llm": self.llm, "verbose": True, "enable_cache": False, "max_retries": 10})
        sorted_df = ou.chat('Please review the data.If there is any date column, then Sort the data by the date column and format the dates as %B-%Y.')
        return self.convert_timestamps_to_strings(sorted_df)

    def process_dataframe_response(self, response_content: pd.DataFrame) -> Dict[str, Union[str, Dict]]:
        response_content = response_content.fillna(0).round(2)
        response_content = self.sort_and_format_dates(response_content)
        return {
            "message": [],
            "table": {
                "columns": response_content.columns.tolist(),
                "data": response_content.values.tolist()
            }
        }

    def process_dataframe_add_prefix(self, response_content) -> Dict[str, Union[str, Dict]]:
        response_content = convert_table_to_dataframe(response_content["table"])
        ou = SmartDataframe(response_content, config={"llm": self.llm, "verbose": True, "enable_cache": False, "max_retries": 10})
        response_content = ou.chat('Please review the data. If there is a currency column, add the rupee symbol. If other symbols are needed for dimensions, include those as well.')
        return {
            "message": [],
            "table": {
                "columns": response_content.columns.tolist(),
                "data": response_content.values.tolist()
            }
        }

class PromptHandler:
    def __init__(self, llm_model: str):
        self.llm = ChatOpenAI(temperature=0, model=llm_model)
        self.dataframe_processor = DataFrameProcessor(llm_model=llm_model)

    def run(self, input_text: str, dataframes_list: List[pd.DataFrame]) -> Dict[str, Any]:
        agent = Agent(dataframes_list, config={"llm": self.llm, "verbose": True, "enable_cache": False, "max_retries": 10})
        rephrased_query = agent.rephrase_query(input_text)
        response_content = agent.chat(rephrased_query)
        return self.handle_response_content(agent, response_content, input_text)

    def handle_response_content(self, agent, response_content, input_text: str) -> Dict[str, Union[str, Dict]]:
        if isinstance(response_content, (int, float)):
            response_content = {"message": [str(response_content)], "table": {}}
        elif any(phrase in response_content for phrase in ["Unfortunately", ".png", "No data available for the given conditions"]):
            input_text = get_planner_instruction(input_text)
            rephrased_query = agent.rephrase_query(input_text)
            response_content = agent.chat(rephrased_query)
            if isinstance(response_content, (int, float)):
                response_content = {"message": [str(response_content)], "table": {}}
            elif isinstance(response_content, pd.DataFrame):
                response_content = self.dataframe_processor.process_dataframe_response(response_content)
            else:
                response_content = {"message": [str(response_content)], "table": {}}
        else:
            if isinstance(response_content, pd.DataFrame):
                response_content = self.dataframe_processor.process_dataframe_response(response_content)
            else:
                response_content = {"message": [str(response_content)], "table": {}}
        return response_content

class GenerateInsightRecommendationOptimization:
    def __init__(self, llm_model: str):
        self.llm = ChatOpenAI(temperature=0, model=llm_model)
        self.question_instruction = '''Based on the provided data, generate questions related to insights, recommendations, and optimization. Return the questions as a Python list. Here is the data: '''
        
    def generate_questions(self, response_content: Dict[str, Any]) -> Dict[str, Any]:
        questions_list = list()
        try:
            output = convert_table_to_dataframe(response_content["table"])
            questions_list = self.llm.invoke(self.question_instruction + output.head(2).to_markdown())
            questions_list = re.sub(r"```|python|json", "", questions_list, 0, re.MULTILINE)
            questions_list = eval(questions_list)
        except Exception as ex:
            logger.error(f"Graph generation failed: {str(ex)}")
        return questions_list
    
    def answer_questions(self, question_list: list[str, Any], response_content: Dict[str, Any]) -> Dict[str, Any]:
        answer_dict = dict()
        output = convert_table_to_dataframe(response_content["table"])
        agent = Agent(output, config={"llm": self.llm, "verbose": True, "enable_cache": False, "max_retries": 10})
        for query in question_list:
            try:
                response_content = agent.chat(query)
                answer_dict[query] = response_content
            except Exception as ex:
                logger.error(f"GenerateInsightRecommendationOptimization failed: {str(ex)}")
                continue
        return answer_dict
        
        
class GraphGenerator:
    def __init__(self, llm_model: str):
        self.llm = ChatOpenAI(temperature=0, model=llm_model)

    async def generate_graphs(self, response_content: Dict[str, Any]) -> Dict[str, Any]:
        try:
            graph_df = convert_table_to_dataframe(response_content["table"])
            graph_instruction = get_graph_instruction()
            graph_output = self.llm.invoke(graph_instruction + graph_df.to_markdown())
            graph_output = re.sub(r'\bfalse\b', 'False', re.sub(r'\btrue\b', 'True', graph_output.content, flags=re.IGNORECASE), flags=re.IGNORECASE)
            graph_output = re.sub(r"```|python|json", "", graph_output, 0, re.MULTILINE)
            graph_output_json = eval(graph_output)
            return graph_output_json
        except Exception as ex:
            logger.error(f"Graph generation failed: {str(ex)}")
            return {}

class PromptFacade:
    def __init__(self):
        self.prompt_handler = PromptHandler(llm_model="gpt-4o")
        self.graph_generator = GraphGenerator(llm_model="gpt-4o")
        self.dataframe_processor = DataFrameProcessor(llm_model="gpt-4o")
        self.generate_insights = GenerateInsightRecommendationOptimization(llm_model="gpt-4o")

    async def handle_prompt(self, input_text: str, board_id: str, user_name:str, use_cache: bool) -> Dict[str, Any]:
        '''
        Author: Shashi Raj
        Date: 09-06-2024
        
        To do: 
        We need to write a logic to identify the dataframe.
        If there are multiple dataframe.
        
        '''
        start_time = datetime.now()

        combined_contents, dataframes_list, table_name_list = prompt_repository.get_file_download_links_by_board_id(board_id)
        hash_key = prompt_response_repository.generate_hash_key(combined_contents, input_text)
        existing_response = await prompt_response_repository.check_existing_response(hash_key)

        if existing_response and use_cache:
            return existing_response[3]

        response_content = self.prompt_handler.run(input_text, dataframes_list)

        if "columns" in response_content["table"] and len(response_content["table"]['data']):
            graph_output_json = await self.graph_generator.generate_graphs(response_content)
            #response_content = self.dataframe_processor.process_dataframe_add_prefix(response_content)
            #generate_questions = self.generate_insights.generate_questions(response_content)
            #insights_dict = self.generate_insights.answer_questions(generate_questions, response_content)
        else:
            graph_output_json = {}

        end_time = datetime.now() 
        result = self.create_response(start_time, end_time, board_id, input_text, response_content, graph_output_json)
        # Save the response to the Prompt_response table
        result["user_name"] = user_name
        await prompt_response_repository.save_response_to_database(hash_key, result)
        
        return result

    def create_response(self, start_time: datetime, end_time: datetime, board_id: str, input_text: str, 
                        response_content: Dict[str, Any], graph_output_json: Dict[str, Any]) -> Dict[str, Any]:  
        duration = end_time - start_time
        result = {
            "status_code": 200,
            "detail": "Prompt Run Successfully",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "board_id": board_id,
            "prompt_text": input_text,
            **response_content,
            **graph_output_json
        }
        
        return result

@router.post("/run_prompt_v2")
async def run_prompt_v2(input_text: str, board_id: str, user_name:str = '', use_cache: bool = True):
    """
    API endpoint to run prompt, validate, generate graphs, and extract insights.
    """
    try:
        facade = PromptFacade()
        result = await facade.handle_prompt(input_text, board_id, user_name, use_cache)
        return JSONResponse(content=json.loads(json.dumps(result, cls=CustomJSONEncoder)))
    except Exception as e:
        logger.error(f"Error in run_prompt_v2: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")