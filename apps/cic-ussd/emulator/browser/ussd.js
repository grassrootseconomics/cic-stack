var ssl = false;
var host = 'localhost';
var port = 9000;
var proto = 'https';
var host = 'staging.sarafu.network';
var user = 'foo';
var pass = 'bar';
var path = '/';
var serviceCode = '*483*46#';

// cheekily stolen from https://www.tutorialspoint.com/how-to-create-guid-uuid-in-javascript
function createUUID() {
   return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
   });
}

var uuid = createUUID();
var phone = undefined;

function send(s) {
	document.getElementById('send_input').innerHTML = 'connecting...';
	document.getElementById('input').disabled = true;
	document.getElementById('send_input').disabled = true;
	var xhr = new XMLHttpRequest();
	xhr.responseType = 'text';
	const current_user = document.getElementById('user').value;
	const current_pass = document.getElementById('pass').value;
	const current_host = document.getElementById('host').value;
	const current_port = document.getElementById('port').value;
	let current_scheme = 'http';
	if (document.getElementById('ssl').checked) {
		current_scheme += 's';
	}
	const url = current_scheme + '://' + current_host + ':' + current_port + '?username=' + current_user + '&password=' + current_pass
	console.debug('connecting to', url);
	xhr.open('POST', url, true);
	xhr.setRequestHeader('Content-Type', 'application/json');
	data = {
		sessionId: uuid,
		serviceCode: serviceCode,
		phoneNumber: phone,
		text: s,
	}
	xhr.onreadystatechange = () => {
		if (xhr.readyState == 2) {
			document.getElementById('send_input').innerHTML = 'connected...';
		}
	};
	xhr.onprogress = () => {
		document.getElementById('send_input').innerHTML = 'recieving...';
	};
	xhr.onload = () => {
		document.getElementById('send_input').innerHTML = 'processing...';
		if (xhr.status == '200') {
			process(xhr.responseText);
			return;
		}
		var t = document.getElementById('monitor');
		t.value = t.value + '!!! ' + xhr.status + ' ' + xhr.statusText + '\n';
		t.value = t.value + '!!! ' + xhr.responseText + '\n';
		t.value = t.value + '----- SESSION ' + uuid_fingerprint() + ' ERRORED FOR ' + phone + ' -----\n';
		reset();
	};
	xhr.send(JSON.stringify(data));
}

function reset() {
	document.getElementById('input').value = '';
	document.getElementById('session').style.display = 'none';
	document.getElementById('login').style.display = 'block';
}

function process(s) {
	var t = document.getElementById('monitor');
	t.value = t.value + s.substring(4) + '\n';
	document.getElementById('input').value = '';
	if (s.substring(0, 3) == 'END') {
		t.value = t.value + '----- SESSION ' + uuid_fingerprint() + ' ENDED FOR ' + phone + ' -----\n';
		reset();
		return;
	}
	document.getElementById('input').value = '';
	document.getElementById('send_input').innerHTML = 'send as ' + phone;
	document.getElementById('input').disabled = false;
	document.getElementById('send_input').disabled = false;
	document.getElementById('input').focus();
	t.scrollTop = t.scrollHeight;
}

function uuid_fingerprint() {
	return uuid.substring(0, 8);
}

function setPhone(s) {
	uuid = createUUID(); // global
	phone = s; // global
	var t = document.getElementById('monitor');
	t.value = t.value + '----- SESSION ' + uuid_fingerprint() + ' STARTED FOR ' + phone + ' -----\n';
	var v = document.getElementById('send_input').innerHTML;
	document.getElementById('send_input').innerHTML = v + ' ' + phone;
	document.getElementById('login').style.display = 'none';
	document.getElementById('session').style.display = 'block';
	send(serviceCode);
}


function abort() {
	var t = document.getElementById('monitor');
	t.value = t.value + '----- SESSION ' + uuid_fingerprint() + ' ABORTED FOR ' + phone + ' -----\n';
	reset();
	return;
}

window.addEventListener('load', () => {
	document.getElementById('user').value = user;
	document.getElementById('pass').value = pass;
	document.getElementById('host').value = host;
	document.getElementById('port').value = port;
	document.getElementById('phone').addEventListener('keyup', (e) => {
		if (e.keyCode == '13') {
			document.getElementById('input').value = '';
			document.getElementById('input').focus();
			setPhone(document.getElementById('phone').value);
		}
	});
	document.getElementById('input').addEventListener('keyup', (e) => {
		if (e.keyCode == '13') {
			send(document.getElementById('input').value);
		}
	});
	document.getElementById('phone').focus();
});
