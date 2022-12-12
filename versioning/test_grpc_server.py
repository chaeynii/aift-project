from __future__ import annotations
from concurrent import futures
from rt_kiwoom import *
from agent import *
from time_manager import TimeManager
from config_manager import ConfigManager
import grpc
import prediction_pb2 as prediction_pb2
import prediction_pb2_grpc as prediction_pb2_grpc
from baseline_model import InputBuilder_BaselineModel, BaselineModel
import sys
import pickle
import logging

class PredictionServer(prediction_pb2_grpc.PredictorServicer):
    def __init__(self, model):
        self.model=model

    def Predict(self, request, context):
        # dummy implementation for just testing
        input_builder = InputBuilder_BaselineModel(request)
        logging.getLogger().info(f"{input_builder.X_test=}")
        y_pred = self.model.predict(input_builder.X_test)
        logging.getLogger().info(f"{y_pred=}")
        y_proba = self.model.predict_proba(input_builder.X_test)
        logging.getLogger().info(f"{y_proba=}")

        return prediction_pb2.PredictResponse(actions={'NOP':y_proba[0][0], 'X':y_proba[0][1], 'Y':y_proba[0][2]})


def serve(model):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    prediction_pb2_grpc.add_PredictorServicer_to_server(PredictionServer(model), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":

    print("실행중")

    model = BaselineModel("./models/baseline/automl_10m.pkl")#./jupyter/.automl_3m.pkl
    print("실행끝")

    logging.basicConfig()
    print('1')
    logging.getLogger().setLevel(logging.INFO)
    print('2')
    serve(model)
    print('3')
