"""Planner routing cases taken from real traffic (data/rag_query_logs).

Checks per case (all optional):
  tools_include / tools_exclude: tool names that must / must not appear
  tools_exact: exact set of tool names (empty list means no tools)
  modules: exact module set on the first get_fund_data / get_investor_portfolio call
  windows: exact windows on the first get_fund_data call
  sections / top_n: on the first get_portfolio_data call
  scope: allowed portfolio_scope values
  advice: asks_for_advice must equal this
Every case also fails when the plan has more than max_tools (default 3) tool calls.
"""

CASES: list[dict] = [
    {"q": "what is the nav of axis largecap fund", "tools_exact": ["get_fund_data"], "modules": ["snapshot"]},
    {"q": "what is the nav of the bandhan large cap fund ?", "tools_exact": ["get_fund_data"], "modules": ["snapshot"]},
    {"q": "what is the aum of hdfc large cap fund?", "tools_exact": ["get_fund_data"], "modules": ["snapshot"]},
    {"q": "whats the 1 year historical retrurns of absl large cap?", "tools_exact": ["get_fund_data"], "windows": ["1Y"]},
    {"q": "show me hdfc large cap fund one day return", "tools_exclude": ["search_financial_news"], "windows": ["1D"]},
    {"q": "tell me about the fund manager of the hdfc large cap fund", "tools_exact": ["get_fund_data"], "modules": ["managers"]},
    {"q": "what is the drawdown of hdfc large cap fund?", "tools_exclude": ["search_financial_news"], "modules_include": ["drawdown"]},
    {"q": "do the risk analysis of hdfc large cap fund", "tools_exclude": ["search_financial_news"], "modules_include": ["risk"]},
    {"q": "tell me about hdfc large cap funds weekly sip limit", "tools_exact": ["get_fund_data"], "modules": ["limits"]},
    {"q": "what is the name of the benchmark of the hdfc large cap?", "tools_exclude": ["search_financial_news"]},
    {"q": "what are the top 5 sectors of absl Conservative Hybrid Active FOF", "tools_exact": ["get_portfolio_data"], "sections": ["sectors"], "top_n": 5},
    {"q": "top sector of axis largecap", "tools_exact": ["get_portfolio_data"], "sections": ["sectors"]},
    {"q": "compare axis large cap fund and hdfc large cap fund?", "tools_exact": ["compare_funds"]},
    {"q": "tell me about the news related to the hdfc large cap fund in last one month?", "tools_include": ["search_financial_news"]},
    {"q": "tell me about the news related to axis bank?", "tools_include": ["search_financial_news"], "tools_exclude": ["get_fund_data", "compare_funds"]},
    {"q": "Why is gold down", "tools_include": ["search_financial_news"], "tools_exclude": ["get_fund_data", "compare_funds"]},
    {"q": "what are the current market news", "tools_exclude": ["get_fund_data", "compare_funds", "get_investor_portfolio"]},
    {"q": "what is swp", "tools_exact": []},
    {"q": "differenc  between flexi cap and hybrid fund", "tools_exact": []},
    {"q": "if i invest for 10 year 10000 per month and increased it 10% half yearly so how much money would i have if the average return is 12", "tools_exact": []},
    {"q": "tell me any 5 defence funds", "tools_exact": ["screen_funds_by_exposure"], "top_n_screen": 5},
    {"q": "name the highest rating large cap fund?", "tools_include": ["screen_funds_by_exposure"], "tools_exclude": ["search_financial_news"]},
    {"q": "recommend me any 5 large cap funds", "tools_include": ["screen_funds_by_exposure"], "advice": True},
    {"q": "whats my portfolios aum", "tools_exact": ["get_investor_portfolio"], "scope": ["investor"], "modules": ["summary"]},
    {"q": "whats my last one months return s", "tools_include": ["get_investor_portfolio"], "scope": ["investor", "both"]},
    {"q": "show me my all funds one month returns", "tools_include": ["get_investor_portfolio"], "scope": ["investor", "both"], "windows_if_fund_data": ["1M"]},
    {"q": "what is the concentration of my portfolio", "tools_include": ["get_investor_portfolio"], "scope": ["investor", "both"]},
    {"q": "do i have any systematic tranfer process", "tools_exact": ["get_investor_portfolio"], "modules": ["stp"]},
    {"q": "which of my funds have banking sector in it and how much", "tools_include": ["get_investor_portfolio"], "scope": ["investor", "both"]},
    {"q": "whats my risk profile", "tools_include": ["get_investor_portfolio"], "scope": ["investor", "both"]},
    {"q": "How will rising bond yields impact debt mutual funds in India?", "tools_exclude": ["get_investor_portfolio"]},
    {"q": "tell me hdfc flexi cap fund?", "tools_include": ["get_fund_data"], "scope": ["none", "catalog"]},
    {"q": "why did hdfc large cap fall in the last month", "tools_include": ["get_fund_data"], "scope": ["none", "catalog"]},
    {"q": "compare any two large cap funds which are performing well in last 1 year?", "tools_exclude": ["get_investor_portfolio"]},
    # Needs a prior contra turn in memory; live eval without that history is not meaningful.
    {"q": "Compare this with the large cap in my portfolio", "tools_include": ["compare_funds", "get_investor_portfolio"], "needs_prior_fund": True},
]
