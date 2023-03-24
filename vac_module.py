#Inputs all on the bottom:



#communicate to managers: statuses can be changed
import ezgmail, os, csv, ezsheets, glob,shutil, re
from datetime import date, datetime,timedelta
from twilio.rest import Client
from pathlib import Path
os.chdir(r'C:\Users\Lenovo\PycharmProjects\Vacancy')

#Aug 6th: 2022 -- we want to add functionality where: if there is a new vacant unit in AppFolio, the code sends out a text msg alert to everyone
#we are going to try to do as much of this outside the class as possible (waay too messy inside the class)
def Add_To_Textmsg_Body():
    #first: pull both csv's and store data in lists
    today = date.today()
    yesterday = today - timedelta(days=1)
    path = r'C:\Users\Lenovo\PycharmProjects\Vacancy\module_update'
    def download_csvs():
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        #(1) Download the most recent vacancy csv
        thread[0].messages[0].downloadAllAttachments(downloadFolder=path)
        #(2) Download yesterday's csv
        thread[1].messages[0].downloadAllAttachments(downloadFolder=path)
    #after it's all said and done, clear everything from the "module_update" folder
    def clear_downloadfolder():
        folder = path
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

 #helper function: given a date, scrape through gmail to find the corresponding csv file
    #--> and then spit that csv file data into a list (returned)
    def extract_csv_data(date):
        firsthalf = r'C:\Users\Lenovo\PycharmProjects\Vacancy\module_update\unit_vacancy_detail-'
        secondhalf = str(date).replace('-', '') + '.csv'
        filename = firsthalf + secondhalf
        file = open(filename)
        reader = csv.reader(file)
        data = list(reader)
        print(data)
        # print(data)
        return data
        # second: compare today's csv with yesterday's csv (compare the two lists!)
        # 1a: determine if a row in the csv is a unit or not (done)
        # 2a: store all units in some kind of a list (done)
        # 3a: compare lists from one csv to the next one (done)

    all_properties = ['Holiday', 'Mt Vista', 'Westwind', 'Crestview', \
                          'Hitching Post', 'SFH', 'Patrician', 'Wishing Well',\
                      'Avalon','Aladdin','Bonanza']

    SFH = ['Chestnut', 'Elm', '12398 4th', '12993 2nd', 'Reedywoods', 'North Grove', \
               'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood']

    # 1a: given a list(row in excel), return whether that excel row is a unit
    def isunit(list):
        if len(list) < 2:
            return False

        # helper function: given a string(or int?), determine if that it is a unit num. for ex, "98A" or "94" would be a unit, but "General Rental Application" would not be
        def is_space(string):
            def has_numbers(inputString):
                return any(char.isdigit() for char in inputString)

            if len(string) < 5 and has_numbers(string):
                return True
            return False

        space_num = list[0]
        prop_address = list[-1]
        for i in all_properties:
            if i in prop_address and is_space(space_num):
                return True
        # sadly, SFH do not have space numbers, so gotta find some other way to do this...
        for i in SFH:
            if i in prop_address and len(list) > 7:
                return True
        return False

    #2a: todays_csvoutput --> strips --> todays_vacunits
    #loops thru csv file (list of lists [each row being a list]) and puts vacant units in one, clean list
    def extract_vacunits(csvoutput):

        #Helper: given a long address list "Hitching Post - 34642 Yucaipa Blvd Yucaipa, CA 92399", abbreviate to "HP"
        def abbr_propname(longpropname):
            d = {'Holiday': 'Hol', 'Mt Vista': 'MtV', 'Westwind': 'West', 'Crestview': 'Crest', \
                 'Hitching Post': 'HP', 'SFH': 'SFH', 'Patrician': 'Pat', 'Wishing Well': 'Wish', \
                 'Avalon':'Av', 'Aladdin':'Al', 'Bonanza':'Bon',\
                 'Chestnut': 'Chestnut', 'Elm': 'Elm', '12398 4th': '12398 4th', '12993 2nd': '12993 2nd',\
                 'Reedywoods': 'Reedywd', 'North Grove': 'Grove', \
                 'Massachusetts': 'Massachu', 'Michigan': 'Mich', '906 N 4th': '906 N 4th',\
                 'Indian School': 'Indian School', 'Cottonwood': 'Cottonwd'
                 }
            for i in d:
                if i in longpropname:
                    return d[i]
            return 'Uh Oh, No Matches!'
        #Helper: given a long address (ex--"910 E Indian School Lane - 910 E Indian School Ln Banning, CA 92220"), return whether it is a SFH
        def is_SFH(longpropname):
            for i in SFH:
                if i in longpropname:
                    return True
            return False

        vacant_list = []
        for row in csvoutput:
            if isunit(row):
                #if it is a SFH, there is no space num (obviously! duh!)
                if is_SFH(row[-1]):
                    space_num = ''
                else:
                    space_num = row[0]
                prop_name = abbr_propname(row[-1])
                combined = prop_name + ' '+ space_num
                vacant_list.append(combined)
        return vacant_list

    #3A: compares today's and yesterday's vacant lists; returns third list of new vacants (in string format)
    def compare(today_lst,yest_lst):
        new_vacants = []
        string = ''
        for unit in today_lst:
            if unit not in yest_lst:
                new_vacants.append(unit)
        #cool, now let's put everything in a string
        for i in new_vacants:
            if new_vacants.index(i)==0:
                string = i + string
            else:
                string = i + ', '+string
        return string

    #3B: if there are not any new vacants, there is nothing to add to the text body!
    def are_there_any_new_vacants(today_lst,yest_lst):
        if compare(today_lst,yest_lst) == '':
            return False
        return True

    download_csvs()
    todays_csvoutput = extract_csv_data(today)
    yest_csvoutput = extract_csv_data(yesterday)
    todays_vacunits = extract_vacunits(todays_csvoutput)
    yest_vacunits = extract_vacunits(yest_csvoutput)
    clear_downloadfolder()
    if are_there_any_new_vacants(todays_vacunits,yest_vacunits):
        text_PtA = "New Vacancy! (Plz Update): "
        text_PtB = compare(todays_vacunits,yest_vacunits)
        return text_PtA + text_PtB + """\n"""
    #if no new vacant units, append empty string to self.beginning
    return ""

