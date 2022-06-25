#code up a construction txt msg
#Make sure everything is uploaded onto the GDrive shared folder: 'link'
#(1) Waiting for HCD Permit (2) Waiting for City Permit, (3) Waiting for HCD Insp (4) Waiting for City Insp (5) Passed (6) No Status
#one unit can only belong to one category

#communicate to managers: statuses can be changed
import ezgmail, os, csv, ezsheets, glob
from datetime import date, datetime
from twilio.rest import Client
from pathlib import Path
os.chdir(r'C:\Users\19097\PycharmProjects\VacancyTextScript')

class vacancy_csv(object):
#returns Data set from AppFolio Vacancy (using def read_csv)
    def __init__(self):
        self.printedmsg = ""
        #to send or not to send, that is the question
        self.tosendornot = False
        self.data = []
        self.d = {}
        self.vac_list = []
        self.properties = ['Holiday', 'Mt Vista', 'Westwind', 'Wilson Gardens', 'Crestview',\
                            'Hitching Post', 'SFH', 'Patrician','Wishing Well']
        self.dic = {'Holiday':{},'Mt Vista': {},'Westwind':{},'Wilson Gardens':{},\
                    'Crestview':{},'Hitching Post':{},'SFH':{},'Patrician':{},'Wishing Well':{}}
        # self.statuslist = ['Trash Need To Be Cleaned Out','Undergoing Turnover',\
        #                    'Need Appliances','Need Cleaning','Rent Ready','Rented',\
        #                    'Under Construction', 'No Status']
        self.statuslist = ['Rent Ready','Unit Still Needs Work','Rented','Under Construction','No Status (Please Update)']
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
        self.skimthefat()
    def scrapegmail(self):
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        thread[0].messages[0].downloadAllAttachments(downloadFolder=r'C:\Users\19097\PycharmProjects\VacancyTextScript')
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
    def create_dic(self):
        for i in self.data:
            if len(i)>2:
                unit = i[0]
                prop = i[-1]
                if self.is_unit(unit) and self.is_prop(prop):
                    # print(unit,prop)
                    obj = Unit(self.which_prop(prop), unit)
                    self.dic[self.which_prop(prop)].update({unit:obj})

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
        d = {'Holiday':'Hol', 'Mt Vista':'MtV', 'Westwind':'West', 'Wilson Gardens':'Wilson', 'Crestview':'Crest', \
         'Hitching Post':'HP', 'SFH':'SFH', 'Patrician':'Pat','Wishing Well':'Wish'}
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

    def txtmsg(self):
        #create print statement for mass text distribution
        string = """"""
        string += "\n"
        string+= "Rent Ready:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"
        for i in self.sorted_dic['Rent Ready']:
            complex = self.sorted_dic['Rent Ready'][i].complex
            unit = self.sorted_dic['Rent Ready'][i].unit
            askingrent = self.sorted_dic['Rent Ready'][i].askingrent
            unittype = self.sorted_dic['Rent Ready'][i].unittype
            string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- $"+askingrent +"\n"

        string+= " \n"
        string+= "Unit Turns:\n"
        string+= "-  -  -  -  -  -  -  -  -  -  -\n"
        for i in self.sorted_dic['Unit Still Needs Work']:
            complex = self.sorted_dic['Unit Still Needs Work'][i].complex
            unit = self.sorted_dic['Unit Still Needs Work'][i].unit
            nextsteps = self.sorted_dic['Unit Still Needs Work'][i].notes
            unittype = self.sorted_dic['Unit Still Needs Work'][i].unittype
            if nextsteps == "":
                nextsteps = "What's next?"
            string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- "+nextsteps +"\n"

        string+= "\n"
        string+= "Just Rented:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"

        for i in self.sorted_dic['Rented']:
            complex = self.sorted_dic['Rented'][i].complex
            unit = self.sorted_dic['Rented'][i].unit
            actualrent = self.sorted_dic['Rented'][i].actualrent
            unittype = self.sorted_dic['Rented'][i].unittype
            string+= self.abbr_complex(complex) +" "+ unit+ self.abbr_type(unittype)+"- $"+actualrent +"\n"

        string+= "\n"
        string += "Under Construction:\n"
        string += "-  -  -  -  -  -  -  -  -  -  -\n"
        L = []
        for i in self.sorted_dic['Under Construction']:
            complex = self.abbr_complex(self.sorted_dic['Under Construction'][i].complex)
            unit = self.sorted_dic['Under Construction'][i].unit
            combined = complex + " "+ unit
            L.append(combined)
            # compile everything in list & add to one line in string
        liststring = ''
        for x in L:
            liststring += x + ", "
        string += liststring+"\n"

        string+= "\n"
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
        string+= "Do Not Rent: https://tinyurl.com/345drb6w"
        self.printedmsg = self.printedmsg + string

        return None

    #delete all the old csv files pulled from appfolio
    def skimthefat(self):
        path = r'C:\Users\19097\PycharmProjects\VacancyTextScript\*.csv'

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
    d = {'Victor':'+19098163161','Jian':'+19092101491','Karla':'+19097677208','Brian':'+19097140840',
        'Richard':'+19516639308','Jeff':'+19092228209','Tony':'+16269991519','Hector':'+19094897033',
         'Charles':'+19095507143','Amanda':'+19094861526'
    }
    L = []
    for i in d:
        L.append(d[i])
    return L

def call_twilio():
    #call twilio api to print
    L = numberstomessage()
    account_sid = readtxtfile()['sid']
    auth_token = readtxtfile()['token']
    client = Client(account_sid, auth_token)
    #create object from csv class
    o1 = vacancy_csv()
    text = o1.printedmsg
    numbers_to_message = L
    print(L)

    if o1.tosendornot:
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
# print(o1.dic)
# print(o1.sorted_dic)
# print(o1.printedmsg)

call_twilio()
# numberstomessage()







