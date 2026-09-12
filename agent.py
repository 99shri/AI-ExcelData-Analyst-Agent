import json
import os
import re

from dotenv import load_dotenv
from google import genai

from data_tools import ExcelAnalyzer


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set. "
        "Please add GEMINI_API_KEY to your .env file."
    )

client = genai.Client(api_key=API_KEY)

# Current Gemini Interactions API model
MODEL = "gemini-3.8-flash"

# Active dataset
analyzer = None


# =========================================================
# DATASET SETUP
# =========================================================

def set_analyzer(new_analyzer):
    """
    Set the active ExcelAnalyzer.
    """
    global analyzer
    analyzer = new_analyzer


# =========================================================
# BASIC DATASET FUNCTIONS
# =========================================================

def dataset_summary():
    """
    Return basic information about the dataset.
    """

    if analyzer is None:
        return "No dataset uploaded."

    try:
        df = analyzer.df

        return {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "column_names": list(df.columns),
        }

    except Exception as e:
        return f"Error getting dataset summary: {str(e)}"


def calculate_column(column, operation):
    """
    Perform calculation on a numeric column.
    """

    if analyzer is None:
        return "No dataset uploaded."

    if column not in analyzer.df.columns:
        return f"Column '{column}' not found."

    try:
        series = analyzer.df[column]

        numeric_series = series
        if not hasattr(series, "mean"):
            return f"Column '{column}' cannot be calculated."

        if operation == "sum":
            return float(numeric_series.sum())

        elif operation == "average":
            return float(numeric_series.mean())

        elif operation == "minimum":
            return float(numeric_series.min())

        elif operation == "maximum":
            return float(numeric_series.max())

        else:
            return (
                "Unsupported operation. "
                "Use sum, average, minimum, or maximum."
            )

    except Exception as e:
        return f"Error calculating column: {str(e)}"


def get_top_values(column, n=5):
    """
    Return most common values in a column.
    """

    if analyzer is None:
        return "No dataset uploaded."

    if column not in analyzer.df.columns:
        return f"Column '{column}' not found."

    try:
        n = int(n)

        result = (
            analyzer.df[column]
            .astype(str)
            .str.strip()
            .value_counts()
            .head(n)
        )

        return result.to_dict()

    except Exception as e:
        return f"Error getting top values: {str(e)}"


def filter_data(column, value):
    """
    Filter rows where column matches value.
    """

    if analyzer is None:
        return "No dataset uploaded."

    if column not in analyzer.df.columns:
        return f"Column '{column}' not found."

    try:

        mask = (
            analyzer.df[column]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            str(value).strip().casefold()
        )

        result = analyzer.df[mask]

        return result.to_dict(orient="records")

    except Exception as e:
        return f"Error filtering data: {str(e)}"


def count_filtered_data(column, value):
    """
    Count rows where a column matches a value.
    """

    if analyzer is None:
        return "No dataset uploaded."

    if column not in analyzer.df.columns:
        return f"Column '{column}' not found."

    try:

        mask = (
            analyzer.df[column]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            str(value).strip().casefold()
        )

        return int(mask.sum())

    except Exception as e:
        return f"Error counting data: {str(e)}"


# =========================================================
# VEHICLE MAPPING
# =========================================================

VEHICLE_MAPPING = {
    "truck": "Truck",
    "trucks": "Truck",

    "bus": "Bus",
    "buses": "Bus",

    "cycle": "Cycle",
    "cycles": "Cycle",

    "car": "Car",
    "cars": "Car",

    "motorcycle": "Motorcycle",
    "motorcycles": "Motorcycle",

    "bike": "Motorcycle",
    "bikes": "Motorcycle",

    "pedestrian": "Pedestrian",
    "pedestrians": "Pedestrian",
}


# =========================================================
# FIND COLUMN SAFELY
# =========================================================

def find_column(possible_names):
    """
    Find a column using case-insensitive matching.
    """

    if analyzer is None:
        return None

    columns = list(analyzer.df.columns)

    normalized = {
        str(col).strip().casefold(): col
        for col in columns
    }

    for name in possible_names:

        key = str(name).strip().casefold()

        if key in normalized:
            return normalized[key]

    return None


# =========================================================
# DIRECT ROW COUNT
# =========================================================

def handle_row_count_question(question):
    """
    Directly answer questions about total number of rows.
    """

    if analyzer is None:
        return None

    q = question.lower().strip()

    patterns = [
        "how many rows",
        "number of rows",
        "total rows",
        "how many records",
        "number of records",
        "total records",
        "how many accidents",
        "number of accidents",
        "total accidents",
        "total number of accidents",
    ]

    if any(pattern in q for pattern in patterns):

        # Avoid treating state-specific questions here.
        if " in " not in q and " for " not in q:
            return (
                f"There are {len(analyzer.df)} "
                f"records in the dataset."
            )

    return None


# =========================================================
# DETECT VEHICLE
# =========================================================