#we don't want this to run every 5 minutes if there is a vacancy!
#so we want this to run only if it is between the times of 8am and 8:05 am (Helper Below)
def is_it_time_baby():
    import datetime
    now = datetime.datetime.now()
    today9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    today905am = now.replace(hour=9, minute=5, second=0, microsecond=0)
    if now>today9am and now<today905am:
        return True
    return False

class vacancy_csv(object):
#returns Data set from AppFolio Vacancy (using def read_csv)
    def __init__(self):
        self.beginning = Add_To_Textmsg_Body()
        self.printedmsg = ""
        #to send or not to send, that is the question
        self.tosendornot = False
        self.data = []
        self.d = {}
        self.vac_list = []
        self.properties = ['Holiday', 'Mt Vista', 'Westwind', 'Crestview',\
                            'Hitching Post', 'SFH', 'Patrician','Wishing Well',\
                           'Avalon','Aladdin','Bonanza']
        self.SFH = ['Chestnut', 'Elm', '12398 4th', '12993 2nd', 'Reedywoods', 'North Grove', \
                    'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood']
        self.dic = {'Holiday':{},'Mt Vista': {},'Westwind':{}, \
                    'Avalon':{}, 'Aladdin':{}, 'Bonanza':{},\
                    'Crestview':{},'Hitching Post':{},'SFH':{},'Patrician':{},'Wishing Well':{},\
                    'Chestnut': {}, 'Elm': {}, '12398 4th': {}, '12993 2nd': {}, 'Reedywoods': {}, 'North Grove': {}, \
                    'Massachusetts': {}, 'Michigan': {}, '906 N 4th': {}, 'Indian School': {}, 'Cottonwood': {}}
        # self.statuslist = ['Trash Need To Be Cleaned Out','Undergoing Turnover',\
        #                    'Need Appliances','Need Cleaning','Rent Ready','Rented',\
        #                    'Under Construction', 'No Status']
        self.statuslist = ['Rent Ready','Recently Vacated - Needs Work','Rented','New Coach/Construction','Empty Lot','No Status (Please Update)']
        self.ss = ezsheets.Spreadsheet('1Jn3vSrRxB3j1oZab3QZd1gnFczyndmLEbeUqn_JaEkU')
        #action items: calling helper functions
        self.scrapegmail()
        self.read_csv()
        self.create_dic()
        #update csv dic from gsheets
        self.gsheets()
        self.sorted_dic()
        #compare (new) gsheet input with old local stuff
        self.compare()
        #add the sorted dic into self.printed msg
        self.txtmsg()
        # self.firestore()
        self.skimthefat()
    def scrapegmail(self):
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        thread[0].messages[0].downloadAllAttachments(downloadFolder=r'C:\Users\Lenovo\PycharmProjects\Vacancy')
        return None
    def read_csv(self):
        s1 = "unit_vacancy_detail-"
        today = date.today()
        s2 = str(today).replace('-','') +'.csv'
        s3 = s1+s2
        file = open(s3)
        reader = csv.reader(file)
        self.data = list(reader)
        return self.data


    def is_SFH(self, string):
        # given a string, return whether it is one of our SFHs
        SFH_list = ['Chestnut', 'Elm', '12398 4th', '12993 2nd', 'Reedywoods', 'North Grove', \
                    'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood']
        for i in SFH_list:
            if i in string:
                return True
        return False

    def is_unit(self, string):
        # given a string, analyze whether it is a unit
        if len(string) > 4 or len(string) < 1:
            return False
        count = 0
        for i in string:
            if i.isalpha():
                count += 1
            if count > 1:
                return False
            # else:
            #     print('no characters detected')
        return True
    def is_prop(self,string):
        #given a string, return whether it is one of our props
        for i in self.properties:
            if i in string:
                return True
        return False
    def which_prop(self,string):
        #given a long string with prop hidden inside, return which property it is!
        for i in self.properties:
            if i in string:
                return i
        for x in self.SFH:
            if x in string:
                return x
        return None
    def create_dic(self):
        for i in self.data:
            if len(i)>2:
                unit = i[0]
                prop = i[-1]
                if self.is_unit(unit) and self.is_prop(prop):
                    # print(unit,prop)
                    obj = Unit(self.which_prop(prop), unit)
                    self.dic[self.which_prop(prop)].update({unit:obj})
                if self.is_SFH(unit):
                    obj = Unit(self.which_prop(prop), 'House')
                    self.dic[self.which_prop(prop)].update({'House': obj})

    def in_dic(self, complex, unit):
    #given complex & unit, return True if they can be found in dictionary
        try:
            self.dic[complex][unit]
        except:
            return False
        return True
    def gsheets(self):
        #pull data from google sheets & update dictionary
        sheet = self.ss[0]
        for i in sheet:
            if self.is_SFH(i[1]):
                complex = i[1].replace(" House", "")
                unit = 'House'
            else:
                complex = i[1]
                unit = i[2]

            if len(i[0])>0 and self.in_dic(complex,unit):
                status = i[3]
                askingrent = i[4]
                bedbath = i[5]
                nextsteps = i[6]
                actualrent = i[7]
                person = i[8]
                self.dic[complex][unit].status = status
                self.dic[complex][unit].askingrent = askingrent
                self.dic[complex][unit].unittype = bedbath
                self.dic[complex][unit].actualrent = actualrent
                self.dic[complex][unit].notes = nextsteps
                self.dic[complex][unit].person = person
        return self.dic
    def compare(self):
    #compare old csv with gsheet
    #if any incongruity, call update_announcement()
        old_file = open('old.csv')
        reader1 = csv.reader(old_file)
        data1 = list(reader1)

        #next,download gsheet into local folder
        self.ss.downloadAsCSV()
        new_file = open('new.csv')
        reader2 = csv.reader(new_file)
        data2 = list(reader2)
        self.newdata = data2

        oldstamps = []
        newstamps = []
        for i in data1:
            oldstamps.append(i[0])
        for i in data2:
            newstamps.append(i[0])

        #compare the last 2 timestamps
        if oldstamps == newstamps:
            print('nothing to update here!')
            self.tosendornot = False
            return False

        if not oldstamps == newstamps:
            self.updated_lines = []
            self.tosendornot = True

            # find the index of last matching timestamp,
            for i in oldstamps:
                try:
                    if len(i[0])>0:
                        ind = oldstamps.index(i)
                except:
                    x = 'do nothing'
            #add everything after that point to self.updated_lines
            self.updated_lines.extend(data2[ind+1:])
            # print('updated lines below:')
            # print(self.updated_lines)
            self.update_old()
            self.update_announcement()
            # print('updated!')
            return True
    def update_old(self):
    #after comparing, update old.csv with newly submitted lines from
    #store new_csv in list, write that entire list into old_csv
        outputFile = open('old.csv', 'w', newline='')
        outputWriter = csv.writer(outputFile)
        for i in self.newdata:
            outputWriter.writerow(i)
        return None

    def update_announcement(self):
    #if called upon, change the first few lines of the txt msg (final output)
        s = """"""
        personlist = []
        for i in self.updated_lines:
            person = i[8]
            if person not in personlist:
                personlist.append(person)

        for i in range(len(personlist)):
            if i < len(personlist)-1:
                s+= personlist[i]+", "
            else:
                s+= personlist[i]

        s += " recently updated: "

        count = 0
        for i in self.updated_lines:
            count+=1
            if self.is_SFH(i[1]):
                prop = self.abbr_complex(i[1].replace(" House", ""))
                space = "House"
            else:
                prop = self.abbr_complex(i[1])
                space = i[2]
            if count < len(self.updated_lines):
                s+= prop + " "+ space + ", "
            else:
                s+= prop + " " + space

        self.printedmsg = s + '\n'+ self.printedmsg
        return None

    def sorted_dic(self):
    #sort dictionary by status {'status1':{obj1,obj2},'status2':{obj1,obj2}}
        #first set default parameters for your new sorted dictionary
        self.sorted_dic = {}
        for i in self.statuslist:
            self.sorted_dic.update({i:{}})
        #then fill the sorted dictionary by looping through your og dictionary
        for prop in self.dic:
            for unit in self.dic[prop]:
                a = self.dic[prop][unit]
                # print(a.complex + ' '+a.unit + ' '+a.status)
                try:
                    self.sorted_dic[a.status].update({a.complex + ' '+a.unit:a})
                except:
                    print("the object's (that you're looping thru) status does not exist")
        return self.sorted_dic

    #helper function for method below
    #abbreviate name of complex for txt msg. takes in full name of unit & returns abbr unit name string
    def abbr_complex(self, complex):
        d = {'Holiday':'Hol', 'Mt Vista':'MtV', 'Westwind':'West', 'Crestview':'Crest', \
             'Avalon':'Av', 'Aladdin':'Al', 'Bonanza':'Bon',\
         'Hitching Post':'HP', 'SFH':'SFH', 'Patrician':'Pat','Wishing Well':'Wish',\
             'Chestnut': 'Chestnut', 'Elm': 'Elm', '12398 4th': '12398 4th', '12993 2nd': '12993 2nd', 'Reedywoods': 'Reedywd', 'North Grove': 'Grove', \
             'Massachusetts': 'Massachu', 'Michigan': 'Mich', '906 N 4th': '906 N 4th', 'Indian School': 'Indian School', 'Cottonwood': 'Cottonwd'
             }
        return d[complex]
    #abbreviate name of unit type from "2Bd 2 Ba"--> "(2/2)"
    def abbr_type(self,unittype):
        txt = unittype
        L = [s for s in txt.split() if s.isdigit()]
        if txt == 'N/A':
            s2 = "(?/?)"
        else:
            s2 = "("+L[0]+"/"+L[1]+")"
        return s2

        # Oct 5th firestore code baby!
    def firestore(self):
        import firebase_admin
        from firebase_admin import credentials
        from firebase_admin import firestore
        cred = credentials.Certificate(r'C:\Users\Lenovo\PycharmProjects\Vacancy\serviceaccountkey.json')
        firebase_admin.initialize_app(cred)
        db = firestore.client()

        # first: delete all existing documents (Hierarchy: collection ('vacancy') --> document ('rent_ready') --> fields )
        L = ['just_rented', 'no_status', 'recently_updated', 'rent_ready', 'under_construction','empty_lots', 'unit_turns']
        for i in L:
            db.collection('Vacancy').document(i).delete()
        # second: create new documents
        for i in L:
            db.collection('Vacancy').document(i).set({'type': i})
        # third: fill up documents with txt msg data

        # Rent Ready
        for i in self.sorted_dic['Rent Ready']:
            complex = self.sorted_dic['Rent Ready'][i].complex
            unit = self.sorted_dic['Rent Ready'][i].unit
            askingrent = self.sorted_dic['Rent Ready'][i].askingrent
            unittype = self.sorted_dic['Rent Ready'][i].unittype

            key = self.abbr_complex(complex) + "_" + unit
            value = self.abbr_type(unittype) + "-$" + askingrent

            db.collection('Vacancy').document('rent_ready').update({key: value})

        # Unit Turns
        for i in self.sorted_dic['Recently Vacated - Needs Work']:
            complex = self.sorted_dic['Recently Vacated - Needs Work'][i].complex
            unit = self.sorted_dic['Recently Vacated - Needs Work'][i].unit
            unittype = self.sorted_dic['Recently Vacated - Needs Work'][i].unittype

            key = self.abbr_complex(complex) + "_" + unit
            value = self.abbr_type(unittype)
            db.collection('Vacancy').document('unit_turns').update({key: value})

        # Just Rented
        for i in self.sorted_dic['Rented']:
            complex = self.sorted_dic['Rented'][i].complex
            unit = self.sorted_dic['Rented'][i].unit
            actualrent = self.sorted_dic['Rented'][i].actualrent
            unittype = self.sorted_dic['Rented'][i].unittype

            key = self.abbr_complex(complex) + "_" + unit
            value = self.abbr_type(unittype) + "-$" + actualrent

            db.collection('Vacancy').document('just_rented').update({key: value})

        # Under Construction
        for i in self.sorted_dic['New Coach/Construction']:
            complex = self.abbr_complex(self.sorted_dic['New Coach/Construction'][i].complex)
            unit = self.sorted_dic['New Coach/Construction'][i].unit

            key = complex + "_" + unit
            value = ""
            db.collection('Vacancy').document('under_construction').update({key: value})

        #Empty Lots
        for i in self.sorted_dic['Empty Lot']:
            complex = self.abbr_complex(self.sorted_dic['Empty Lot'][i].complex)
            unit = self.sorted_dic['Empty Lot'][i].unit

            key = complex + "_" + unit
            value = ""
            db.collection('Vacancy').document('empty_lots').update({key: value})

        # No Status
        for i in self.sorted_dic['No Status (Please Update)']:
            complex = self.abbr_complex(self.sorted_dic['No Status (Please Update)'][i].complex)
            unit = self.sorted_dic['No Status (Please Update)'][i].unit

            key = complex + "_" + unit
            value = ""
            db.collection('Vacancy').document('no_status').update({key: value})

    def txtmsg(self):

        #create print statement for mass text distribution
        string = """"""
        string += "\n"
        string+= "Rent Ready:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"

        # March 23 updates: chatgpt code
        #make sure to import re!
        def natural_sort_key(s):
            """Key function for natural sorting"""
            return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', s)]

        def alphabetize_nested_dict(nested_dict):
            for key, value in nested_dict.items():
                if isinstance(value, dict):
                    nested_dict[key] = alphabetize_nested_dict(value)
            return dict(sorted(nested_dict.items(), key=lambda x: natural_sort_key(x[0])))

        #alphabetize everything using that sweet sweet gpt code
        alph_dic = alphabetize_nested_dict(self.sorted_dic['Rent Ready'])

        for i in alph_dic:
            complex = alph_dic[i].complex
            unit = alph_dic[i].unit
            askingrent = alph_dic[i].askingrent
            unittype = alph_dic[i].unittype
            string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- $"+askingrent +"\n"

        # for i in self.sorted_dic['Rent Ready']:
        #     complex = self.sorted_dic['Rent Ready'][i].complex
        #     unit = self.sorted_dic['Rent Ready'][i].unit
        #     askingrent = self.sorted_dic['Rent Ready'][i].askingrent
        #     unittype = self.sorted_dic['Rent Ready'][i].unittype
        #     string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- $"+askingrent +"\n"

        string+= " \n"
        string+= "Recently Vacated - Needs Work:\n"
        string+= "-  -  -  -  -  -  -  -  -  -  -\n"
        for i in self.sorted_dic['Recently Vacated - Needs Work']:
            complex = self.sorted_dic['Recently Vacated - Needs Work'][i].complex
            unit = self.sorted_dic['Recently Vacated - Needs Work'][i].unit
            nextsteps = self.sorted_dic['Recently Vacated - Needs Work'][i].notes
            unittype = self.sorted_dic['Recently Vacated - Needs Work'][i].unittype
            if nextsteps == "":
                nextsteps = "What's next?"
            # string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- "+nextsteps +"\n"
            # string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+", "
            #March 23 2023 Update: getting rid of unit type to condense space
            string += self.abbr_complex(complex) + " " + unit +  ", "

        string+= "\n"
        string+= "\nJust Rented:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"

        for i in self.sorted_dic['Rented']:
            complex = self.sorted_dic['Rented'][i].complex
            unit = self.sorted_dic['Rented'][i].unit
            actualrent = self.sorted_dic['Rented'][i].actualrent
            unittype = self.sorted_dic['Rented'][i].unittype
            string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- $"+actualrent +"\n"

        string+= "\n"
        string += "New Coach/Construction:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"
        L = []
        for i in self.sorted_dic['New Coach/Construction']:
            complex = self.abbr_complex(self.sorted_dic['New Coach/Construction'][i].complex)
            unit = self.sorted_dic['New Coach/Construction'][i].unit
            combined = complex + " "+ unit
            L.append(combined)
            # compile everything in list & add to one line in string
        liststring = ''
        for x in L:
            liststring += x + ", "
        string += liststring+"\n"

        string+= "\n"

        string += "\n"
        string += "Empty Lots:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"
        L = []
        for i in self.sorted_dic['Empty Lot']:
            complex = self.abbr_complex(self.sorted_dic['Empty Lot'][i].complex)
            unit = self.sorted_dic['Empty Lot'][i].unit
            combined = complex + " " + unit
            L.append(combined)
            # compile everything in list & add to one line in string
        liststring = ''
        for x in L:
            liststring += x + ", "
        string += liststring + "\n"

        string += "\n"

        string += "No Status (Pls Update):\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"
        L2 = []
        for i in self.sorted_dic['No Status (Please Update)']:
            complex = self.abbr_complex(self.sorted_dic['No Status (Please Update)'][i].complex)
            unit = self.sorted_dic['No Status (Please Update)'][i].unit
            combined = complex + " " + unit
            L2.append(combined)
            # compile everything in list & add to one line in string
        liststring2 = ''
        for x in L2:
            liststring2 += x + ", "
        string += liststring2 + "\n"

        string+= "\n"
        string+= "https://forms.gle/ZJminE5umWn9E8YM6"
        string+= "\n"
        if is_it_time_baby():
            self.printedmsg = self.beginning + self.printedmsg + string
        else:
            self.printedmsg = self.printedmsg + string

        return None

    #delete all the old csv files pulled from appfolio
    def skimthefat(self):
        path = r'C:\Users\Lenovo\PycharmProjects\Vacancy\*.csv'

        count = 0
        for fname in glob.glob(path):
            #continue only if file is AppFolio unit_vacancy file
            if 'unit_vacancy_detail' in fname:
                datestr = fname[-12:-4]
                year = datestr[2:4]
                month = datestr[4:6]
                day = datestr[6:]
                s = day+'/'+month+'/'+year

                #(2)create datetime object "mightbeold"
                mightbeold = datetime.strptime(s,'%d/%m/%y')

                #(3) create datetime obj for today
                year2 = str(date.today().year - 2000)
                month2 = str(date.today().month)
                day2 = str(date.today().day)
                s2 = day2+'/'+month2+'/'+year2
                todayobj = datetime.strptime(s2,'%d/%m/%y')

                if todayobj>mightbeold:
                    count+=1
                    os.remove(fname)
                    print('removed '+fname)
        if count == 0:
            print('No milk to skim!')

