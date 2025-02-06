def get_weather(text: str) :
    get_weather_triggers = ["weather", "forecast"]
    for trigger_word in get_weather_triggers : 
        if (text.__contains__(trigger_word)) : 
            from requests import get
            from pyowm import OWM
            import datetime
            import geocoder
            import tts
            VERIFOWM = OWM(api_key="xxxxxxxxxxxxxxxxxxxxxxxx")

            # get out IP address
            ip = get('https://api.ipify.org').content.decode('utf8')
            # trace our current location
            ip_location = geocoder.ip(ip)
            # Init weather manager
            mgr = VERIFOWM.weather_manager()
            currWeather = mgr.weather_at_coords(lat = ip_location.lat, lon=ip_location.lng).weather
            oc = mgr.one_call(lat = ip_location.lat, lon=ip_location.lng)                                            
            forecast = oc.forecast_daily

            # Weekday array and dictionary
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

            # map each day of the week with its place in the array
            weekdayDict = {0:"monday", "monday":0, 
                        1:"tuesday", "tuesday":1, 
                        2:"wednesday", "wednesday":2,
                        3:"thursday", "thursday":3,
                        4:"friday", "friday":4,
                        5:"saturday", "saturday":5,
                        6:"sunday", "sunday":6}
            reqDay = ""
            reqDayNum = -1

            # Set requested day
            for d in days:
                if text.__contains__(d):
                    reqDay = d
                    reqDayNum = weekdayDict[reqDay]
                    break

            
            # If requested retreive tomorrows tempurature and conditions
            if text.__contains__("tomorrow"):
                tomTemp = str(int(forecast[1].temperature("fahrenheit")["day"]))
                tomTempMax = str(int(forecast[1].temperature("fahrenheit")["max"]))
                tomTempMin = str(int(forecast[1].temperature("fahrenheit")["min"]))

                avgWeather = "the temperature tomorrow is" + tomTemp  + "degrees" + "and the conditions are" + forecast[1].detailed_status
                extrWeather = " the highest temperature for tomorrow is" + tomTempMax + "degrees" + "and the lowest temperature is" + tomTempMin + "degrees"

                tts.speak(avgWeather + extrWeather)

            # If a weekday is requested get tempurature and conditions for that day
            # if multiple days are requested we can get results for all of them
            if reqDayNum != -1:
                for fc in forecast:
                    if datetime.datetime.weekday(fc.reference_time("date")) == int(reqDayNum):
                        dayTemp = str(int(fc.temperature("fahrenheit")["day"]))                     
                        dayTempMax = str(int(fc.temperature("fahrenheit")["max"]))
                        dayTempMin = str(int(fc.temperature("fahrenheit")["min"]))

                        avgWeather = "the temperature " + weekdayDict[reqDayNum] + " will be " + dayTemp + "degrees" + "and the conditions will be " + fc.detailed_status
                        extrWeather = " the highest temperature " + weekdayDict[reqDayNum] + " will be " + dayTempMax + "degrees" + "and the lowest temperature will be " + dayTempMin + "degrees"

                        tts.speak(avgWeather + extrWeather)
                        break

            else :
                # Get todays tempuratures and conditions in readable string format
                currTemp = str(int(currWeather.temperature("fahrenheit")["temp"]))
                todayTempMax = str(int(forecast[0].temperature("fahrenheit")["max"]))
                todayTempMin = str(int(forecast[0].temperature("fahrenheit")["min"]))

                currentWeather = "the current temperature is" + currTemp + "degrees" + "and the conditions are" + currWeather.detailed_status
                todayExtremes = " the highest temperature for today is" + todayTempMax  + "degrees" + "and the lowest temperature is" + todayTempMin  + "degrees"

                tts.speak(currentWeather + todayExtremes)

