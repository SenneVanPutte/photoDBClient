import requests
import json
import urllib

import os

import hashlib

class IIHEPhotoDB:
    def __init__(self):
        global cookies

        username="CleanRoom" # User name in the PhotoDB
        print("Connecting to the DB...!")
        url= "https://photodb.iihe.ac.be/ws.php?format=json"
        load = {"method": "pwg.session.login", "username": username, "password": "*****"}   # password is needed
        try:
            api_req = requests.post(url, load)
            api = json.loads(api_req.content.decode('utf-8'))
            if(api['stat']=='ok'):
                print("Connected")
                print(api)
            if(api['stat']=='fail'):
                print("Not Connected")
                print(api)
        except Exception as e:
            print("Error...")
            raise
        cookies=api_req.cookies
    def getListOfFolder(self):
        try:
            api_req = requests.get("https://photodb.iihe.ac.be/ws.php?format=json&method=pwg.categories.getList&recursive=true", cookies= cookies)
            api = json.loads(api_req.content.decode('utf-8'))
            if(api['stat']=='ok'):
                print("Success!")
            if(api['stat']=='fail'):
                print("Failed!")
        except Exception as e:
            print("Error...")
        result = []
        for i in api["result"]["categories"]:
            result.append(str(i["id"])+' - '+ str(i["name"]))
            text = '\n'.join(result)
        print("List of albums (id  -  name):")
        print(text)
        return result

    def createFolder(self, folder_name):
        ## Create in parent folder "IIHE camera stand": id = 149
        try:
            api_req = requests.get("https://photodb.iihe.ac.be/ws.php?format=json&method=pwg.categories.add&name=%s&parent=149&status=private" % (folder_name), cookies=cookies)
            api = json.loads(api_req.content.decode('utf-8'))
            if(api['stat']=='ok'):
                print("Album is created!")
                alb_id = str(api["result"]["id"])
                return alb_id
            if(api['stat']=='fail'):
                print("Failed to create an album!")
                print(api)
        except Exception as e:
            print("Error...")
    def uploadImage(self, image_path, id_cat, tags,comment):
            # metadata_list=metadata.split(";")
            # tag=metadata_list[2]+","+metadata_list[-1].replace('\n','')
            # comment=metadata_list[3]
            tag_str = ""
            for tt in tags:
                if tt!="":
                    tag_str+=","
            
            if len(tag_str) > 0:
                tag_str = tag_str[:-1] #removing trailing ","

            
            url = "https://photodb.iihe.ac.be/ws.php?format=json"
            headers = {'Content_Type': 'form-data'}

            data={}
            data["method"]=["pwg.images.addSimple"]
            data["category"]=id_cat
            data["comment"]=comment
            if tag_str != "":
                data["tags"]=tag_str
            # data["name"]="CleanRoom"
            print(data["tags"])

            file_to_send = {'image': open(image_path,'rb')}
            try:
                api_req = requests.post(url, data, files=file_to_send, cookies=cookies, headers=headers)
                print(api_req)
                print(api_req.content.decode("utf-8"))
                api = json.loads(api_req.content.decode('utf-8'))
                print(api)
                if(api['stat']=='ok'):
                    print("Picture is uploaded to DB")
                    print(api)
                if(api['stat']=='fail'):
                    print("Picture is NOT uploaded to DB")
                    print(api)
            except Exception as e:
                print(f"Error while uploading: {e}")
