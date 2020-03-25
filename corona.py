import dash
from datetime import date, timedelta
from flask_session import Session
from common import cache
import os
import pandas as pd
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
from utils.colors import THEME_COLORS

from calc.simulation import simulate_individuals
from calc.datasets import get_detected_cases
from components.cards import GraphCard
from components.graphs import make_layout
from variables import set_variable, get_variable


os.environ['DASH_PRUNE_ERRORS'] = 'False'
os.environ['DASH_SILENCE_ROUTES_LOGGING'] = 'False'


app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True
server = app.server
with server.app_context():
    server.config.from_object('common.settings')

    cache.init_app(server)
    sess = Session()
    sess.init_app(server)


def generate_layout():
    rows = []
    rows.append(dbc.Row([
        dbc.Col([
            html.H2('COVID-19-epidemian kehittyminen: %s' % get_variable('area_name')),
        ], className='mb-4'),
    ], className='mt-4'))
    rows.append(dbc.Row([
        dbc.Col([
            dbc.Button('Laske', id='run-simulation')
        ])
    ]))
    rows.append(dbc.Row([
        dbc.Col([
            dcc.Loading(html.Div(id="sir-graph-container"))
        ]),
    ]))
    rows.append(dbc.Row([
        dbc.Col([
            html.Div(id='day-details-container')
        ])
    ]))
    return dbc.Container([dbc.Row([dbc.Col(rows)])])


app.layout = generate_layout


@app.callback(
    Output('day-details-container', 'children'),
    [Input('sir-graph', 'clickData')]
)
def show_day_details(data):
    print(data)
    return html.Div()


@app.callback(
    Output('sir-graph-container', 'children'),
    [Input('run-simulation', 'n_clicks')],
)
def building_selector_callback(n_clicks):
    set_variable('simulation_days', 60)
    det = get_detected_cases()
    df = simulate_individuals()

    pop_cols = (
        ('susceptible', 'yellow', 'Alttiit'),
        ('infected', 'orange', 'Tartunnan saaneet'),
        ('all_detected', 'teal', 'Havaitut tapaukset (sim.)'),
        ('hospitalized', 'red', 'Sairaalassa'),
        ('dead', 'indigo', 'Kuolleet'),
        ('recovered', 'green', 'Toipuneet'),
    )

    card = GraphCard('population', graph=dict(config=dict(responsive=False)))
    traces = []
    for col, color, name in pop_cols:
        if col in ('susceptible', 'recovered'):
            continue
        t = dict(
            type='scatter', line=dict(color=THEME_COLORS[color]),
            name=name, x=df.index, y=df[col], mode='lines'
        )
        traces.append(t)

    traces.append(dict(
        type='scatter', marker=dict(color=THEME_COLORS['teal']),
        name='Havaitut tapaukset (tod.)', x=det.index, y=det['confirmed'], mode='markers'
    ))

    layout = make_layout(title='Väestö', height=250, showlegend=True)
    fig = dict(data=traces, layout=layout)
    card.set_figure(fig)
    c1 = card.render()

    hc_cols = (
        ('hospital_beds', 'Vuodepaikat'),
        ('icu_units', 'Tehohoitopaikat')
    )
    card = GraphCard('healthcare', graph=dict(config=dict(responsive=False)))
    traces = []
    for col, name in hc_cols:
        t = dict(type='scatter', name=name, x=df.index, y=df[col], mode='lines')
        traces.append(t)
    layout = make_layout(title='Sairaanhoitojärjestelmä', height=250, showlegend=True)
    fig = dict(data=traces, layout=layout)
    card.set_figure(fig)
    c2 = card.render()

    param_cols = (
        ('r', 'R-luku'),
    )
    card = GraphCard('params', graph=dict(config=dict(responsive=False)))
    traces = []
    for col, name in param_cols:
        t = dict(type='scatter', name=name, x=df.index, y=df[col], mode='lines')
        traces.append(t)
    layout = make_layout(title='Epidemian parametrit', height=250, showlegend=True)
    fig = dict(data=traces, layout=layout)
    card.set_figure(fig)
    c3 = card.render()

    return dbc.Row([dbc.Col(c1, md=12), dbc.Col(c2, md=12), dbc.Col(c3, md=12)])


if __name__ == '__main__':
    # Write the process pid to a file for easier profiling with py-spy
    with open('.corona.pid', 'w') as pid_file:
        pid_file.write(str(os.getpid()))
    app.run_server(debug=True, port=8123)