class Unit(object):
    def __init__(self, complex, unit):
        self.complex = complex
        self.unit = unit
        self.unittype = 'Empty'
        self.status = 'No Status (Please Update)'
        #notes is equivalent to next steps: column 6 in the spreadsheet
        self.notes = 'Empty'
        self.person = 'Empty'
        self.askingrent = 'Empty'
        self.actualrent = 'Empty'

#return list of numbers to message
def numberstomessage():

    # d = {'Victor':'+19098163161','Jian':'+19092101491','Karla':'+19097677208','Brian':'+19097140840',
    #     'Richard':'+19516639308','Jeff':'+19092228209','Tony':'+16269991519','Hector':'+19094897033',
    #      'Rick':'+19092541913','Amanda':'+19094861526','Debbie':'+7605141103'
    # }
    d = {'Victor':'+19098163161'}
    L = []
    for i in d:
        L.append(d[i])
    return L

def call_twilio():

    # Helper: if there is a new vacant unit (determined by our fancy new function "Addtotextmsgbody"),
    # We want to over-ride everything and send the txt msg anyway
    def are_there_new_vacs():
        if Add_To_Textmsg_Body() != "" and is_it_time_baby():
            return True
        return False

    #call twilio api to print
    L = numberstomessage()
    account_sid = readtxtfile()['sid']
    auth_token = readtxtfile()['token']
    client = Client(account_sid, auth_token)
    #create object from csv class
    o1 = vacancy_csv()
    text = o1.printedmsg
    #to be removed
    print(text)
    numbers_to_message = L
    print(L)

    if o1.tosendornot or are_there_new_vacs():
        for number in numbers_to_message:
            client.messages.create(
                body = text,
                from_=readtxtfile()['from'],
                to = number
            )
        # message = client.messages \
        #     .create(
        #     body=text,
        #     from_=readtxtfile()['from'],
        #     to=readtxtfile()['to']
        # )
        print('txt msg sent:')
        # print(message.sid)
    else:
        print('txt msg should not have sent: there are no updates so no need for a txt msg')
    return 'nothing'

def readtxtfile():
    #return dictionary of {'sid':x,'token':y,'from':z,'to':a}
    #hiding my keys from you github mf's
    p = Path('twiliocreds.txt')
    text = p.read_text()
    #hard coding the shit out of this bby
    start = text.index('sid')
    sid = text[start+5: start+4+35]
    start = text.index('token')
    token = text[start+7: start+6+33]
    start = text.index('phone_from')
    phone_from = text[start+11: start+11+13]
    start = text.index('phone_to')
    phone_to = text[start+9: start+9+13]
    d = {'sid':sid,'token':token,'from':phone_from,'to':phone_to}
    return d
#
# o1 = vacancy_csv()
# print(o1.printedmsg)
# print(o1.beginning)
# print(o1.dic)
# print(o1.sorted_dic)
# print(o1.printedmsg)

call_twilio()







