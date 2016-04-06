#-*-coding:utf-8-*-
#!flask/bin/python
from flask import Flask, jsonify, request
import pandas as pd, csv, xgboost as xgb, numpy as np, \
	unicodedata, math, json, urllib2, re

dEbUg = True

app = Flask(__name__)

def right(): return jsonify({'result': 'yes'})
def wrong(): return jsonify({'result': 'no'})
def error(e): return jsonify({'error' : e})

def MAG(data):
	req = urllib2.Request('http://magraph.cloudapp.net/')
	req.add_header('Content-Type', 'application/json')
	return json.load(urllib2.urlopen(req, json.dumps(data)))

def GetAuthorName(AuthorID):
	data = {
		"path": "/author",
		"author": {
			"type": "Author",
			"id": [ AuthorID ],
			"select":[ "Name" ]
		}
	}
	response = MAG(data)
	if len(response) == 0: return None
	return response[0][0]['Name']

def GetOriginalPaperTitle(PaperID):
	data = {
		"path": "/paper",
		"paper": {
			"type": "Paper",
			"id": [ PaperID ],
			"select":[ "OriginalPaperTitle" ]
		}
	}
	response = MAG(data)
	if len(response) == 0: return None
	return response[0][0]['OriginalPaperTitle']

def GetNormalizedPaperTitle(PaperID):
	data = {
		"path": "/paper",
		"paper": {
			"type": "Paper",
			"id": [ PaperID ],
			"select":[ "NormalizedPaperTitle" ]
		}
	}
	response = MAG(data)
	if len(response) == 0: return None
	return response[0][0]['NormalizedPaperTitle']

def GetPublishConference(PaperID):
	data = {
		"path": "/paper/*/conferenceseries",
		"paper": {
			"type": "Paper",
			"id": [ PaperID ],
		},
		"conferenceseries": {
			"type": "ConferenceSeries",
			"select": [ "ShortName" ]
		}
	}
	response = MAG(data)
	if len(response) == 0: return None
	return int(response[0][1]['ShortName'])

def GetPublishYear(PaperID):
	data = {
		"path": "/paper",
		"paper": {
			"type": "Paper",
			"id": [ PaperID ],
			"select":[ "PublishYear" ]
		}
	}
	response = MAG(data)
	if len(response) == 0: return None
	return int(response[0][0]['PublishYear'])

def GetAuthorAffiliations(AuthorID):
	data = {
		"path": "/author/*/affiliation",
		"author": {
			"type": "Author",
			"id": [ AuthorID ],
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
			"id" : [ PaperID ],
			"select": [ "OriginalPaperTitle", "NormalizedPaperTitle"]
		},
		"author": {
			"type": "Author",
			"select":[ "Name" ]
		}
	}
	return MAG(data)

def GetAuthorPublicationPairs(AuthorID):
	data = {
		"path": "/author/*/paper",
		"paper": {
			"type": "Paper",
			"select": [ "OriginalPaperTitle", "NormalizedPaperTitle", "PublishYear"]
		},
		"author": {
			"type": "Author",
			"id" : [ AuthorID ],
			"select":[ "Name" ]
		}
	}
	return MAG(data)

def CountAuthorConference(AuthorID, ConferenceShortName):
	data = {
		"path": "/author/*/paper/*/conferenceseries",
		"paper": {
			"type": "Paper",
		},
		"conferenceseries": {
			"type": "ConferenceSeries",
			"ShortName": ConferenceShortName
		},
		"author": {
			"type": "Author",
			"id" : [ AuthorID ],
			"select":[ "Name" ]
		}
	}
	return len(MAG(data))

def CheckPublicationAuthor(PaperID, AuthorID):
	data = {
		"path": "/paper/*/author",
		"paper": {
			"type": "Paper",
			"id" : [ PaperID ],
			"select": [ "OriginalPaperTitle", "NormalizedPaperTitle" ]
		},
		"author": {
			"type": "Author",
			"select": [ "Name" ]
		}
	}
	for w in MAG(data):
		if w[1]['CellID'] == AuthorID:
			return True
	return False

def regcut(rule, s):
    return " ".join( \
		filter(lambda x : len(x) > 0, re.compile(rule).split(s.lower())))

def NormalizeString(s):
    my_unicode = s.decode('unicode-escape')
    s = unicodedata \
		.normalize('NFD', my_unicode) \
		.encode('ascii', 'ignore')
    return regcut("[\W+_]", regcut("\<[^\>]*\>", s))

def editdistance(s, t):
	if (isAbbr(s) or isAbbr(t)) and s[0] == t[0]: return 0
	m = len(s) + 1
	n = len(t) + 1
	opt = {}
	for i in xrange(m): opt[i, 0] = i
	for j in xrange(n): opt[0, j] = j
	for i in xrange(1, m):
		for j in xrange(1, n):
			cost = 0 if s[i-1] == t[j-1] else 1
			opt[i, j] = min( opt[i, j-1] + 1, \
				opt[i-1, j] + 1, \
				opt[i-1, j-1] + cost)
	return opt[i, j]

def isAbbr(x): return len(x) == 1

