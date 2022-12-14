from time import sleep
import pandas as pd
import numpy as np
import tensorflow as tf
import hashlib
import sys
from tensorflow import keras

from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import socketio

socketClient = socketio.Client()

features = []
prediction = []
box_information = []

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def test_connect(auth):
    socketio.emit('my response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@socketio.on('request_features')
def request_features():
    print('client requested features. sending')
    socketio.emit('features', {'data': box_information})

@socketio.on('request_prediction')
def request_prediction():
    print('client requested prediction. sending')
    socketio.emit('prediction', {'data': prediction.tolist()})

def filescanner():
    socketClient.connect('http://localhost:5000')
    global features, prediction, box_information
    # load model
    model = keras.models.load_model('box_model_89.45.2_london_checkpoint_6')
    # load features from file
    id = 0
    lines = []
    while True:
        proceed = True
        #try to open file
        try:
            f = open("box_features.csv", "r")
        except:
            proceed = False
            #print("failed opening file")

        #try to read opened file
        try:
            lines = f.readlines()
        except:
            proceed = False
            #print("failed reading lines")

        #try to close file
        try:
            f.close()
        except:
            print("failed closing file")

        #proceed to predicting
        if(proceed):
            for i in range(len(lines)):
                lines[i] = lines[i][:-1]

            if(len(lines)<4):
                print("lines length is less than four. features corrupt")
                f.close()
                write_success = False
                error_count = 0
                while(write_success == False and error_count<20):
                    try:
                        fp = open("box_prediction.csv", "w")
                        fp.write("features corrupt")
                        write_success = True
                        fp.close()
                    except:
                        error_count += 1
                        print("failed writing (corrupt warning)",sys.exc_info()[0],". tries: "+str(error_count))
                        sleep(0.25)
                sleep(0.1)
                continue

            verified = False
            if id != lines[0]:
                id = lines[0]
                feature_string = lines[1]
                feature_hash = lines[2]
                calculated_hash = hashlib.md5(feature_string.encode()).hexdigest()
                print(id)
                #print(feature_string[-1])
                print(feature_hash)
                print(calculated_hash)
                if feature_hash == calculated_hash:
                    print("verified")
                    verified = True
                else:
                    print("integrity lost")

            if(verified):
                features = [feature_string.split(",")[:-1]]
                box_information = [lines[3].split(",")]
                prediction = model.predict(np.array(features,dtype="float32"))
                print("prediction: ")
                #print(features)
                print(prediction)
                content = str(id) + "\n"
                line2 = str(prediction[0][0]) + "," + str(prediction[0][1])
                content += line2 + "\n"
                content += hashlib.md5(line2.encode()).hexdigest()
                write_success = False
                error_count = 0
                socketClient.emit("request_features")
                socketClient.emit("request_prediction")
                while(write_success == False and error_count<20):
                    try:
                        fp = open("box_prediction.csv", "w")
                        fp.write(content)
                        write_success = True
                        fp.close()
                    except:
                        error_count += 1
                        print("failed writing to file. ",sys.exc_info()[0],". tries: "+str(error_count))
                        sleep(0.25)
        # sleep(0.01)
    
def runSocket():
    socketio.run(app)

threading.Thread(target=runSocket).start()

threading.Thread(target=filescanner).start()


