import socket
import logging
import sys
import os
PORT=11199
#1mb buffer should be big enough for most audio chunks
RECV_BUFFER_SIZE=4096
# default mic is index 1
SELECTED_MIC_IDX = 1
# sample rate that works with whisper / most voice recognizers
RATE = 16000
# are we collecting logs?
LOGGING = True
def start_logging(LOGGING) :
    if (LOGGING) :
        if (not os.path.isdir("logs")) : os.mkdir("logs")
        logging.basicConfig(filename="logs/log.txt", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        

# what word triggers out agent to act?
def get_trigger_word() :
    try :
        trigger_word = open("trigger_word.txt", "rt").readline()
    except OSError :
        # default trigger word creates a file we can later edit
        trigger_word = "jarvis"
        trigger_word_file = open("trigger_word.txt", "xt")
        trigger_word_file.write(trigger_word)
        trigger_word_file.close()
    return trigger_word


def get_server_address() :
    if (len(sys.argv) == 1) :
        if (LOGGING) : 
            logging.error("Must specify a server hostname/ip as the first argument, e.g start_controller.py 192.168.1.24")
            raise Exception("Must specify a server hostname/ip as the first argument, e.g start_controller.py 192.168.1.24")
    else :
        return sys.argv[1]
    

def gui() :
    # command to send the selected microphone to the other threads
    def select() :
        global SELECTED_MIC_IDX
        # returns a list but only 1 selection is allowed
        SELECTED_MIC_IDX = lb.curselection()[0]
        # close the gui
        root.destroy()
    
    import tkinter as tk
    import speech_recognition as sr
    mic_list = sr.Microphone.list_microphone_names()

    # TODO fix gui so the selection window is a better size and more flexible
    # window geometry
    window_height = 360
    # golden ratio
    window_width = int(window_height*0.618)
    root = tk.Tk()
    root.title("Select a Microphone")
    root.geometry(f"{window_width}x{window_height}")
    # create a listbox to display the microphones
    lb = tk.Listbox(root, selectmode="single", height=20, width=window_width)
    # create scrollbars to navigate the listbox
    x_scroll = tk.Scrollbar(root, orient="horizontal", command=lb.xview)
    x_scroll.pack(side="bottom", fill="both")
    y_scroll = tk.Scrollbar(root, orient="vertical", command=lb.yview)
    y_scroll.pack(side="right", fill="both")
    # set the scrollbars to the listbox
    lb.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
    # populating the listbox
    for mic in mic_list : 
        lb.insert("end", mic)
    # create a button to send the selected mic to the listening thread
    select_button = tk.Button(root, text="Select", width=window_width, anchor="s", command=select)
    lb.pack()
    select_button.pack()
    root.mainloop()


def connect_to_server(hostname, port) :
    server_socket = None
    for targets in socket.getaddrinfo(hostname, port,socket.AF_UNSPEC,socket.SOCK_STREAM) :
        af, socktype, proto, canonname, socket_address = targets
        try:
            server_socket = socket.socket(af, socktype, proto)
        except OSError as msg:
            server_socket = None
            continue
        # Test the connection, make sure its still alive before sending
        try:
            server_socket.connect(socket_address)
        except OSError as msg:
            server_socket.close()
            server_socket = None
            continue
        break
    if server_socket is None:
        if (LOGGING) : logging.error("Failed to open socket")
        raise Exception(f"Failed to connect to server at {hostname}:{PORT}")
    return  server_socket, socket_address


def get_server_data(server_connection, socket_address) :
    # Need to block for the first packet then recieve the rest of the batch
    # TODO recieve this data in another thread so we can go back to collecting audio faster
    transcribed_text_data = b""
    # If the transcription is unrepsonsive after 60 seconds the server is probably waiting on us or broken
    server_connection.settimeout(60.0)
    try :
        data_packet = server_connection.recv(RECV_BUFFER_SIZE)
        server_connection.settimeout(0.5)
        transcribed_text_data += data_packet
    except TimeoutError :
        if (LOGGING) : logging.warning("Failed to get packet from server, dropping")
    # Then wait up to 0.5 seconds for each packet to make sure we collect all the data
    while True :
        try :
            data_packet = server_connection.recv(RECV_BUFFER_SIZE)
        except BlockingIOError :
            break
        except TimeoutError :
            break
        if (data_packet == b"") :
            transcribed_text_data = None
            break
        else :
            transcribed_text_data += data_packet
    server_connection.settimeout(None)
    server_connection.setblocking(True)
    if transcribed_text_data == None : 
        logging.error(f"Connection closed by server {socket_address}:{PORT}, shutting down")
        return None
    try :
        transcribed_text = transcribed_text_data.decode()
        return transcribed_text
    except EOFError :
        if (LOGGING) : logging.error(f"Connection closed by server {socket_address}:{PORT}, shutting down")
        return None


def transmit_data(server_connection, socket_address, data) :
    import sys
    if (LOGGING) : logging.debug(f"Sending Packet of Size: {sys.getsizeof(data)} bytes -> {socket_address}")
    server_connection.sendall(data)


def convert_to_float_array(wavdata) :
    import numpy as np
    intarray = np.frombuffer(wavdata, dtype=np.int16, count=int(len(wavdata)/2), offset=0)
    # This normalizes our audio data, and is why we prefer models with higher precision
    floatarray = intarray.astype(np.float32, order="C") / 32768.0
    return floatarray


def listen(server_connection : socket.socket, socket_address) :
    import speech_recognition as sr
    import numpy as np
    # Init and config the speech recognition
    data = sr.AudioData
    recog = sr.Recognizer()
    # Volume above 500 to trigger voice commands

    recog.energy_threshold = 50
    # Half second pause to end a voice line
    recog.pause_threshold = 0.75
    # Configure volume adjustment
    recog.dynamic_energy_ratio = 3
    recog.dynamic_energy_adjustment_damping = 0.9

    # get the previsouly selected mic from the gui and stream audio
    mic = sr.Microphone(device_index=SELECTED_MIC_IDX, sample_rate=RATE)
    with mic as source:
        recog.adjust_for_ambient_noise(source=mic, duration=1)

        if (LOGGING) : logging.debug(f"Listening with sensitivity {recog.energy_threshold}")

        # TODO handle timeout after 5 minutes of silence by offloading the model to conserve resources
        data = recog.listen(source, phrase_time_limit=15, timeout=None)
        # Convert our audio to an array of floats for the model
        wavdata = data.get_wav_data(convert_rate=RATE)
        fwavdata = convert_to_float_array(wavdata)
        fwavdata_string = np.array2string(fwavdata, threshold=(len(fwavdata)+1), precision=32, separator=",")
        fwavdata_packet = fwavdata_string.encode()

        transmit_data(server_connection, socket_address, fwavdata_packet)
        text = get_server_data(server_connection, socket_address)
        return text
    

def parse_text(text: str, trigger_word) : 
    if (LOGGING) : logging.debug(f"Detected speech: {text}")
    import actions
    try :
        if (text.__contains__(trigger_word)) :
            actions.parse_for_triggers(text)
    except Exception as e :
        if (LOGGING) : logging.debug(f"{e}")
        return None

def main() :
    start_logging(LOGGING)
    trigger_word = get_trigger_word()
    server_address = get_server_address()
    # Launch the GUI for the user to select their input device
    gui()
    # Start listening on that device
    server_connection, socket_address = connect_to_server(server_address, PORT)
    with server_connection:
        # Shutdown the program if told to stop
        transcribed_speech = ""
        while (not transcribed_speech.__contains__("stop")) :
            transcribed_speech = listen(server_connection, socket_address[0])
            if (transcribed_speech == None) :
                break
            parse_text(transcribed_speech, trigger_word)

if __name__ == "__main__" :
    main()