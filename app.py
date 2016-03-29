#!flask/bin/python
from flask import Flask, jsonify, request
import urllib2, json
dEbUg = True

app = Flask(__name__)

def right():
	global dEbUg
	if dEbUg: print 'result', 'yes'
	return jsonify({'result': 'yes'})

def wrong():
	global dEbUg
	if dEbUg: print 'result', 'no'
	return jsonify({'result': 'no'})

def error(e):
	global dEbUg
	if dEbUg: print 'error', e
	return jsonify({'error' : e})

def check(AuthorID, PaperID):
	global dEbUg
    data = {
        "path": "/author",
        "author": {
        "type": "Author",
        "id": [AuthorID],
        "select":[
            "Name"
        ]}
    }
    req = urllib2.Request('http://magraph.cloudapp.net/')
    req.add_header('Content-Type', 'application/json')
    response = json.load(urllib2.urlopen(req, json.dumps(data)))
    AuthorName = response[0][0]['Name']
    data = {
        "path": "/paper/AuthorIDs/author",
        "paper": {
            "type": "Paper",
            "id" : [PaperID],
            "select": [
                "OriginalPaperTitle"
            ]
        },
        "author": {
            "type": "Author",
            "select":[
                "Name"
            ]
        }
    }
    req = urllib2.Request('http://magraph.cloudapp.net/')
    req.add_header('Content-Type', 'application/json')
    response = json.load(urllib2.urlopen(req, json.dumps(data)))
    if dEbUg: print json.dumps(response, indent=4, sort_keys=True)
    for AApair in response:
        if AApair[1]['Name'] == AuthorName:
            return True
    return False

@app.route('/big2016/', methods=['POST'])
def create_task():
	global dEbUg
	if not request.json:
		return error("json format error")
	else:
		data = request.json

	if dEbUg: print data

	'''
	try:
		temp = json.loads(data)
	except Exception,e:
		return error("json format error")
	'''

	if ('paper_id' in data and 'author_id' in data):
		AuthorID = data['author_id']
		PaperID = data['paper_id']
		if check(AuthorID, PaperID):
			return right()
		else:
			return wrong()
	else:
		return error("json content error")

if __name__ == '__main__':
	app.run(host = "0.0.0.0", port = 23201, debug=True)