def set_timer(text: str) :
    set_timer_triggers = ["alarm", "timer"]
    for trigger_word in set_timer_triggers : 
        if (text.__contains__(trigger_word)) :
            import playsound
            from tkinter import ttk
            import tkinter as tk
            import time
            import tts
            # To cancle timers uhhhhh TODO

            # Split the text around whitespace and dashes
            dur = 0
            rawdur = 0
            text = text.split()
            for w in text :
                if w.__contains__("-") :
                    t = w.split("-")
                    t.reverse()
                    for j in t :
                        text.insert(0, j)
                    break

            # Check for a numbers in the text then convert them to seconds
            for word in text :
                if str.isdigit(word) :
                    rawdur = int(word)
                if word == "one" :
                    rawdur = 1
                elif word.__contains__("half"):
                    dur = rawdur + 0.5
                elif word.__contains__("hour") :
                    dur = dur + (rawdur * 60 * 60)
                elif word.__contains__("minute") :
                    dur = dur + (rawdur * 60)
                    
            # Let the user know the request was successful
            tts.speak("timer set")

            # Wait for the correct time
            setTime = int(time.time())
            while (setTime + dur) != int(time.time()) :
                time.sleep(1)

            # Start playing the timer and create the window
            # GUI needs some work and kills main thread otherwise works
            playsound("timernoise.mp3")
            root = tk.Tk()
            root.title("Ring Ring...")
            root.iconbitmap("voice_control.ico")
            #root.geometry("48x24")
            mainframe = ttk.Frame(root, padding="48 24 48 24", width=48, height=24)
            mainframe.grid(column=2, row=2)
            ttk.Button(mainframe, text = "End Timer", width=36, command=root.destroy).grid(column=0, row=0)
            root.mainloop()


def run_program(text: str) :
    run_program_triggers = ["open", "run", "launch"]
    for trigger_word in run_program_triggers : 
        if (text.__contains__(trigger_word)) :
            print("runing app")
            import filefinder
            import time
            import json
            import tts
            import os
            # if our file paths are older than an hour (or nonexistent) refresh them
            if (not os.path.exists("file_paths.json") or ((os.path.getmtime("file_paths.json") - time.time()) > 3600)) :
                user_dir = os.path.expanduser("~")
                directories = [user_dir,user_dir+"/Appdata/Roaming/Microsoft/Windows/Start Menu/Programs","C:/ProgramData/Microsoft/Windows/Start Menu/Programs"]
                filefinder.update_list(4,directories,[".exe",".lnk",".url"],saveas="file_paths")

            path_file = open("file_paths.json", "r")
            apps = json.load(path_file)
            file_names = apps.keys()
            # take the ending of the speech blurb as the app to be opened
            request = text.split(trigger_word, 1)[1]

            from fuzzywuzzy import process
            closestGuess = process.extractOne(score_cutoff=90, query=request, choices=[*file_names])
            if closestGuess != None:
                confidence = closestGuess[1]
                closestGuess=closestGuess[0]
                if (confidence>90) :
                    os.startfile(apps.get(closestGuess))
                    tts.speak("launching")
            else :
                tts.speak("not found")
            break


def rescan(text: str) :
    rescan_triggers = ["rescan"]
    for trigger_word in rescan_triggers : 
        if (text.__contains__(trigger_word)) :
            import filefinder
            import os
            user_dir = os.path.expanduser("~")
            print(user_dir)
            directories = [user_dir,user_dir+"/Appdata/Roaming/Microsoft/Windows/Start Menu/Programs","C:/ProgramData/Microsoft/Windows/Start Menu/Programs"]
            filefinder.update_list(4,directories,[".exe",".lnk",".url"],saveas="file_paths")


def web_search(text: str) :
    web_search_triggers = ["search"]
    for trigger_word in web_search_triggers : 
        if (text.__contains__(trigger_word)) :
            import webbrowser
            # Create search string from split transcription
            request = text.split(trigger_word, 1)[1]
            # Launch google search on default browser
            webbrowser.get().open("http://www.google.com/search?hl=eng&q=" + request + "&btnG=Google+\Search")
            break


def parse_for_triggers(text: str) :
    get_weather(text)
    set_timer(text)
    rescan(text)
    run_program(text)
    web_search(text)