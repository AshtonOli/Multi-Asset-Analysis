import dash
from dash import Dash, html

from data.datamanagement import data_manager


app = Dash(__name__, use_pages=True)

app.layout = html.Div([
    html.H1("Multi-Asset Analysis Dashboard"),
    html.Div([
        html.A(page["name"], href=page["path"])
        for page in dash.page_registry.values()
    ]),
    dash.page_container
])

if __name__ == '__main__':
    app.run(debug=True, port = 8080)