def detect_vehicle(question):
    """
    Detect a vehicle mentioned in a question.
    """

    q = question.lower()

    for keyword, vehicle in VEHICLE_MAPPING.items():

        if re.search(
            rf"\b{re.escape(keyword)}\b",
            q
        ):
            return vehicle

    return None


# =========================================================
# SIMPLE VEHICLE COUNT
# =========================================================

def handle_vehicle_count_question(question):
    """
    Answer questions such as:

    How many trucks?
    Accident by truck
    How many accidents involve buses?
    """

    if analyzer is None:
        return None

    q = question.lower()

    count_words = [
        "how many",
        "number of",
        "count",
        "total",
        "accident by",
        "accidents by",
        "accident involving",
        "accidents involving",
        "vehicle count",
    ]

    if not any(word in q for word in count_words):
        return None

    vehicle = detect_vehicle(question)

    if vehicle is None:
        return None

    vehicle_column = find_column([
        "Vehicle Type Involved"
    ])

    if vehicle_column is None:
        return (
            "The dataset does not contain "
            "'Vehicle Type Involved'."
        )

    count = count_filtered_data(
        vehicle_column,
        vehicle
    )

    if isinstance(count, int):

        return (
            f"The total count of accidents involving "
            f"a {vehicle} is {count}."
        )

    return str(count)


# =========================================================
# STATE + VEHICLE MOST INVOLVED
# =========================================================

def handle_state_vehicle_question(question):
    """
    Answer questions such as:

    While in Sikkim which vehicle is most involved in accident?
    Which vehicle is most involved in Sikkim?
    In Sikkim which vehicle has the highest accidents?
    """

    if analyzer is None:
        return None

    q = question.lower().strip()

    # Words indicating a "most involved" question
    most_words = [
        "most involved",
        "most common",
        "highest",
        "maximum",
        "most accidents",
        "maximum accidents",
        "highest accidents",
    ]

    if not any(word in q for word in most_words):
        return None

    # Find State Name column
    state_column = find_column([
        "State Name",
        "State"
    ])

    # Find vehicle column
    vehicle_column = find_column([
        "Vehicle Type Involved"
    ])

    if state_column is None:
        return (
            "The dataset does not contain "
            "'State Name'."
        )

    if vehicle_column is None:
        return (
            "The dataset does not contain "
            "'Vehicle Type Involved'."
        )

    # -----------------------------------------------------
    # Detect state from the actual dataset
    # -----------------------------------------------------

    states = (
        analyzer.df[state_column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    state_lookup = {
        state.casefold(): state
        for state in states.unique()
    }

    selected_state = None

    for state_key, actual_state in state_lookup.items():

        if re.search(
            rf"\b{re.escape(state_key)}\b",
            q
        ):
            selected_state = actual_state
            break

    if selected_state is None:
        return None

    # -----------------------------------------------------
    # Filter state
    # -----------------------------------------------------

    state_mask = (
        analyzer.df[state_column]
        .astype(str)
        .str.strip()
        .str.casefold()
        ==
        selected_state.strip().casefold()
    )

    state_df = analyzer.df[state_mask]

    if state_df.empty:
        return (
            f"No accident records were found "
            f"for {selected_state}."
        )

    # -----------------------------------------------------
    # Count vehicle involvement
    # -----------------------------------------------------

    vehicle_counts = (
        state_df[vehicle_column]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
    )

    if vehicle_counts.empty:
        return (
            f"No vehicle information was found "
            f"for {selected_state}."
        )

    most_vehicle = vehicle_counts.index[0]
    most_count = int(vehicle_counts.iloc[0])

    # Check for ties
    highest_count = vehicle_counts.max()

    tied_vehicles = [
        str(vehicle)
        for vehicle, count in vehicle_counts.items()
        if count == highest_count
    ]

    if len(tied_vehicles) > 1:

        vehicles_text = ", ".join(tied_vehicles)

        return (
            f"In {selected_state}, the vehicles most "
            f"involved in accidents are {vehicles_text}, "
            f"with {int(highest_count)} accidents each."
        )

    return (
        f"In {selected_state}, the vehicle most involved "
        f"in accidents is {most_vehicle}, with "
        f"{most_count} accidents."
    )


# =========================================================
# STATE ACCIDENT COUNT
# =========================================================

def handle_state_count_question(question):
    """
    Answer:

    How many accidents happened in Sikkim?
    Number of accidents in Maharashtra?
    """

    if analyzer is None:
        return None

    q = question.lower().strip()

    state_column = find_column([
        "State Name",
        "State"
    ])

    if state_column is None:
        return None

    count_words = [
        "how many",
        "number of",
        "count",
        "total",
    ]

    if not any(word in q for word in count_words):
        return None

    # Avoid handling vehicle questions here
    if detect_vehicle(question) is not None:
        return None

    states = (
        analyzer.df[state_column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    state_lookup = {
        state.casefold(): state
        for state in states.unique()
    }

    selected_state = None

    for state_key, actual_state in state_lookup.items():

        if re.search(
            rf"\b{re.escape(state_key)}\b",
            q
        ):
            selected_state = actual_state
            break

    if selected_state is None:
        return None

    count = int(
        (
            analyzer.df[state_column]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            selected_state.casefold()
        ).sum()
    )

    return (
        f"There are {count} accident records "
        f"in {selected_state}."
    )


# =========================================================
# GEMINI TOOL DEFINITIONS
# =========================================================

tools = [
    {
        "type": "function",
        "name": "dataset_summary",
        "description": (
            "Get the number of rows, columns and "
            "column names in the uploaded dataset."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },

    {
        "type": "function",
        "name": "calculate_column",
        "description": (
            "Calculate sum, average, minimum or maximum "
            "for a numeric column."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string"
                },
                "operation": {
                    "type": "string",
                    "enum": [
                        "sum",
                        "average",
                        "minimum",
                        "maximum"
                    ]
                },
            },
            "required": [
                "column",
                "operation"
            ],
        },
    },

    {
        "type": "function",
        "name": "get_top_values",
        "description": (
            "Find the most common values in a column."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string"
                },
                "n": {
                    "type": "integer"
                },
            },
            "required": [
                "column"
            ],
        },
    },

    {
        "type": "function",
        "name": "filter_data",
        "description": (
            "Filter rows where a column equals a value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string"
                },
                "value": {
                    "type": "string"
                },
            },
            "required": [
                "column",
                "value"
            ],
        },
    },

    {
        "type": "function",
        "name": "count_filtered_data",
        "description": (
            "Count rows where a column equals a value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string"
                },
                "value": {
                    "type": "string"
                },
            },
            "required": [
                "column",
                "value"
            ],
        },
    },
]


