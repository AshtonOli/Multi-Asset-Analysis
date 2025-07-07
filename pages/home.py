import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from data.datamanagement import data_manager


dash.register_page(__name__, path="/", name="Home")
layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.H1("Crypto Holdings", className="text-center"),
                    dash_table.DataTable(
                        id="crypto-assets-table",
                        data=[
                            {
                                "symbol": symbol,
                                "units": data_manager.get_symbol_element(symbol,"units"),
                                "price": data_manager.get_symbol_element(symbol,"price"),  # Placeholder for price
                                "value": data_manager.get_symbol_element(symbol,"value"),  # Placeholder for value
                                "weight": data_manager.get_symbol_element(symbol,"weight"),  # Placeholder for weight
                            }

                            for symbol in data_manager.get_symbol_list()
                        ],
                        columns=[
                            {"name": "Symbol", "id": "symbol", "type": "text"},
                            {"name": "Units", "id": "units", "type": "numeric"},
                            {"name": "Price", "id": "price", "type": "numeric"},
                            {"name": "Value", "id": "value", "type": "numeric"},
                        ],
                        style_table={"overflow": "scroll", "height": 600},
                        style_cell={"textAlign": "center"},
                        row_deletable=True,
                        editable=True,
                        style_header={
                            "backgroundColor": "rgb(230, 230, 230)",
                            "fontWeight": "bold",
                        },
                    ),
                    width={"size": 12, "offset": 0, "order": 1},
                )
            ]
        )
    ]
)
