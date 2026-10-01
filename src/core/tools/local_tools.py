from langchain.tools import tool

"""
Tool 1 (mockear): search_financial_data(metric, period) - Retorna datos financieros simulados. Delay de 2 segundos
Tool 2 (mockear): calculate_ratio(numerator, denominator) - Retorna resultado numérico
"""

@tool("search_financial_data")
def search_financial_data(metric: str, period: str) -> dict:
    """
    Simulates searching for financial data based on a given metric and period.

    Parameters:
        metric (str): The financial metric to search for (e.g., 'revenue', 'profit').
        period (str): The period to analyze (e.g., '1mo', '3mo', '1y').

    Returns:
        dict: A dictionary containing simulated financial data.
    """
    # Simulated financial data
    simulated_data = {
        "metric": metric,
        "period": period,
        "data": {
            "2023-01": 1000000,
            "2023-02": 1200000,
            "2023-03": 1100000,
            "2023-04": 1300000,
            "2023-05": 1250000,
        }
    }
    
    return simulated_data


@tool("calculate_ratio")
def calculate_ratio(numerator: float, denominator: float) -> float:
    """
    Calculates a financial ratio based on the provided numerator and denominator.

    Parameters:
        numerator (float): The numerator value for the ratio.
        denominator (float): The denominator value for the ratio.

    Returns:
        float: The calculated ratio, or an error message if the denominator is zero.
    """
    if denominator == 0:
        return {"error": "Denominator cannot be zero."}
    
    ratio = numerator / denominator
    return ratio


FINANCIAL_ANALYST_TOOLS = [
    search_financial_data,
    calculate_ratio
]