import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pygame
import threading

# 数据库路径
DB_PATH = "sensor_data.db"

# 初始化 Dash 应用
app = dash.Dash(__name__)

# 默认报警阈值
default_thresholds = {
    "temperature": 30,
    "humidity": 80,
    "pm25": 100,
    "noise": 70
}

# 自定义 CSS 样式
styles = {
    "graph-container": {
        "width": "45%",
        "display": "inline-block",
        "margin": "10px",
        "border": "1px solid #ddd",
        "border-radius": "5px",
        "padding": "10px",
        "background": "#f9f9f9"
    },
    "modal": {
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%, -50%)",
        "background": "#fff",
        "padding": "20px",
        "border": "1px solid #ccc",
        "border-radius": "5px",
        "z-index": 1000,
        "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.2)"
    },
    "overlay": {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "right": 0,
        "bottom": 0,
        "background": "rgba(0, 0, 0, 0.5)",
        "z-index": 999
    }
}

# 布局定义
app.layout = html.Div([
    html.H1("环境信息监控", style={"text-align": "center", "color": "#333"}),
    html.Div([
        html.Button("设置报警阈值", id="open-threshold-modal", style={"margin": "10px", "padding": "10px 20px", "background": "#007BFF", "color": "#fff", "border": "none", "border-radius": "5px", "cursor": "pointer"}),
        dcc.Store(id="threshold-store", data=default_thresholds),  # 存储报警阈值
    ], style={"text-align": "center"}),
    html.Div([
        html.Div(dcc.Graph(id='temperature-graph'), style=styles["graph-container"]),
        html.Div(dcc.Graph(id='humidity-graph'), style=styles["graph-container"]),
        html.Div(dcc.Graph(id='pm25-graph'), style=styles["graph-container"]),
        html.Div(dcc.Graph(id='noise-graph'), style=styles["graph-container"]),
    ], style={"display": "flex", "flex-wrap": "wrap", "justify-content": "center"}),
    dcc.Interval(
        id='interval-component',
        interval=2000,  # 每秒更新一次
        n_intervals=0
    ),
    # 报警阈值设置模态框
    html.Div(id="threshold-modal", style={"display": "none"}, children=[
        html.Div(style=styles["overlay"]),  # 遮罩层
        html.Div([
            html.H3("设置报警阈值", style={"margin-bottom": "20px"}),
            html.Label("温度阈值 (°C):", style={"display": "block", "margin-bottom": "10px"}),
            dcc.Input(id="temperature-threshold", type="number", value=default_thresholds["temperature"], style={"width": "100%", "padding": "5px", "margin-bottom": "10px"}),
            html.Label("湿度阈值 (%):", style={"display": "block", "margin-bottom": "10px"}),
            dcc.Input(id="humidity-threshold", type="number", value=default_thresholds["humidity"], style={"width": "100%", "padding": "5px", "margin-bottom": "10px"}),
            html.Label("PM2.5 阈值 (µg/m³):", style={"display": "block", "margin-bottom": "10px"}),
            dcc.Input(id="pm25-threshold", type="number", value=default_thresholds["pm25"], style={"width": "100%", "padding": "5px", "margin-bottom": "10px"}),
            html.Label("噪声阈值 (dB):", style={"display": "block", "margin-bottom": "10px"}),
            dcc.Input(id="noise-threshold", type="number", value=default_thresholds["noise"], style={"width": "100%", "padding": "5px", "margin-bottom": "10px"}),
            html.Button("保存", id="save-thresholds", style={"margin-right": "10px", "padding": "10px 20px", "background": "#28a745", "color": "#fff", "border": "none", "border-radius": "5px", "cursor": "pointer"}),
            html.Button("关闭", id="close-threshold-modal", style={"padding": "10px 20px", "background": "#dc3545", "color": "#fff", "border": "none", "border-radius": "5px", "cursor": "pointer"}),
        ], style=styles["modal"])
    ])
])

# 从数据库读取最近5分钟的数据
def fetch_data():
    five_minutes_ago = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(f"""
            SELECT * FROM sensor_data 
            WHERE timestamp >= '{five_minutes_ago}' 
            ORDER BY timestamp
        """, conn)
    return df

