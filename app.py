import dash
from dash import html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import numpy as np

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.SLATE],
    title="Analizador BJT"
)

app.title = "Analizador BJT - Transistores"

# ----- Estilos personalizados -----
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { background-color: #1e1e2f; font-family: 'Segoe UI', sans-serif; }
            .soft-box {
                background-color: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 12px;
                box-shadow: 0 4px 30px rgba(0,0,0,0.1);
                backdrop-filter: blur(4px);
                border: 1px solid rgba(255,255,255,0.1);
                margin-bottom: 15px;
                transition: all 0.3s ease-in-out;
            }
            input:invalid {
                background-color: #ffcccc !important;
            }
            .error-input {
                background-color: #ffcccc !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ----- Funciones de utilidad -----

def interpretar_valor(valor_str):
    prefijos = {
        "E": 1e18, "P": 1e15, "T": 1e12, "G": 1e9, "M": 1e6, "k": 1e3,
        "h": 1e2, "da": 1e1, "d": 1e-1, "c": 1e-2, "m": 1e-3,
        "u": 1e-6, "µ": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18
    }
    valor_str = valor_str.strip()
    if not valor_str:
        return None
    for p in sorted(prefijos, key=lambda x: -len(x)):
        if valor_str.lower().endswith(p.lower()):
            try:
                num = float(valor_str[:-len(p)])
                return num * prefijos[p]
            except:
                raise ValueError("Error al interpretar valor con prefijo")
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

# ----- Lógica principal -----

def calcular_y_graficar(config, Vcc, Rc, Rb, Re, beta, Vbe):
    try:
        Vcc = interpretar_valor(Vcc)
        Rc = interpretar_valor(Rc)
        Rb = interpretar_valor(Rb)
        Re = interpretar_valor(Re)
        beta = float(beta)
        Vbe = interpretar_valor(Vbe)
    except:
        return html.Div("⚠️ Error en los valores ingresados. Revisa los campos en rojo."), go.Figure()

    faltantes = []
    for nombre, valor in zip(["Vcc", "Rc", "Rb", "Re", "β", "Vbe"], [Vcc, Rc, Rb, Re, beta, Vbe]):
        if valor is None:
            faltantes.append(nombre)

    if faltantes:
        return html.Div(f"⚠️ Valores faltantes: {', '.join(faltantes)}"), go.Figure()

    Ib = Ic = Ie = Vb = Ve = Vc = Vce = Vbc = 0

    if config == "Emisor común":
        divisor = Rb + (beta + 1) * Re if (Rb or Re) else 1
        Ib = (Vcc - Vbe) / divisor
        Ic = beta * Ib
        Ie = Ic + Ib

    elif config == "Base común":
        Ie = (Vcc - Vbe) / (Re + Rc)
        Ic = (beta / (beta + 1)) * Ie
        Ib = Ie - Ic

    elif config == "Colector común":
        divisor = Rb + (beta + 1) * Re if (Rb or Re) else 1
        Ib = (Vcc - Vbe) / divisor
        Ie = (beta + 1) * Ib
        Ic = beta * Ib

    Ve = Ie * Re
    Vb = Ve + Vbe
    Vc = Vcc if config == "Colector común" else Vcc - Ic * Rc
    Vce = Vc - Ve
    Vbc = Vb - Vc

    Vce_sat = 0.2
    Ic_sat = Vcc / Rc if Rc else 0
    Pmax = Vce_sat * Ic_sat

    estado = "SATURACIÓN" if Vce < 0.2 else "ACTIVA" if Ic > 0 else "CORTE"

    resultados = html.Table([
        html.Thead(html.Tr([html.Th("Parámetro"), html.Th("Valor")])),
        html.Tbody([
            html.Tr([html.Td("Estado del transistor"), html.Td(estado)]),
            html.Tr([html.Td("Ib"), html.Td(formatear_valor(Ib))]),
            html.Tr([html.Td("Ic"), html.Td(formatear_valor(Ic))]),
            html.Tr([html.Td("Ie"), html.Td(formatear_valor(Ie))]),
            html.Tr([html.Td("Vb"), html.Td(f"{Vb:.2f} V")]),
            html.Tr([html.Td("Ve"), html.Td(f"{Ve:.2f} V")]),
            html.Tr([html.Td("Vc"), html.Td(f"{Vc:.2f} V")]),
            html.Tr([html.Td("Vce"), html.Td(f"{Vce:.2f} V")]),
            html.Tr([html.Td("Vbc"), html.Td(f"{Vbc:.2f} V")]),
            html.Tr([html.Td("Ic(sat)"), html.Td(formatear_valor(Ic_sat))]),
            html.Tr([html.Td("Vce(sat)"), html.Td(f"{Vce_sat:.2f} V")]),
            html.Tr([html.Td("Pmax"), html.Td(f"{Pmax:.3f} W")])
        ])
    ], className="table table-dark table-striped soft-box")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, Vcc], y=[Ic_sat, 0], mode='lines', name='Recta de carga'))
    fig.add_trace(go.Scatter(x=[Vce], y=[Ic], mode='markers', name='Punto Q', marker=dict(size=10, color='red')))
    fig.update_layout(title="Recta de carga y punto Q", xaxis_title="VCE (V)", yaxis_title="IC (A)", template="plotly_dark")

    return resultados, fig

# ----- Diseño principal -----

app.layout = dbc.Container([
    html.H2("Analizador de Transistor BJT", className="my-3 text-center text-light"),

    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Label("Configuración"),
                dcc.Dropdown(
                    id="config",
                    options=[
                        {"label": "Emisor común", "value": "Emisor común"},
                        {"label": "Base común", "value": "Base común"},
                        {"label": "Colector común", "value": "Colector común"}
                    ],
                    value="Emisor común",
                    className="mb-3"
                ),
                *[
                    html.Div([
                        dbc.Label(campo),
                        dbc.Input(id=campo, placeholder=campo, type="text", className="mb-2", value="")
                    ]) for campo in ["Vcc", "Rc", "Rb", "Re", "β", "Vbe"]
                ],
                dbc.Button("Calcular", id="btn-calc", className="btn btn-success mt-2")
            ], className="soft-box")
        ], md=4),

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
        return resultados
    elif tab == "tab2":
        return dcc.Graph(figure=grafico)
    elif tab == "tab3":
        try:
            Vce_range = np.linspace(0, interpretar_valor(Vcc), 100)
            divisor = interpretar_valor(Rb) + (float(beta)+1)*interpretar_valor(Re)
            Ib = (interpretar_valor(Vcc) - interpretar_valor(Vbe)) / divisor
            Ic_curva = [float(beta) * Ib for _ in Vce_range]
            fig_curvas = go.Figure()
            fig_curvas.add_trace(go.Scatter(x=Vce_range, y=Ic_curva, mode='lines', name='Curva IC vs VCE'))
            fig_curvas.update_layout(title="Curva Dinámica IC vs VCE", xaxis_title="VCE (V)", yaxis_title="IC (A)", template="plotly_dark")
            return dcc.Graph(figure=fig_curvas)
        except:
            return html.Div("Error al calcular curva dinámica. Revisa los valores.")

if __name__ == "__main__":
    app.run(debug=True)
