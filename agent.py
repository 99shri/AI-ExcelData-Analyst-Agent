import json
import os

from dotenv import load_dotenv
from google import genai

from data_tools import ExcelAnalyzer


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Fast model
MODEL = "gemini-3.5-flash-lite"

# Current uploaded dataset
analyzer = None


# ============================================================
# TOOL 1 — DATASET SUMMARY
# ============================================================

def dataset_summary():
    """Return basic information about the uploaded dataset."""

    if analyzer is None:
        return {"error": "No dataset uploaded."}

    return analyzer.get_summary()


# ============================================================
# TOOL 2 — CALCULATE
# ============================================================

def calculate_column(column, operation):
    """Calculate sum, average, minimum or maximum."""

    if analyzer is None:
        return "No dataset uploaded."

    return analyzer.calculate(
        column,
        operation
    )


# ============================================================
# TOOL 3 — TOP VALUES
# ============================================================

def get_top_values(column, n=5):
    """Return the most common values in a column."""

    if analyzer is None:
        return "No dataset uploaded."

    return analyzer.get_top_values(
        column,
        n
    )


# ============================================================
# TOOL 4 — FILTER
# ============================================================

def filter_data(column, value):
    """Filter the dataset using a column and value."""

    if analyzer is None:
        return "No dataset uploaded."

    return analyzer.filter_data(
        column,
        value
    )


# ============================================================
# GEMINI TOOL DEFINITIONS
# ============================================================

tools = [

    {
        "type": "function",
        "name": "dataset_summary",
        "description": (
            "Get the dataset structure including "
            "column names, row count, data types "
            "and missing values."
        ),
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },

    {
        "type": "function",
        "name": "calculate_column",
        "description": (
            "Calculate a numeric column. "
            "Use for total, average, minimum "
            "or maximum."
        ),
        "parameters": {
            "type": "object",
            "properties": {

                "column": {
                    "type": "string",
                    "description": "Exact column name."
                },

                "operation": {
                    "type": "string",
                    "enum": [
                        "sum",
                        "average",
                        "minimum",
                        "maximum"
                    ]
                }

            },
            "required": [
                "column",
                "operation"
            ]
        }
    },

    {
        "type": "function",
        "name": "get_top_values",
        "description": (
            "Find the most common values "
            "in a column."
        ),
        "parameters": {
            "type": "object",
            "properties": {

                "column": {
                    "type": "string"
                },

                "n": {
                    "type": "integer"
                }

            },
            "required": [
                "column"
            ]
        }
    },

    {
        "type": "function",
        "name": "filter_data",
        "description": (
            "Filter rows using a column "
            "and a specific value."
        ),
        "parameters": {
            "type": "object",
            "properties": {

                "column": {
                    "type": "string"
                },

                "value": {
                    "type": "string"
                }

            },
            "required": [
                "column",
                "value"
            ]
        }
    }

]


# ============================================================
# FUNCTION MAP
# ============================================================

available_functions = {

    "dataset_summary": dataset_summary,

    "calculate_column": calculate_column,

    "get_top_values": get_top_values,

    "filter_data": filter_data

}


# ============================================================
# AI AGENT
# ============================================================

def ask_agent(question):

    if analyzer is None:
        return "Please upload an Excel or CSV file first."

    # --------------------------------------------------------
    # Give Gemini ONLY the column names.
    # Don't send the whole dataset.
    # --------------------------------------------------------

    columns = list(analyzer.df.columns)

    prompt = f"""
You are an AI Data Analyst.

Dataset columns:
{columns}

User question:
{question}

Rules:

1. If the question requires actual data,
   use the appropriate tool.

2. NEVER guess numerical values.

3. For total/average/minimum/maximum,
   use calculate_column.

4. For most common values,
   use get_top_values.

5. For filtering,
   use filter_data.

6. If the question asks about the dataset
   structure, use dataset_summary.

7. Keep the final answer short and clear.
"""

    # --------------------------------------------------------
    # FIRST GEMINI CALL
    # --------------------------------------------------------

    interaction = client.interactions.create(
        model=MODEL,
        input=prompt,
        tools=tools
    )

    # --------------------------------------------------------
    # FIND TOOL CALL
    # --------------------------------------------------------

    function_calls = [
        step
        for step in interaction.steps
        if step.type == "function_call"
    ]

    # --------------------------------------------------------
    # NO TOOL NEEDED
    # --------------------------------------------------------

    if not function_calls:
        return interaction.output_text

    # --------------------------------------------------------
    # EXECUTE TOOLS
    # --------------------------------------------------------

    function_results = []

    for step in function_calls:

        function_name = step.name
        arguments = step.arguments

        function = available_functions.get(
            function_name
        )

        if function is None:

            result = {
                "error": f"Unknown tool: {function_name}"
            }

        else:

            try:

                result = function(
                    **arguments
                )

            except Exception as e:

                result = {
                    "error": str(e)
                }

        # ----------------------------------------------------
        # FAST PATH
        # ----------------------------------------------------
        # For simple calculations, return the result
        # directly without asking Gemini for another response.
        # ----------------------------------------------------

        if (
            function_name == "calculate_column"
            and len(function_calls) == 1
        ):

            operation = arguments.get("operation")
            column = arguments.get("column")

            operation_text = {
                "sum": "Total",
                "average": "Average",
                "minimum": "Minimum",
                "maximum": "Maximum"
            }.get(
                operation,
                operation
            )

            return (
                f"{operation_text} of "
                f"'{column}': **{result}**"
            )

        function_results.append({

            "type": "function_result",

            "name": function_name,

            "call_id": step.id,

            "result": [
                {
                    "type": "text",
                    "text": json.dumps(
                        result,
                        default=str
                    )
                }
            ]

        })

    # --------------------------------------------------------
    # COMPLEX QUESTIONS
    # --------------------------------------------------------
    # Only complex questions require Gemini to formulate
    # a natural-language response after the tool result.
    # --------------------------------------------------------

    final_interaction = client.interactions.create(

        model=MODEL,

        previous_interaction_id=interaction.id,

        input=function_results,

        tools=tools

    )

    return final_interaction.output_text