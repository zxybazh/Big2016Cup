#!flask/bin/python
from flask import Flask, jsonify, request
import urllib2, json, re

dEbUg = True

app = Flask(__name__)

def right():
	global dEbUg
	# if dEbUg: print 'result', 'yes'
	return jsonify({'result': 'yes'})

def wrong():
	global dEbUg
	# if dEbUg: print 'result', 'no'
	return jsonify({'result': 'no'})

def error(e):
	global dEbUg
	# if dEbUg: print 'error', e
	return jsonify({'error' : e})

def MAG(data):
	req = urllib2.Request('http://magraph.cloudapp.net/')
	req.add_header('Content-Type', 'application/json')
	return json.load(urllib2.urlopen(req, json.dumps(data)))

def GetAuthorName(AuthorID):
	data = {
		"path": "/author",
		"author": {
		"type": "Author",
		"id": [AuthorID],
		"select":[ "Name" ]}
	}
	response = MAG(data)
	return response[0][0]['Name']

def GetAuthorAffiliations(AuthorID):
	data = {
		"path": "/author/*/affiliation",
		"author": {
			"type": "Author",
			"id": [AuthorID],
        },
		"affiliation": {
			"type": "Affiliation",
			"select":[ "Name" ]
		}
	}
	response = MAG(data)
	affiliations = []
	for cell in response:
		affiliations.append(cell[1]['Name'])
	return affiliations

def GetPublicationAuthorPairs(PaperID):
	data = {
		"path": "/paper/*/author",
		"paper": {
			"type": "Paper",
			"id" : [PaperID],
			"select": [ "OriginalPaperTitle" ]
		},
		"author": {
			"type": "Author",
			"select":[ "Name" ]
		}
	}
	return MAG(data)

def editdistance(s, t):
	if (abbr(s) or abbr(t)) and s[0] == t[0]:
		return 0
	m = len(s) + 1
	n = len(t) + 1
	opt = {}
	for i in xrange(m): opt[i, 0] = i
	for j in xrange(n): opt[0, j] = j
	for i in xrange(1, m):
		for j in xrange(1, n):
			cost = 0 if s[i-1] == t[j-1] else 1
			opt[i, j] = min(opt[i, j-1] + 1, opt[i-1, j] + 1, opt[i-1, j-1] + cost)
	return opt[i, j]

def abbr(x):
	return len(x) == 1

def VagueMatch(s, t):
	SplitString = "##############################"
	infinity = 1e9
	a = filter(lambda x:len(x) > 0, re.compile("[\W]").split(s))
	b = filter(lambda x:len(x) > 0, re.compile("[\W]").split(t))
	if (len(a) == len(b)):
		for i in xrange(len(a)):
			if (abbr(a[i]) or abbr(b[i])) and a[i][0] == b[i][0]:
				a[i] = a[i][0]
				b[i] = b[i][0]
		return editdistance(SplitString.join(a), SplitString.join(b)) < 3
	else:
		if (len(a) > len(b)): a, b = b, a
		m = len(a) + 1
		n = len(b) + 1
		opt = {}
		for i in xrange(m): opt[i, 0] = i
		for j in xrange(n): opt[0, j] = 0
		for i in xrange(1, m):
			for j in xrange(i, n):
				cost = 0 if editdistance(a[i - 1], b[j - 1]) < 2 else 1
				opt[i, j] = infinity
				for k in xrange(i-1, j):
					opt[i, j] = min(opt[i, j], opt[i - 1, k] + cost)
		ans = infinity
		for t in xrange(m-1, n):
			ans = min(opt[m-1, t], ans)
		return ans < 2

def check(AuthorID, PaperID):
	global dEbUg
	AuthorName = GetAuthorName(AuthorID)
	AuthorAffiliations = GetAuthorAffiliations(AuthorID)

	if dEbUg:
		print "AuthorID	:", AuthorID
		print "AuthorName	:", AuthorName
		print "AuthorAffiliations :"
		for AuthorAffiliation in AuthorAffiliations:
			print AuthorAffiliation

	PublicationAuthorPairs = GetPublicationAuthorPairs(PaperID)
	# print json.dumps(PublicationAuthorPair, indent=4, sort_keys=True)
	if dEbUg: print "Checking Authors..."
	for PublicationAuthorPair in PublicationAuthorPairs:
		if dEbUg: print "Checking Author", PublicationAuthorPair[1]['Name']
		if VagueMatch(PublicationAuthorPair[1]['Name'], AuthorName):
			if dEbUg: print "Name Matched :)"
			Flag = False
			if AuthorAffiliations == []:
				Flag = True
				print "No Affiliation information >_<"
			CandidateAuthorAffiliations = GetAuthorAffiliations(PublicationAuthorPair[1]['CellID'])
			for CandidateAuthorAffiliation in CandidateAuthorAffiliations:
				for AuthorAffiliation in AuthorAffiliations:
					if (CandidateAuthorAffiliation == AuthorAffiliation or CandidateAuthorAffiliation.find(AuthorAffiliation) == 0 or AuthorAffiliation.find(CandidateAuthorAffiliation) == 0):
						if dEbUg: print "Affiliation Matched :)"
						Flag = True
						break
				if (Flag): break
			if Flag:
				return True
			else:
				if dEbUg:
					print "Affiliation Mismatched :("
					# print AuthorAffiliation
					# print CandidateAuthorAffiliation
	return False

@app.route('/big2016/', methods=['POST'])
def create_task():
	global dEbUg
	if not request.json:
		return error("json format error")
	else:
		data = request.json

	if dEbUg:
		print "==============================================="
		print data

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
			if dEbUg: print "==============================================="
			return right()
		else:
			if dEbUg: print "==============================================="
			return wrong()
	else:
		return error("json content error")

if __name__ == '__main__':
	app.run(host = "0.0.0.0", port = 23201, debug=True)
