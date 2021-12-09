# import the necessary packages
from imutils.video import VideoStream
from pyzbar import pyzbar
import argparse
import datetime
import imutils
import time
import cv2
import peopleInRoom
import seeed_dht
from grove.display import JHD1802
import UltrasonicSensor
# from imutils.video import VideoStream
from flask import Response
from flask import request
from flask import Flask
from flask import render_template
import threading
# import argparse
# import datetime
# import imutils
# import time
# import cv2
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO
import base64

outputFrame = None

# initialize a flask object
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
socketio = SocketIO(app, cors_allowed_origins="*")



def qrDectector():
 
    # construct the argument parser and parse the arguments
    print("QR detector started")
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", type=str, default="barcodes.csv",
        help="path to output CSV file containing barcodes")
    args = vars(ap.parse_args())
    
    ### From there, let’s initialize our video stream and open our CSV file:
    # initialize the video stream and allow the camera sensor to warm up
    print("[INFO] starting video stream...")

    vs = VideoStream(src=0).start()                 
    time.sleep(2.0)

    qrFlag = False
    legitFlag = False
     
    # open the output CSV file for writing and initialize the set of
    # barcodes found thus far
    csv = open("users.csv", "r+")
    found = set()
    
    lcd = JHD1802()
    lcd.setCursor(0, 0)
    print(csv)
     
    start = time.time()
    #print("start: " , start)
    
    ### Let’s begin capturing + processing frames:
    # loop over the frames from the video stream
    try:
        while True:
            # grab the frame from the threaded video stream and resize it to
            # have a maximum width of 400 pixels
            frame = vs.read()
            frame = imutils.resize(frame, width=400)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
            # find the barcodes in the frame and decode each of the barcodes
            barcodes = pyzbar.decode(frame)

        ### Let’s proceed to loop over the detected barcodes
        # loop over the detected barcodes
            for barcode in barcodes:
                # extract the bounding box location of the barcode and draw
                # the bounding box surrounding the barcode on the image
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        
                # the barcode data is a bytes object so if we want to draw it
                # on our output image we need to convert it to a string first
                barcodeData = barcode.data.decode("utf-8")
                barcodeType = barcode.type
        
                # draw the barcode data and barcode type on the image
                text = "{} ({})".format(barcodeData, barcodeType)
                cv2.putText(frame, text, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
                # if the barcode text is currently not in our CSV file, write
                # the timestamp + barcode to disk and update the set
                
                #if 's3755614,Tran Kim Long,0797999956' in csv.read():
                if barcodeData in csv.read():
                    print("Users Get Successfully")
                    if peopleInRoom.pp < 2: # If QR Code is valid and there are still rooms for more
                        peopleInRoom.pp = peopleInRoom.pp + 1
                        lcd.setCursor(0,0)
                        lcd.write('Welcome to the')
                        lcd.setCursor(1,0)
                        lcd.write('room, bitches!')
                        UltrasonicSensor.smallBuzzing() # Buzz small and cool
                        print("Welcome!")
                        legitFlag = True
                        qrFlag = True
                    else:# Signal the room is currently full
                        lcd.setCursor(0,0)
                        lcd.write('Sorry, the room')
                        lcd.setCursor(1,0)
                        lcd.write('is full!')
                        print("Over 5 people in the room")
                        UltrasonicSensor.loudBuzzing() # Buzz loud and clear
                        time.sleep(4.5)
                        peopleInRoom.leavingNoQR = 0
                        qrFlag = True
                else: #If Invalid QR Code is scanned
                    """
                    csv.write("{}\n".format(barcodeData))
                    csv.flush()
                    found.add(barcodeData)
                    print("{}\n".format(barcodeData))
                        
                    """
                    UltrasonicSensor.smallBuzzing() # Buzz small and cool
                    lcd.setCursor(0, 0)
                    lcd.write('QR code is not')
                    lcd.setCursor(1, 0)
                    lcd.write('in the database')
                    print("QR code is not in the database")
                    time.sleep(4.5)
                    peopleInRoom.leavingNoQR = 0
                    qrFlag = True

                    # show the output frame
            cv2.imshow("Barcode Scanner", frame)
            key = cv2.waitKey(1) & 0xFF
            
            
            #print("timer: ", time.time() - start)
            (flag, encodedImage) = cv2.imencode(".jpg", frame)
                # if not flag:
                #     continue
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                bytearray(encodedImage) + b'\r\n')
            
            if (time.time() - start) > 10.0:
                peopleInRoom.leavingNoQR = 1
                cv2.destroyAllWindows()
                vs.stop()
                break
        
            if qrFlag is True:
                peopleInRoom.leavingDect = 0
                peopleInRoom.leavingNoQR = 0
                time.sleep(3.5)
                peopleInRoom.leavingNoQR = 0
                print("[INFO] cleaning up...")
                lcd.clear()
                lcd.setCursor(0,0)
                lcd.write('Please scan QR')
                # close the output CSV file do a bit of cleanup                
                csv.close()
                cv2.destroyAllWindows()
                vs.stop()
                break
                if legitFlag is True:
                    return ("LegitBarcode:{}:{}:\n".format(barcodeData,peopleInRoom.pp))
                else:
                    return ("{},{}\n".format(datetime.datetime.now(),barcodeData))
    finally:
        print('ended')
    return None

t = threading.Thread(target=qrDectector)
t.daemon = True
t.start()

def qrMain():
    t.join()
    print("Started thread")
    # start the flask app
    #app.run(host=args["ip"], port=args["port"], debug=True,
        # threaded=True, use_reloader=False)
    print("Started the server")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RunTimeError("TF is this sheet")
    func()

@app.route("/video_feed")
@cross_origin()
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(qrDectector(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/shutdown")
@cross_origin()
def shutdown():
    shutdown_server()
    return 'QR Camera Shutting Down...zZz'

def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock
    qrDectector()
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            # (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # # ensure the frame was successfully encoded
            # if not flag:
            # 	continue
   
   
            # frame = outputFrame
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # frame = cv2.GaussianBlur(frame, (7, 7), 0)
            # (flag, encodedImage) = cv2.imencode(".jpg", frame)
            # if not flag:
            #     continue
   
        # yield the output frame in the byte format
        # yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
        #     bytearray(encodedImage) + b'\r\n')



# if __name__ == '__main__':
    # construct the argument parser and parse command line arguments
    #ap = argparse.ArgumentParser()
    #ap.add_argument("-i", "--ip", type=str, required=True,
    #    help="ip address of the device")
    #ap.add_argument("-o", "--port", type=int, required=True,
   #     help="ephemeral port number of the server (1024 to 65535)")
  #  ap.add_argument("-f", "--frame-count", type=int, default=32,
 #       help="# of frames used to construct the background model")
#    args = vars(ap.parse_args())
    
    # start a thread that will perform motion detection
     # t = threading.Thread(target=detect_motion, args=(
        #args["frame_count"],))

    # print("Started the server")
    
    # t = threading.Thread(target=qrDectector)
    # t.daemon = True
    # t.start()
    
    # print("Started thread")
    
    # # start the flask app
    # #app.run(host=args["ip"], port=args["port"], debug=True,
    #     # threaded=True, use_reloader=False)

    # app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)
    
    # socketio.run(app, host='0.0.0.0', port=5000)
    
# release the video stream pointer
# vs.stop()

# py webstreaming.py  --ip 0.0.0.0 --port 5000
# py qrServiceTEST.py  --ip 0.0.0.0 --port 5000  
