from flask import *
from flask_socketio import SocketIO
from datetime import *
from cryptography.fernet import Fernet
import os
import random
import hashlib
import pytds
import time as timeimp
import threading

app = Flask(__name__)

paramFile = './config.txt'
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app)

encryption_key = Fernet.generate_key()
fernet = Fernet(encryption_key)

def readParams(filename):
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f]
    except FileNotFoundError:
        dprint(f"Error: File '{filename}' not found")
        return []

gotParams = readParams(paramFile)
serverName = gotParams[0][3:]
serverUser = gotParams[1]
serverPass = gotParams[2]
eventFilename = gotParams[3]
debugMode = gotParams[4]

def dprint(text):
    if debugMode == 'debug':
        print(text)

def generateSHA256(text):
    return str(hashlib.sha256(text.encode()).hexdigest())

def grabTime(timeMinus = timedelta()):
    return str(datetime.now() - timeMinus).split('.')[0]

def checkTimeScope(dt, scope):
    start_time = time.fromisoformat(scope[0])
    end_time = time.fromisoformat(scope[1])
    
    check_time = dt.time()
    
    return start_time <= check_time <= end_time

def ensureLogin(session):
    try:
        loginInformation = decrypt(session.get('login'))
        
        loginKeyword = loginInformation[:5]
        loginPasskey = int(loginInformation[-8:])
        
        if loginKeyword == 'login':
            if loginPasskey > 9999999 and loginPasskey < 100000000:
                return True
            else:
                return False
        else:
            return False     
    except:
        return False
    
def encrypt(data):
    encrypted_data = str(fernet.encrypt(data.encode()).decode('ascii'))
    return encrypted_data

def decrypt(encrypted_data):
    decrypted_data = fernet.decrypt(encrypted_data).decode()
    return decrypted_data

def grabNewDatabaseInfo(grabTime):
    with pytds.connect(serverName, 'PWNT', serverUser, serverPass) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT LOGDEVDESCRP, EVNT_DESCRP, EVNT_DAT FROM dbo.EV_LOG WHERE EVNT_DAT > '{grabTime}';")
            result = cur.fetchall()
            
    return result

def parseEvents(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            parsed_paths = [line.strip().split('/') for line in file if line.strip()]       
            return parsed_paths    
    except :
        return []

def loopGrab():
    timeimp.sleep(5)
    while True:
        try:
            dprint('grab')
            previousTime = grabTime(timedelta(seconds=5))
            sectorEvents = grabNewDatabaseInfo(previousTime)
            eventSearch = parseEvents(eventFilename)

            for curEvent in sectorEvents:
                for searchEvent in eventSearch:
                    dprint(curEvent)
                    dprint(searchEvent)
                    
                    searchEventLocation = searchEvent[0]
                    curEventLocation = curEvent[0]
                    curEventEvent = curEvent[1]
                    searchEventEvent = searchEvent[1]
                    
                    if searchEvent[0].startswith("\ufeff"):
                        searchEventLocation = searchEvent[0][1:]
                    if curEvent[0].startswith("\ufeff"):
                        curEventLocation = curEvent[0][6:]
                    if curEvent[1].startswith("\ufeff"):
                        curEventEvent = curEvent[1][6:]
                    if searchEvent[1].startswith("\ufeff"):
                        searchEventEvent = searchEvent[1][6:]

                    dprint(searchEventLocation)
                    dprint(curEventLocation)
                    dprint(curEventEvent)
                    dprint(searchEventEvent)
                        
                    if checkTimeScope(curEvent[2], [searchEvent[2], searchEvent[3]]):
                        dprint(1)
                        if curEventLocation == searchEventLocation:
                            dprint(2)
                            if curEventEvent == searchEventEvent:
                                dprint(3)
                                dprint('report')
                                dprint({'eventLocation': curEvent[0], 'eventName': curEvent[1]})
                                socketio.emit('eventMatchAlert', {'eventLocation': curEvent[0], 'eventName': curEvent[1], 'eventTime': str(curEvent[2])})
        except:
            pass
        timeimp.sleep(5)

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if ensureLogin(session):
        return render_template('control.html')
    else:
        return render_template('signin.html')
    
@app.route('/alert')
def alert():
    if ensureLogin(session):
        alertLocation = request.args.get('alertLocation') 
        alertEvent = request.args.get('alertEvent')
        alertTime = request.args.get('alertTime')
        
        return render_template('alert.html', alertLocation = alertLocation, alertEvent = alertEvent, alertTime = alertTime)
    else:
        return redirect('/')

@app.route('/loginCallback', methods=['POST'])
def loginCallback():
        password = request.form['password']
        
        file = open("passwordhash.txt", "r")

        for line in file:
            correctPasswordHash = line.strip()

        file.close()
        
        userPasswordHash = generateSHA256(password)
        if correctPasswordHash == userPasswordHash:
            sessionKey = 'login' + str(random.randint(10000000, 99999999))
            session['login'] = encrypt(sessionKey)
            
            return redirect('/control')
        
        else:
            return render_template('passwordError.html')
    
@app.route('/control')
def control():
    if ensureLogin(session):
        return render_template('control.html')
    else:
        return redirect('/')
    
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if ensureLogin(session):
        if not os.path.exists(eventFilename):
            with open(eventFilename, 'w', encoding='utf-8') as f:
                f.write('')
        
        if request.method == 'POST':
            try:
                content = request.form.get('content', '')
                content = content.replace('\r\n', '\n')
                with open(eventFilename, 'w', encoding='utf-8') as f:
                    f.write(content)
                return render_template('settingsSaved.html', content=content)
            except Exception as e:
                return render_template('settings.html', content='', error=f'保存设置时出现问题: {str(e)}')
        
        try:
            with open(eventFilename, 'r', encoding='utf-8') as f:
                content = f.read()
            return render_template('settings.html', content=content, error='')
        except Exception as e:
            return render_template('settings.html', content='', error=f'读取文件时出现问题: {str(e)}')
    else:
        return redirect('/')
    
@app.route('/signout')
def signout():
    session.clear()
    
    return redirect('/')

def runAppServer():
    socketio.run(app, host='0.0.0.0', port=8080)
    
loopGrabThread = threading.Thread(target=loopGrab)
runAppThread = threading.Thread(target=runAppServer)
                
if __name__ == '__main__':
    loopGrabThread.start()
    runAppThread.start()

    loopGrabThread.join()
    runAppThread.join()