def VagueNameMatch(s, t):
	infinity = 1e9

	a = NormalizeString(s).split(" ")
	b = NormalizeString(t).split(" ")

	if (len(a) == len(b)):
		for i in xrange(len(a)):
			if isAbbr(a[i]) or isAbbr(b[i]):
				a[i] = a[i][0]
				b[i] = b[i][0]
		return editdistance(" ".join(a), " ".join(b)) <= 1
	else:
		if (len(a) > len(b)): a, b = b, a
		m = len(a) + 1
		n = len(b) + 1
		opt = {}
		for i in xrange(m): opt[i, 0] = i
		for j in xrange(n): opt[0, j] = 0
		for i in xrange(1, m):
			for j in xrange(i, n):
				cost = min(editdistance(a[i - 1], b[j - 1]), 2)
				opt[i, j] = infinity
				for k in xrange(i-1, j):
					opt[i, j] = min(opt[i, j], opt[i - 1, k] + cost)
		ans = infinity
		for t in xrange(m - 1, n):
			ans = min(opt[m - 1, t], ans)
		return ans <= 1

def check(AuthorID, PaperID):
	global dEbUg

	# Get Author Name
	AuthorName = GetAuthorName(AuthorID)
	if AuthorName == None: return False

	OriginalPaperTitle = GetOriginalPaperTitle(PaperID)
	NormalizedPaperTitle = GetNormalizedPaperTitle(PaperID)
	PublishYear = GetPublishYear(PaperID)
	if (OriginalPaperTitle == None and NormalizedPaperTitle == None): return False

	# Get Author Author's Affiliations
	temp = GetAuthorAffiliations(AuthorID)
	AuthorAffiliations = []
	for w in temp:
		AuthorAffiliations += \
			[ NormalizeString(t) for t in w.split("|") ]

	# Debug Information
	if dEbUg:
		print "AuthorID	:", AuthorID
		print "AuthorName	:", AuthorName
		print "AuthorAffiliations :"
		for AuthorAffiliation in AuthorAffiliations:
			print AuthorAffiliation
		print "-" * 30

	# Time Check
	AuthorPublicationPairs = GetAuthorPublicationPairs(AuthorID)
	time_min = 9999
	time_max =-9999
	count = 0

	for w in AuthorPublicationPairs:
		if (w[1]['CellID'] != PaperID and \
			w[1]['PublishYear'] != "" and w[1]['PublishYear'] != "0"):
				time_max = max(time_max, int(w[1]['PublishYear']))
				time_min = min(time_min, int(w[1]['PublishYear']))
				count += 1
	# todo : coauthor check
	if time_max - time_min <= 80 and count > 5 \
		and (PublishYear > time_min + 80 or PublishYear < time_max - 80):
			if dEbUg: print "Time interval check Mismatched :("
			return False
	if count > 20 and (PublishYear > time_max + 10 \
		or PublishYear < time_min - 10):
			if dEbUg: print "Time consecutive check Mismatched :("
			return False

	if (CheckPublicationAuthor(PaperID, AuthorID)):
		return True
	# todo : Check link

	# Get all authors of this publication
	PublicationAuthorPairs = GetPublicationAuthorPairs(PaperID)
	# if dEbUg: print json.dumps(PublicationAuthorPair, indent=4, sort_keys=True)

	# if dEbUg: print "Checking Authors..."
	for PublicationAuthorPair in PublicationAuthorPairs:

		if dEbUg: print "Checking Author", PublicationAuthorPair[1]['Name']

		if VagueNameMatch(PublicationAuthorPair[1]['Name'], AuthorName):
			if dEbUg: print "Name Matched :)"
			if AuthorAffiliations == []:
				print "No Affiliation information >_<"
				# todo : deeper check with coauthor information and other
				return True

			temp = GetAuthorAffiliations(PublicationAuthorPair[1]['CellID'])
			CandidateAuthorAffiliations = []
			for w in temp:
				CandidateAuthorAffiliations += \
					[ NormalizeString(t) for t in w.split("|") ]
			if (len(CandidateAuthorAffiliations) == 0):
				return True
			for CandidateAuthorAffiliation in CandidateAuthorAffiliations:
				for AuthorAffiliation in AuthorAffiliations:
					if (CandidateAuthorAffiliation == AuthorAffiliation or
						CandidateAuthorAffiliation.find(AuthorAffiliation) >= 0
						or AuthorAffiliation.find(CandidateAuthorAffiliation) >= 0):
							if dEbUg: print "Affiliation Matched :)"
							# todo : deeper check with coauthor information and other
							return True
			if dEbUg: print "No Affiliation Matched :("
		else:
			if dEbUg: print "Name Mismatched :("
	# todo : deeper check with coauthor information and other
	# Otherwise the answer is no
	return False

@app.route('/big2016/', methods=['POST'])
def create_task():
	global dEbUg

	if not request.json: return error("json format error")
	else: data = request.json

	if dEbUg:
		print "=" * 30
		print data
		print "-" * 30

	if ('paper_id' in data and 'author_id' in data):
		AuthorID = data['author_id']
		PaperID = data['paper_id']
		if check(AuthorID, PaperID): return right()
		else: return wrong()
	else:
		return error("json content error")

if __name__ == '__main__':
	app.run(host = "0.0.0.0", port = 23201, debug=dEbUg)
