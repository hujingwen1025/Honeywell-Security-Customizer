async function mainProcess() {
    window.alarmToggled = true;

    const socket = io.connect();
	const alarmToggle = document.getElementById('armAlarm');
	const logDiv = document.getElementById('logDiv');
	const clearLog = document.getElementById('logClear');
	
	if (localStorage.getItem("logHTML") != undefined) {
		logDiv.innerHTML = localStorage.getItem("logHTML");
	} else {
		localStorage.setItem("logHTML", '');
	}

    socket.on('eventMatchAlert', function(data) {
		if (window.alarmToggled) {
			window.open(`/alert?alertLocation=${data['eventLocation']}&alertEvent=${data['eventName']}&alertTime=${data['eventTime']}`, "", "width=650,height=200");
			var newLog = document.createElement("p");
			newLog.innerText = `${data['eventTime']} | ${data['eventLocation']} - ${data['eventName']}`
			logDiv.appendChild(newLog);
			localStorage.setItem("logHTML", logDiv.innerHTML)
		} else {
			console.log('Alarm silenced by toggle');
			var newLog = document.createElement("p");
			newLog.innerText = `${data['eventTime']} | ${data['eventLocation']} - ${data['eventName']} - 无警报`
			logDiv.appendChild(newLog);
			localStorage.setItem("logHTML", logDiv.innerHTML)
		}
	});
	
	alarmToggle.onclick = function () {
		if (! window.alarmToggled) {
			window.alarmToggled = true;
			alarmToggle.classList.remove("alarmUnarmed");
			alarmToggle.classList.add("alarmArmed");
		} else {
			window.alarmToggled = false;
			alarmToggle.classList.remove("alarmArmed");
			alarmToggle.classList.add("alarmUnarmed");
		}
	}
	
	clearLog.onclick = function () {
		logDiv.innerHTML = '';
		localStorage.setItem("logHTML", logDiv.innerHTML);
	}
}

document.addEventListener('DOMContentLoaded', () => {
    mainProcess();
});