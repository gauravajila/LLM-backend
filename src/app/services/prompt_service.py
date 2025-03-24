# app/services/prompt_service.py
import io
import re
import json
from typing import Dict, Any, Union, List, Tuple
import requests
import pandas as pd
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_csv_agent, create_pandas_dataframe_agent

from app.repositories.prompt_repository import PromptRepository, PromptResponseRepository
from app.repositories.data_management_table_repository import DataManagementTableRepository  # Import
from app.instructions import get_query_instruction, get_graph_instruction, get_planner_instruction, get_planner_instruction_with_data
from app.utils import CustomJSONEncoder  # Assuming you have this utility class
from pandasai import SmartDatalake, Agent, SmartDataframe
from fastapi import UploadFile
import requests  # For making API calls


class PromptService:
    def __init__(self, prompt_repository: PromptRepository, prompt_response_repository: PromptResponseRepository, data_management_table_repository: DataManagementTableRepository):  # Add repository
        self.prompt_repository = prompt_repository
        self.prompt_response_repository = prompt_response_repository
        self.data_management_table_repository = data_management_table_repository  # Initialize
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")  # Initialize LLM here
        self.dataframe_processor = DataFrameProcessor(self.llm)

    async def run_prompt_pipeline(self, input_text: str, board_id: int, data_table_id: int) -> Dict[str, Any]:
        """Runs the entire prompt processing pipeline, fetching data from the API."""
        try:
            # 1. Fetch file information from the API
            api_url = f"http://143.110.180.27:8003/docs#/Data%20Management%20Tables/get_all_data_management_tables_main_boards_boards_data_management_table_get_all_tables_with_files_get"  # Replace with your API URL
            response = requests.get(api_url)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            table_data = response.json()[0]  # Get the first element of the list, as per your API design

            if not table_data or not table_data.get("files"):
                raise ValueError("No files found for the given data table ID.")

            dataframes = []
            combined_contents = io.BytesIO()

            for file_info in table_data["files"]:
                file_download_link = file_info["file_download_link"]
                table_name = table_data["table_name"]  # Get the table name from the API response
                try:
                    # 2. Download files from MinIO (same as before)
                    object_name = '/'.join(file_download_link.split('/')[-2:])
                    data = self.data_management_table_repository.minio_client.get_object(
                        self.data_management_table_repository.bucket_name, object_name
                    )
                    file_content = data.read()

                    combined_contents.write(file_content)
                    combined_contents.write(b'\n')  # Add a newline separator between files

                    df = pd.read_csv(io.BytesIO(file_content))  # Assumes CSV. Adjust as needed.
                    dataframes.append(df)

                except Exception as e:
                    logger.error(f"Error downloading or processing file: {e}")
                    # Handle error as appropriate (e.g., skip the file, raise exception)

            combined_contents.seek(0)
            combined_contents_bytes = combined_contents.getvalue()

            if not dataframes:
                raise ValueError("No dataframes could be created from the provided files.")

            df = pd.concat(dataframes, ignore_index=True)

            hash_key = self.prompt_response_repository.generate_hash_key(combined_contents_bytes, input_text)
            existing_response = await self.prompt_response_repository.check_existing_response(hash_key)
            if existing_response:
                return existing_response.prompt_out

            agent = create_pandas_dataframe_agent(
                self.llm, df,  # Use the initialized LLM
                verbose=True, agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                handle_parsing_errors=True, number_of_head_rows=0
            )

            instruction = get_query_instruction()
            prompt = instruction + input_text
            response_content_str = agent.run(prompt)

            response_content_str = re.sub(r"```|python|json", "", response_content_str, 0, re.MULTILINE)

            try:
                response_content = eval(response_content_str)  # Try to evaluate the string
            except (SyntaxError, NameError, TypeError) as e:
                logger.error(f"Eval error: {e}. Output string: {response_content_str}")
                response_content = {"message": [response_content_str]}  # Treat as message

            response_content = self.dataframe_processor.process_dataframe_response(response_content, input_text)
            graph_output_json = self.dataframe_processor.generate_chart_json(response_content)

            # Combine response_content and graph_output_json into a single dictionary
            final_output = {**response_content, **graph_output_json}

            # No need for PromptOutput model here - save the dictionary directly
            await self.prompt_response_repository.save_response_to_database(hash_key, final_output)
            return final_output

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling data management API: {e}")
            raise  # Re-raise the exception to be handled by the caller
        except Exception as e:
            logger.exception(f"Error in prompt pipeline: {e}")
            raise


class DataFrameProcessor:  # This class remains unchanged from your previous versions
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    @staticmethod
    def convert_timestamps_to_strings(df: pd.DataFrame) -> pd.DataFrame:
        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')
        return df

    def sort_and_format_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            ou = SmartDataframe(df, config={"llm": self.llm, "verbose": True, "enable_cache": False, "max_retries": 10})
            sorted_df = ou.chat('Please review the data. If there is any date column, then Sort the data by the date column and format the dates as %B-%Y.')
            return self.convert_timestamps_to_strings(sorted_df)
        except Exception as e:
            logger.exception(f"Error in sort_and_format_dates: {e}")
            return df  

    def process_dataframe_response(self, response_content: Any, input_text: str) -> Dict[str, Any]:
        """Handles and formats the LLM response, including DataFrame processing."""

        if isinstance(response_content, (int, float)):
            return {"message": [str(response_content)]}

        elif any(pattern in str(response_content).lower() for pattern in ("unfortunately", ".png", "no data available")):  # Convert to string for checking
            try:
                logger.info("Running Pandasai Agent 2nd time with Planner")
                input_text = get_planner_instruction(input_text)
                rephrased_query = self.llm.rephrase_query(input_text)
                response_content = self.llm.chat(rephrased_query)

                return self.process_dataframe_response(response_content, input_text)  # Recursive call
            except Exception as ex:
                logger.error(f"2nd Time After planning also : {ex}")
                return {"message": ["Please review and modify the prompt with more specifics."]}

        elif isinstance(response_content, pd.DataFrame):
            response_content = response_content.fillna(0).round(2)
            response_content = self.sort_and_format_dates(response_content)  # Sort and format dates

            return {
                "message": [],
                "table": {
                    "columns": response_content.columns.tolist(),
                    "data": response_content.values.tolist()
                }
            }
        else:
            return {"message": [str(response_content)]}

    def generate_chart_json(self, response_content: Dict[str, Any]) -> dict:
        try:
            if "table" in response_content and "columns" in response_content["table"] and len(response_content["table"]['data']):
                graph_df = pd.DataFrame(response_content["table"]["data"], columns=response_content["table"]["columns"])
                graph_instruction = get_graph_instruction()
                graph_output = self.llm.invoke(graph_instruction + graph_df.to_markdown())
                graph_output = re.sub(r'\bfalse\b', 'False', re.sub(r'\btrue\b', 'True', graph_output.content, flags=re.IGNORECASE), flags=re.IGNORECASE)
                graph_output = re.sub(r"```|python|json", "", graph_output, 0, re.MULTILINE)
                graph_output_json = eval(graph_output)
                logger.info("Graph Generation Success")
                return graph_output_json
            else:
                return {}  # Return empty dict if no table data
        except Exception as ex:
            logger.error(f"Graph generation failed: {ex}")
            return {}