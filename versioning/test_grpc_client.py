from __future__ import annotations
from rt_kiwoom import *
from agent import *
from time_manager import TimeManager
from config_manager import ConfigManager
import grpc
import prediction_pb2 as prediction_pb2
import prediction_pb2_grpc as prediction_pb2_grpc
from data_provider import *
from request import RequestBuilder
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cm = ConfigManager('config/.config.template.xml')
    agent = RTAgent(
        kiwoom_backend_ocx=None, 
        config_manager=cm, 
        log_config_path=cm.get_path('log_config_path'),
        log_path=cm.get_path('agent_log_path')
        )

    history_provider = MinuteChartDataProvider.Factory(cm, tag='history')
    history_minute_dic = history_provider.get_history_from_ndays_ago(n_days=5)
    

    agent.get_logger().info(f"Prediction client before request")
    request = RequestBuilder(agent, history_minute_dic, cm, window_size=720)
    response = request.send_and_wait()
    agent.get_logger().info(f"Prediction client received: {response}")