available_functions = {
    "dataset_summary": dataset_summary,
    "calculate_column": calculate_column,
    "get_top_values": get_top_values,
    "filter_data": filter_data,
    "count_filtered_data": count_filtered_data,
}


# =========================================================
# GEMINI INSTRUCTIONS
# =========================================================

SYSTEM_INSTRUCTIONS = """
You are an AI Excel Data Analyst.

Analyze the uploaded dataset.

IMPORTANT:
- Never invent numerical values.
- Never guess counts.
- Use the provided tools for numerical calculations.
- Use exact column names from the dataset.
- The vehicle column is "Vehicle Type Involved".
- The state column is "State Name".
- If the user asks which vehicle is most involved in a state,
  compare the actual vehicle counts for that state.
- Give concise answers.
"""


# =========================================================
# GEMINI AGENT
# =========================================================

def ask_gemini(question):
    """
    Handle questions that are not handled directly by Pandas.
    """

    prompt = (
        SYSTEM_INSTRUCTIONS
        + "\n\nUser question:\n"
        + question
    )

    try:

        interaction = client.interactions.create(
            model=MODEL,
            input=prompt,
            tools=tools,
        )

        while True:

            function_results = []

            for step in interaction.steps:

                if step.type == "function_call":

                    function_name = step.name
                    arguments = step.arguments

                    if function_name not in available_functions:
                        continue

                    function = available_functions[
                        function_name
                    ]

                    try:

                        result = function(
                            **arguments
                        )

                    except Exception as e:

                        result = (
                            f"Tool error: {str(e)}"
                        )

                    function_results.append(
                        {
                            "type": "function_result",
                            "name": function_name,
                            "call_id": step.id,
                            "result": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        result,
                                        default=str
                                    ),
                                }
                            ],
                        }
                    )

            # No more function calls
            if not function_results:
                return interaction.output_text

            # Send tool results back to Gemini
            interaction = client.interactions.create(
                model=MODEL,
                previous_interaction_id=interaction.id,
                input=function_results,
                tools=tools,
            )

    except Exception as e:

        return (
            "Gemini error: "
            f"{str(e)}"
        )


# =========================================================
# MAIN ASK FUNCTION
# =========================================================

def ask_agent(question):
    """
    Main function used by the Streamlit application.
    """

    if analyzer is None:
        return "Please upload a dataset first."

    if not question or not question.strip():
        return "Please enter a question."

    question = question.strip()

    # -----------------------------------------------------
    # 1. TOTAL ROW COUNT
    # -----------------------------------------------------

    result = handle_row_count_question(question)

    if result is not None:
        return result

    # -----------------------------------------------------
    # 2. STATE + MOST INVOLVED VEHICLE
    # -----------------------------------------------------

    result = handle_state_vehicle_question(question)

    if result is not None:
        return result

    # -----------------------------------------------------
    # 3. VEHICLE COUNT
    # -----------------------------------------------------

    result = handle_vehicle_count_question(question)

    if result is not None:
        return result

    # -----------------------------------------------------
    # 4. STATE ACCIDENT COUNT
    # -----------------------------------------------------

    result = handle_state_count_question(question)

    if result is not None:
        return result

    # -----------------------------------------------------
    # 5. OTHER QUESTIONS -> GEMINI
    # -----------------------------------------------------

    return ask_gemini(question)


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "AI Excel Data Analyst Agent "
        "loaded successfully."
    )