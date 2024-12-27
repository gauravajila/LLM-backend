# instructions.py

def get_query_instruction() -> str:
    return """
    Perform the following steps to address the given query:
    Step 1: Begin by verifying if the provided dataframe and instructions contain sufficient information for the required analysis. In case of insufficient details, respond with:
    ```json
    {
      "table": {},
      "message": ["Please review and modify the prompt with more specifics."]
    }
    ```
    Step 2: If the query requires creating a table and ensuring that the number of columns always matches the number of columns in the data rows, format your response using the following structure:    ```json
    {
      "table": {
        "columns": ["column1", "column2", ...],
        "data": [[value1, value2, ...], [value1, value2, ...], ...]
      },
      "message": []
    }
    ```
    Step 3: For queries requiring solely a textual response, utilize the following format:
    ```json
    {
      "table": {},
      "message": ["Your text response here"]
    }
    ```
    Step 4: Ensure consistent usage of standard decimal format without scientific notation. Replace any None/Null values with 0.0."
    Always Return output in json format from above step 1 to 3.
    Query: """
    

#iteration1: Till 7April Generate a JSON representation of charts based on the provided dataset. The objective is to craft visually clear and intuitive visualizations that effectively convey insights from the data. The resulting JSON structure should adhere to the format demonstrated in the example below:
    
def get_graph_instruction():
  return ''' 
Utilize exclusively the dataset's existing data to generate visually clear and intuitive visualizations. The objective is to effectively convey insights. Ensure that the resulting JSON structure adheres to the format demonstrated in the example below:
```json
{
  "charts": [
    {
      "chart_type": "bar",
      "data_format": {
        "labels": ["Label1", "Label2", ...],
        "categories": ["Category1", "Category2", ...],
        "values": [
          [Value11, Value12, ...],
          [Value21, Value22, ...],
          ...
        ],
        "isStacked": True/False
      },
      "insight": [
        "Insight1",
        "Insight2",
        ...
      ]
    },
    {
      "chart_type": "pie",
      "data_format": {
        "labels": ["Label1", "Label2", ...],
        "categories": ["Category1", "Category2", ...],
        "values": [Value1, Value2, ...],
        "isStacked": True/False
      },
      "insight": [
        "Insight1",
        "Insight2",
        ...
      ]
    },
    {
      "chart_type": "line",
      "data_format": {
        "labels": ["Label1", "Label2", ...],
        "categories": ["Category1", "Category2", ...],
        "values": [
          [Value11, Value12, ...],
          [Value21, Value22, ...],
          ...
        ],
        "isStacked": True/False
      },
      "insight": [
        "Insight1",
        "Insight2",
        ...
      ]
    }
  ]
}```
Here is the data:
'''

def get_planner_instruction(input_prompt):
  return f''' 
  Enhance the instructions by employing a Pandas DataFrame without providing specific code. 
  Remove the steps associated with importing libraries and loading data.
  Note: Kindly present the output in either text or tabular DataFrame format.
  User input prompt: {input_prompt} '''
  
def get_planner_instruction_with_data(input_prompt, data):
  return f''' 
  Enhance the instructions for using a Pandas DataFrame without including specific code.
  When revising the instructions, consider the following categories for column:  
  1. "Group" : ['MRI', 'Bio Chemistry', 'CT', 'Haematology', 'Others',
       'Micro Biology', 'X-Ray', 'Serology', 'USG', 'Pathology', 'Food',
       'ECG', 'Bio Medical', 'Room Charges', 'EEG', 'Others-OP',
       'Clinical Pathology', 'Surgery', 'Theraphy', 'EMR', 'Ambulance',
       'Tray', 'Consumables', 'BIPAP-Rent Income', 'C-Arm', 'Cath Lab',
       'Consultation', 'ECT', 'Admission', 'MRD', 'Oxygen', 'Consumbles',
       'Drugs', 'consultation', 'Lab']
  Exclude steps related to importing libraries and loading data. 
  User input prompt: {input_prompt} 
  Here is data: {data}'''
  
  
def get_ai_documentation_instruction():
    return '''
    Given the data, write column descriptions. Return output in this format:
    ```json
    {
      "configuration_details": "{\"Column_name\":\"Column Description\"}"
    }
    ```
    Here is the data:
    '''