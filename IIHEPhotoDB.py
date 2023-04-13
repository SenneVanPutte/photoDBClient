import os

try:
    from piwigo import Piwigo
except:
    print("Fatal error, Piwigo is not installed!")
    print("Try : 'pip3 install piwigo'")
    raise

class IIHEPhotoDB:
    def __init__(self , silent = True):
        self.silent = silent

        # Read credentials from .photodb
        self._load_credentials()

        self.db = Piwigo('https://photodb.iihe.ac.be/')

        try:
            if self.db.pwg.session.login(
                username=self.username, 
                password=self.password
                ) == True:
                if self.silent == False:
                    print("Connection successful")
            else:
                print("Unable to connect to the db")
                raise
        except Exception as e:
            print(f"Unable to connect to db: {e}")
            raise

    def getListOfFolder(self):
        try:
            api = self.db.pwg.categories.getList(recursive=True)
            result = []
            for i in api["categories"]:
                result.append(str(i["id"])+' - '+ str(i["name"]))
                text = '\n'.join(result)
            if not self.silent:
                print("List of albums (id  -  name):")
                print(text)
            return result    
        
        except Exception as e:
            print(f"Error, unable to get list of folders: {e}")
            return []
        

    def createFolder(self, folder_name):
        ## Create in parent folder "IIHE camera stand": id = 149
        try:
            api = self.db.pwg.categories.add(name=folder_name,parent="149",status="private")
            if(api['info']=='Album added'):
                if not self.silent:
                    print("Album is created!")
                return api["id"]
            else:
                print(f"Error, unable to create album : {api['info']}")
                return -1
        except Exception as e:
            print(f"Error, unable to create album : {e}")
            return -1

    def uploadImage(self, image_path, id_cat, tags,comment):
        tag_str = ""
        for tt in tags:
            while len(tt) > 0 and tt[0] == " ":
                tt = tt[1:]
            while len(tt) > 0 and tt[-1] == " ":
                tt = tt[:-1]
            if tt!="":
                tag_str+=tt+","
        
        if len(tag_str) > 0:
            tag_str = tag_str[:-1] #removing trailing ","
        if self.silent == False:
            print(f"Tags : {tag_str}")

        try:
            api = self.db.pwg.images.addSimple(image=image_path, category=id_cat,tags=tag_str, comment=comment)
            
            if self.silent == False:
                print("Image upload successful!")
                print(api)
            return api['url']
        except Exception as e:
            print(f"Error while uploading: {e}")
            return "Unable to upload picture!"
    
    def _load_credentials(self):
        '''
        Read ".photodb".
        Load password and username.
        '''
        cfg_file = os.path.join(os.path.dirname(__file__), '.photodb')
        o_file = open(cfg_file, 'r')
        lines = o_file.readlines()
        o_file.close()

        for line in lines:
            if line.startswith('USERNAME='):
                self.username = line.replace('\n', '').replace('USERNAME=', '')
            if line.startswith('PASSWORD='):
                self.password = line.replace('\n', '').replace('PASSWORD=', '')

if __name__ == "__main__":
    db = IIHEPhotoDB(silent = False)
    db.getListOfFolder()
    db.createFolder("Testing")
    db.uploadImage("default_img.jpg",152,["module_000"],"My comment")
