#!/usr/bin/env python

import json
import os
import shutil
import re
import urllib.request
import zipfile, io
from jinja2 import Environment, FileSystemLoader

templates = FileSystemLoader('./templates')
env = Environment(loader=templates)

with open('configuration.json') as json_data_file:
    configuration = json.load(json_data_file)

api_urls =  {}
release_documents = {}

def getURLAsJSON(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            the_page = response.read()
            encoding = response.info().get_content_charset('utf-8')
            return json.loads(the_page.decode(encoding))
    except Exception as e:
        pass

    return None

def getURLAsString(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            the_page = response.read()
            encoding = response.info().get_content_charset('utf-8')
            return str(the_page.decode(encoding))
    except Exception as e:
        pass

    return None

def getURL(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(e)
        pass

    return None

def getAPIURL(api):
    return "https://editor-next.swagger.io/?url=https://raw.githubusercontent.com/emanuelfreitas/3gpp-documentation/master/apis/" + api +".yaml"

def getDigit(val):
    if val.isdigit(): return int(val)
    else: return (ord(val) - 87) 

def getAPI(getOpenAPI, regrularExpression):
    print("getAPI:" + str(getOpenAPI))
    urlAPI = re.findall(regrularExpression, str(getURLAsString(getOpenAPI)))
    for url in urlAPI:
        getOpenAPIFile = getOpenAPI + url + ".yaml"
        if os.path.exists("../apis/" + url + ".yaml"): continue        
        
        open("../apis/" + url + ".yaml", 'wb').write(getURLAsString(getOpenAPIFile))

        api_urls[url] = getAPIURL(url)
    print("getAPI Done")

def getAPIFromGithub():
    print("getAPIFromGithub starting")
    fileList = getURLAsJSON("https://api.github.com/repos/jdegre/5GC_APIs/git/trees/Rel-17?recursive=1")

    for entry in fileList["tree"]:
        filename = entry["path"]
        if not filename.endswith(".yaml"): continue
        urlfile = 'https://raw.githubusercontent.com/jdegre/5GC_APIs/master/' + filename
        
        open("../apis/" + filename, 'wb').write(getURL(urlfile))

        api_urls[filename.replace(".yaml", "")] = getAPIURL(filename.replace(".yaml", ""))
    print("getAPIFromGithub end")

baseGitURL = "https://github.com/emanuelfreitas/3gpp-documentation/raw/master/documentation/"

shutil.rmtree("../apis")
os.makedirs("../apis")

for doc in configuration:
    directoryName = doc["id"] + " - " + doc["name"]
    print(directoryName)

    m = re.search('TS (\d+)\.(\d+)', doc["id"])
    serie = m.group(1)
    docId = m.group(2)

    m = re.search('(\d)(\d)(\d)', docId)
    docgroup = m.group(1)

    lastRelease = 0
    releaseDoc = None
    
    releasesList = list(range(6, 18))
    releasesList.sort(reverse=True)

    for relase in releasesList:
        if lastRelease > 0: continue

        directory = "../documentation/" + directoryName + "/Rel-" + str(relase)
        if not os.path.exists(directory):
            os.makedirs(directory)

        filesInDir = os.listdir(directory)

        getSeriesURL = "https://www.etsi.org/deliver/etsi_ts/1" +str(serie) + str(docgroup) + "00_1" +str(serie) + str(docgroup) + "99/1" +str(serie) + str(docId) +"/"
        idArray = re.findall(r"etsi_ts\/1" +str(serie) + str(docgroup) + "00_1" +str(serie) + str(docgroup) + "99\/1" +str(serie) + str(docId) + "\/"+ str(relase).zfill(2) + "\.([\w+|\.]+)\/", str(getURLAsString(getSeriesURL)))
        
        if(len(idArray) == 0): 
            os.rmdir(directory)
            continue
        idArray.sort()
        id = idArray[len(idArray)-1]

        getSeriesURL = "https://www.etsi.org/deliver/etsi_ts/1" +str(serie) + str(docgroup) + "00_1" +str(serie) + str(docgroup) + "99/1" +str(serie) + str(docId) +"/" + str(relase).zfill(2) + "." + str(id) + "/"
        pdfFile = re.findall(r"\/(\w+).pdf", getURLAsString(getSeriesURL))
        zipFile = re.findall(r"\/(\w+).zip", getURLAsString(getSeriesURL))
        if(len(pdfFile) == 0):
            os.rmdir(directory)
            continue
        pdf = pdfFile[0]
        if(len(zipFile) > 0):
            zipF = zipFile[0]
            zipURL = getSeriesURL + "/" + str(zipF) + ".zip"
            resp = urllib.request.urlopen(zipURL)
            myzip = zipfile.ZipFile(io.BytesIO(resp.read()))
            for line in myzip.namelist():
                if line.startswith('TS') and line.endswith('yaml'):
                    myzip.extract(line, '../apis')
                    filedata = None
                    with open('../apis/'+str(line), 'r') as file :
                        print("going to replace")
                        filedata = file.read()
                        filedata = filedata.replace('$ref: \'TS', '$ref: \'https://raw.githubusercontent.com/emanuelfreitas/3gpp-documentation/master/apis/TS')
                    with open('../apis/'+str(line), 'w') as file:
                        file.write(filedata)

                    api_urls[line.replace(".yaml", "")] = getAPIURL(line.replace(".yaml", ""))

        if str(pdf)+".pdf" in filesInDir:
            filesInDir.remove(str(pdf)+".pdf")
        else:
            getSeriesURL = getSeriesURL + "/" + str(pdf) + ".pdf"
            the_page = None
            with urllib.request.urlopen(getSeriesURL) as response:
                the_page = response.read()
            with open(directory + '/' + str(pdf) + '.pdf', 'wb') as f:
                f.write(the_page)
        for f in filesInDir:
            print("GOING TO REMOVE: " + directory + "/" + f)
            os.remove(directory + "/" + f)
        
        lastRelease = relase
        releaseDoc = directoryName + "/Rel-" + str(relase) + '/' + str(pdf) + '.pdf'

    if lastRelease != 0:
        release_documents[doc["id"]] = baseGitURL + releaseDoc.replace(" ", "%20")


##getAPIFromGithub()

readme_template = env.get_template('README.j2')
output = readme_template.render(release_documents=release_documents,api_urls=api_urls)

f = open("../README.md", "w")
f.write(output)
f.close