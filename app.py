import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import numpy as np
import base64
import io
from docx import Document
from docx.shared import Inches
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])

def interpretar_valor(valor_str):
    prefijos = {
        "E": 1e18, "P": 1e15, "T": 1e12, "G": 1e9, "M": 1e6, "k": 1e3,
        "h": 1e2, "da": 1e1, "d": 1e-1, "c": 1e-2, "m": 1e-3,
        "u": 1e-6, "µ": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18
    }
    valor_str = valor_str.strip()
    for p in sorted(prefijos, key=lambda x: -len(x)):
        if valor_str.lower().endswith(p.lower()):
            try:
                num = float(valor_str[:-len(p)])
                return num * prefijos[p]
            except:
                pass
    return float(valor_str)

def formatear_valor(valor):
    if abs(valor) >= 1:
        return f"{valor:.3f} A"
    elif abs(valor) >= 1e-3:
        return f"{valor*1e3:.3f} mA"
    elif abs(valor) >= 1e-6:
        return f"{valor*1e6:.3f} µA"
    else:
        return f"{valor*1e9:.3f} nA"

def calcular_y_graficar(config, Vcc, Rc, Rb, Re, beta, Vbe):
    Vcc = interpretar_valor(Vcc)
    Rc = interpretar_valor(Rc)
    Rb = interpretar_valor(Rb)
    Re = interpretar_valor(Re)
    beta = float(beta)
    Vbe = interpretar_valor(Vbe)

    if config == "Emisor común":
        divisor = Rb + (beta + 1) * Re if Rb != 0 or Re != 0 else 1
        Ib = (Vcc - Vbe) / divisor
        Ic = beta * Ib
        Ie = Ic + Ib

    elif config == "Base común":
        Ie = (Vcc - Vbe) / (Re + Rc)
        Ic = (beta / (beta + 1)) * Ie
        Ib = Ie - Ic

    elif config == "Colector común":
        divisor = Rb + (beta + 1) * Re if Rb != 0 or Re != 0 else 1
        Ib = (Vcc - Vbe) / divisor
        Ie = (beta + 1) * Ib
        Ic = beta * Ib

    Ve = Ie * Re
    Vb = Ve + Vbe
    Vc = Vcc if config == "Colector común" else Vcc - Ic * Rc
    Vce = Vc - Ve
    Vbc = Vb - Vc

    Vce_sat = 0.2
    Ic_sat = Vcc / Rc
    Pmax = Vce_sat * Ic_sat

    estado = "SATURACIÓN" if Vce < 0.2 else "ACTIVA" if Ic > 0 else "CORTE"

    texto = f"""
Estado del transistor: {estado}

Resultados:
Ib = {formatear_valor(Ib)}
Ic = {formatear_valor(Ic)}
Ie = {formatear_valor(Ie)}
Vb = {Vb:.2f} V
Ve = {Ve:.2f} V
Vc = {Vc:.2f} V
Vce = {Vce:.2f} V
Vbc = {Vbc:.2f} V

Punto máximo de potencia en saturación:
Ic(sat) = {formatear_valor(Ic_sat)}
Vce(sat) = {Vce_sat:.2f} V
Pmax = {Pmax:.3f} W
"""

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, Vcc], y=[Ic_sat, 0], mode='lines', name='Recta de carga'))
    fig.add_trace(go.Scatter(x=[Vce], y=[Ic], mode='markers', name='Punto Q', marker=dict(size=10, color='red')))
    fig.update_layout(title="Recta de carga y punto Q", xaxis_title="VCE (V)", yaxis_title="IC (A)", template="plotly_dark")

    return texto.strip(), fig

app.layout = dbc.Container([
    html.H2("Analizador de Transistor BJT", className="my-3 text-center"),
    dbc.Row([
        dbc.Col(
            [
                dbc.Label("Configuración"),
                dcc.Dropdown(
                    id="config",
                    options=[
                        {"label": "Emisor común", "value": "Emisor común"},
                        {"label": "Base común", "value": "Base común"},
                        {"label": "Colector común", "value": "Colector común"}
                    ],
                    value="Emisor común"
                ),
                # Input fields for each parameter
                *[
                    html.Div([
                        dbc.Label(campo),
                        dbc.Input(id=campo, placeholder=campo, type="text", className="mb-2", value="0")
                    ]) for campo in ["Vcc", "Rc", "Rb", "Re", "β", "Vbe"]
                ],
                dbc.Button("Calcular", id="btn-calc", className="btn btn-success my-2")
            ],
            md=4
        ),

        dbc.Col([
            dcc.Tabs(id="tabs", value="tab1", children=[
                dcc.Tab(label='Resultados', value='tab1'),
                dcc.Tab(label='Gráfica', value='tab2'),
                dcc.Tab(label='Curvas Dinámicas', value='tab3')
            ]),
            html.Div(id="contenido_tab")
        ], md=8)
    ])
], fluid=True)

@app.callback(
    Output("contenido_tab", "children"),
    Input("tabs", "value"),
    Input("btn-calc", "n_clicks"),
    State("config", "value"),
    State("Vcc", "value"), State("Rc", "value"), State("Rb", "value"),
    State("Re", "value"), State("β", "value"), State("Vbe", "value")
)
def actualizar_tabs(tab, n, config, Vcc, Rc, Rb, Re, beta, Vbe):
    if not n:
        return ""
    resultados, grafico = calcular_y_graficar(config, Vcc, Rc, Rb, Re, beta, Vbe)

    if tab == "tab1":
        return html.Pre(resultados, style={"whiteSpace": "pre-wrap", "fontFamily": "monospace"})
    elif tab == "tab2":
        return dcc.Graph(figure=grafico)
    elif tab == "tab3":
        Vce_range = np.linspace(0, interpretar_valor(Vcc), 100)
        Ic_curva = [float(beta) * (interpretar_valor(Vcc) - interpretar_valor(Vbe)) / (interpretar_valor(Rb) + (float(beta)+1)*interpretar_valor(Re)) for _ in Vce_range]
        fig_curvas = go.Figure()
        fig_curvas.add_trace(go.Scatter(x=Vce_range, y=Ic_curva, mode='lines', name='Curva IC vs VCE'))
        fig_curvas.update_layout(title="Curva Dinámica IC vs VCE", xaxis_title="VCE (V)", yaxis_title="IC (A)", template="plotly_dark")
        return dcc.Graph(figure=fig_curvas)

if __name__ == "__main__":
    app.run(debug=True)