# 播放报警音频
def play_alarm():
    try:
        pygame.mixer.init()
        pygame.mixer.music.load("alarm.wav")  # 确保文件路径正确
        pygame.mixer.music.play()
    except Exception as e:
        print(f"播放音频失败: {e}")


# 更新图形的回调函数
@app.callback(
    [Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('pm25-graph', 'figure'),
     Output('noise-graph', 'figure')],
    [Input('interval-component', 'n_intervals'),
     Input('threshold-store', 'data')]
)
def update_graphs(n, thresholds):
    df = fetch_data()

    # 如果没有数据，返回空图形
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title='无数据', xaxis_title='时间', yaxis_title='值')
        return empty_fig, empty_fig, empty_fig, empty_fig

    # 获取最新的时间范围
    latest_time = df['timestamp'].max()
    earliest_time = (pd.to_datetime(latest_time) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    # 检查是否超出阈值并触发报警
    latest_data = df.iloc[-1]  # 获取最新一条数据
    for metric, value in latest_data[['temperature', 'humidity', 'pm25', 'noise']].items():
        if value > thresholds[metric]:
            print(f"报警: {metric} 超出阈值 ({value} > {thresholds[metric]})")
            threading.Thread(target=play_alarm).start()  # 异步播放报警音频

    # 创建温度图形
    temperature_fig = go.Figure()
    temperature_fig.add_trace(go.Scatter(x=df['timestamp'], y=df['temperature'], mode='lines', name='温度'))
    temperature_fig.update_layout(
        title='温度变化',
        xaxis_title='时间',
        yaxis_title='温度 (°C)',
        xaxis_range=[earliest_time, latest_time]
    )

    # 创建湿度图形
    humidity_fig = go.Figure()
    humidity_fig.add_trace(go.Scatter(x=df['timestamp'], y=df['humidity'], mode='lines', name='湿度'))
    humidity_fig.update_layout(
        title='湿度变化',
        xaxis_title='时间',
        yaxis_title='湿度 (%)',
        xaxis_range=[earliest_time, latest_time]
    )

    # 创建 PM2.5 图形
    pm25_fig = go.Figure()
    pm25_fig.add_trace(go.Scatter(x=df['timestamp'], y=df['pm25'], mode='lines', name='PM2.5'))
    pm25_fig.update_layout(
        title='PM2.5 变化',
        xaxis_title='时间',
        yaxis_title='PM2.5 (µg/m³)',
        xaxis_range=[earliest_time, latest_time]
    )

    # 创建噪声图形
    noise_fig = go.Figure()
    noise_fig.add_trace(go.Scatter(x=df['timestamp'], y=df['noise'], mode='lines', name='噪声'))
    noise_fig.update_layout(
        title='噪声变化',
        xaxis_title='时间',
        yaxis_title='噪声 (dB)',
        xaxis_range=[earliest_time, latest_time]
    )

    return temperature_fig, humidity_fig, pm25_fig, noise_fig

# 打开/关闭阈值设置模态框的回调函数
@app.callback(
    Output('threshold-modal', 'style'),
    [Input('open-threshold-modal', 'n_clicks'),
     Input('close-threshold-modal', 'n_clicks')],
    [State('threshold-modal', 'style')]
)
def toggle_modal(open_clicks, close_clicks, style):
    if open_clicks or close_clicks:
        if style["display"] == "none":
            style["display"] = "block"
        else:
            style["display"] = "none"
    return style

# 保存阈值的回调函数
@app.callback(
    Output('threshold-store', 'data'),
    [Input('save-thresholds', 'n_clicks')],
    [State('temperature-threshold', 'value'),
     State('humidity-threshold', 'value'),
     State('pm25-threshold', 'value'),
     State('noise-threshold', 'value')]
)
def save_thresholds(n_clicks, temp, humi, pm25, noise):
    if n_clicks:
        return {
            "temperature": temp,
            "humidity": humi,
            "pm25": pm25,
            "noise": noise
        }
    return default_thresholds

# 启动 Dash 应用
if __name__ == '__main__':
    app.run(debug=True)