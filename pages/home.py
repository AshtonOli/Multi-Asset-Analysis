import dash
from dash import html, dcc, dash_table, callback, ctx
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from src.util import dollar_format
from data.datamanagement import portfolio_manager
from typing import Tuple, List, Dict, Any
import plotly.graph_objects as go
import asyncio

portfolio_manager.gen_portfolio_performance()

def update_portfolio_display() -> Tuple[List[Dict[str, Any]], go.Figure, go.Figure]:
    """Helper function to generate updated table and chart data"""
    data_table = [
        {
            "symbol": symbol,
            "units": portfolio_manager.get_symbol_element(symbol, "units"),
            "price": dollar_format(portfolio_manager.get_symbol_element(symbol, "close")),
            "value": dollar_format(portfolio_manager.get_symbol_element(symbol, "value")),
            "weight": dollar_format(portfolio_manager.get_symbol_element(symbol, "weight")),
        }
        for symbol in portfolio_manager.get_symbol_list()
    ]
    
    pie_chart = go.Figure(
        data=[
            go.Pie(
                labels=list(portfolio_manager.symbols.keys()),
                values=[portfolio_manager.get_symbol_element(symbol, "weight") for symbol in portfolio_manager.symbols.keys()],
                marker_colors = [portfolio_manager.get_symbol_element(symbol, "colour") for symbol in portfolio_manager.symbols.keys()]
            )
        ]
    )

    pp_chart = go.Figure(
        data = [
            go.Scatter(
                x = portfolio_manager.portfolio_performance.opentime,
                y = portfolio_manager.portfolio_performance.portfolio_value,
                mode = "lines",
            )
        ],
        layout = go.Layout(
            xaxis = {"title" : "Datetime"},
            yaxis = {
                "title" : "Portfolio Value ($)",
                "tickformat": ",.2f",
                "tickprefix" : "$",
                "ticksuffix" : " USD",

                }
        )
    )
    
    return data_table, pie_chart, pp_chart

init_table, init_pie, init_pp = update_portfolio_display()
portfolio_value = f"Portfolio value: {dollar_format(portfolio_manager.portfolio_value)}"

dash.register_page(__name__, path="/", name="Home")
layout = html.Div(
    [
        html.H1("Crypto Holdings", className="text-center"),
        html.H3(portfolio_value,id = "portfolio-value"),
        dbc.Row(
            [
                # Portfolio summary
                dbc.Col(
                    children = [
                        # Portfolio Summary Table
                        dash_table.DataTable(
                            id="crypto-assets-table",
                            data=init_table,
                            columns=[
                                {"name": "Symbol", "id": "symbol", "type": "text"},
                                {"name": "Units", "id": "units", "type": "numeric"},
                                {"name": "Price", "id": "price", "type": "numeric"},
                                {"name": "Value", "id": "value", "type": "numeric"},
                            ],
                            # style_table={"overflow": "scroll"},
                            style_cell={"textAlign": "center"},
                            row_deletable=True,
                            editable=True,
                            style_header={
                                "backgroundColor": "rgb(230, 230, 230)",
                                "fontWeight": "bold",
                            },
                        ),
                        html.Br(),
                        # New symbol input
                        dcc.Input(
                            id = "new-symbol",
                            type =  "text",
                            placeholder= "BTCUSDT",
                            minLength = 0,
                            maxLength= 10,
                            required= True
                        ),
                        # New Symbol input units
                        dcc.Input(
                            id = "new-symbol-units",
                            type =  "number",
                            placeholder= 1,
                            minLength = 0,
                            maxLength= 10,
                            required= True
                        ),
                        # Process new symbol
                        html.Button("+", id = "add-symbol", n_clicks = 0)
                    ],
                    width={"size": 12, "offset": 0, "order": 1},
                ),
                dbc.Col(
                    dcc.Graph(
                        id = "weight-pie",
                        figure = init_pie
                    )
                ),
                dbc.Col(
                    dcc.Graph(
                        id = "portfolio-performance",
                        figure = init_pp
                    )
                )
            ]
        )
    ]
)
@callback(
    [   
        Output("portfolio-value", "children"),
        Output("crypto-assets-table", "data"),
        Output("weight-pie", "figure"),
        Output("portfolio-performance", "figure"),
        Output("add-symbol", "n_clicks")
    ],
    [
        Input("add-symbol", "n_clicks"),
        Input("crypto-assets-table", "data_previous")
    ],
    [
        State("new-symbol", "value"),
        State("new-symbol-units", "value"),
        State("crypto-assets-table", "data")
    ]
)
def manage_portfolio(n_clicks, data_previous, new_symbol, units, current_data) -> Tuple[str,List[Dict[str, Any]], go.Figure, go.Figure, int]:
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == "add-symbol" and n_clicks > 0:
        print(f"Adding: {new_symbol}")
        portfolio_manager.add_symbol(new_symbol, units, "1h")
        asyncio.run(portfolio_manager.update_all_symbols_async())
    elif triggered_id == "crypto-assets-table" and data_previous is not None:
        for row in data_previous:
            if row not in current_data:
                print(f"Removing: {row}")
                portfolio_manager.remove_symbol(row["symbol"])
                asyncio.run(portfolio_manager.update_all_symbols_async())
    else:
        raise dash.exceptions.PreventUpdate()
    portfolio_manager.gen_combine_ohlc()
    portfolio_manager.gen_portfolio_performance()

    data_table, pie_chart, pp_chart = update_portfolio_display()
    portfolio_value = f"Portfolio value: {dollar_format(portfolio_manager.portfolio_value)}"
    return (portfolio_value,data_table, pie_chart, pp_chart, 0)