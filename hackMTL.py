
import urllib
import oauth2
import simplejson as json
from pprint import pprint
from operator import itemgetter
import cherrypy
import threading
import pygraphviz
import subprocess

consumer, secret = open("keys", "r").read().strip().split("|")
msgs = "http://api.dokdok.com/1.0/contactmessages.json"
threadInfo = "http://api.dokdok.com/1.0/threadinfo.json"
client = oauth2.Client(oauth2.Consumer(key=consumer, secret=secret))

threadStore = {}
for line in open("threads", "r"):
    x = line.strip().split("|")
    threadStore[x[0]] = x[1:]
 
emailStore = {}
for line in open("emails", "r"):
    x = line.strip().split("|")
    emailStore[x[0]] = x[1:]

threadCache = []
emailCache = []
stop = ["nicolas@kruchten.com", "nicolas@ewb.ca", "nicolaskruchten@gmail.com", "nicolas.kruchten@bell.ca", "nic@ewb.ca", "nick@kruchten.com"] #stoplist
connections = []
hitlist = {}
n =[]

def getJSON(url, params):
    print url, params
    resp, content = client.request(url + "?" + urllib.urlencode(params), "GET")
    print resp
    return json.loads(content)

def threadsForEmail(e):
    if e in threadStore.keys(): return threadStore[e]
    content = getJSON(msgs, {"email":e,"limit":75})
    x = [m["gmailThreadId"] for m in content["data"]]
    u = []
    [u.append(t) for t in x if t not in u]
    f = open("threads", "a")
    f.write(e)
    for t in u: f.write("|"+t)
    f.write("\n")
    f.close()
    return u

def emailsForThread(t):
    if t in emailStore.keys(): return emailStore[t]
    content = getJSON(threadInfo, {"gmailthreadid": t})
    x =[e["allEmails"][0] for e in content["data"]["contacts"]]
    u = []
    [u.append(e) for e in x if e not in u]
    f = open("emails", "a")
    f.write(t)
    for e in u: f.write("|"+e)
    f.write("\n")
    f.close()
    return u

def digWithEmail(email):
    del(hitlist[email])
    if email in emailCache: return
    emailCache.append(email)
    if email not in n: n.append(email)
    print "digging: " + email
    threads = threadsForEmail(email)
    for t in [t for t in threads if t not in threadCache]:
        threadCache.append(t)
        emails = emailsForThread(t)
        for e in emails:
            e = e.replace("kruchten.ca", "kruchten.com")
            if e == email or e in stop: continue
            c = (email, e) if email < e else (e, email)
            if c not in connections: 
                connections.append(c)
                if e not in n: n.append(e)
                if e not in emailCache:
                    hitlist[e] = hitlist.get(e,0)+1
                    print "  hitlist[%s] : %d "  % (e, hitlist[e])


class UIServer():
    
    def __init__(self, connections):
        self.connections = connections
    
    def network(self):
        g = pygraphviz.AGraph(name="network", overlap="false")
        for start, end in self.connections:
            start = start.replace("@","@\\n")
            end = end.replace("@", "@\\n")
            g.add_node(start)
            g.add_node(end)
            g.add_edge(start, end)
        cherrypy.response.headers["Content-Type"] = "image/svg+xml"
        return subprocess.Popen('neato -Tsvg', 
                             shell=True, 
                             stdin=subprocess.PIPE, 
                             stdout=subprocess.PIPE).communicate(g.to_string())[0] 
    network.exposed=True

    def json(self):
        result = "var nodes= %s ;\n" % str([{"nodeName":str(s)} for s in n])
        result += "var edges= %s ;\n" % str([{"source":n.index(start), "target":n.index(end)} for (start,end) in connections])
        return result
    json.exposed=True

def dig():
    hitlist["family@kruchten.com"] = 10 #start here
    while len(hitlist) > 0:
        print "sorting " + str(len(hitlist))
        mostHit = sorted(hitlist.iteritems(), key=itemgetter(1), reverse=True)[0][0]
        digWithEmail(mostHit)
    print "ALL DONE\n\n\n\n\n"

if __name__ == "__main__":
    #tasks = threading.Thread(target = dig)
    #tasks.start()
    #cherrypy.quickstart(UIServer(connections))
    dig()


