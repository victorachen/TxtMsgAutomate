
#todo:(1) work on needupdating function (
#(rather than printing everything)
# (2) create method that checks gsheets and adds to beg of self.printedmsg who has updated what
import ezgmail, os, csv, ezsheets
from datetime import date
from twilio.rest import Client
from pathlib import Path
os.chdir(r'C:\Users\Lenovo\PycharmProjects\Vacancy')

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
                            'Hitching Post', 'SFH', 'Patrician']
        self.dic = {'Holiday':{},'Mt Vista': {},'Westwind':{},'Wilson Gardens':{},\
                    'Crestview':{},'Hitching Post':{},'SFH':{},'Patrician':{}}
        self.statuslist = ['Trash Need To Be Cleaned Out','Undergoing Turnover',\
                           'Need Appliances','Need Cleaning','Rent Ready','Rented',\
                           'Under Construction', 'No Status']

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
                    #writing this extra shit (just) for bed/bath
                    if len(i[2])>2:
                        bed = i[2][0]
                        bath = i[2][2]
                    else:
                        bed = '?'
                        bath = '?'
                    obj.setbedbath(bed,bath)
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
                notes = i[4]
                person = i[5]
                self.dic[complex][unit].status = status
                self.dic[complex][unit].notes = notes
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
        s = """Most Recent Updates to Vacancies: \n"""
        for i in self.updated_lines:
            person = i[5]
            prop = i[1]
            space = i[2]
            s+= prop + ' '+space + ' updated by '+person+'\n'
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
    def txtmsg(self):
        #create print statement for mass text distribution
        string = """Below are our vacancies & what still needs to be done: \n ------------------------ \n"""
        for status in self.sorted_dic:
            s = self.sorted_dic[status]
            if len(s) > 0:
                string += "((("+status+"))): \n"
                # print("((("+status+"))):")
                for unit in s:
                    if len(s[unit].notes)>0:
                        string+= s[unit].complex+" "+s[unit].unit+"-- "+s[unit].notes+"\n"
                        # print(s[unit].complex+" "+s[unit].unit+"-- "+s[unit].notes)
                    else:
                        string+= s[unit].complex + " " +s[unit].unit+"\n"
                        # print(s[unit].complex + " " +s[unit].unit)
        string+= "Please submit updates to: https://forms.gle/ZJminE5umWn9E8YM6"
        self.printedmsg = self.printedmsg + string

        return None

class Unit(object):
    def __init__(self, complex, unit):
        self.complex = complex
        self.unit = unit
        self.bed = 0
        # self.bath = 0
        self.status = 'No Status'
        self.notes = ''
        self.person = ''
        # self.bedbath = str(self.bed)+'bd'+str(self.bath)+'ba'
        self.pricelist = {'1bd1ba': 1350, '2bd1ba': 1450, '2bd2ba': 1500, '3bd1ba': 1550,\
                          '3bd2ba': 1650, '4bd2ba': 1800}
    def setbedbath(self,bed,bath):
        self.bed = bed
        self.bath = bath
        self.bedbath = str(self.bed)+'bd'+str(self.bath)+'ba'
        try:
            self.price = self.pricelist[self.bedbath]
        except:
            self.price = '?'
        return self.bedbath

    #s2: print statement

def call_twilio():
    #call twilio api to print
    account_sid = readtxtfile()['sid']
    auth_token = readtxtfile()['token']
    client = Client(account_sid, auth_token)
    #create object from csv class
    o1 = vacancy_csv()
    if o1.tosendornot:
        text = o1.printedmsg
    else:
        text = "No updates so no need for a text message!"

    message = client.messages \
        .create(
        body=text,
        from_=readtxtfile()['from'],
        to=readtxtfile()['to']
    )
    print(message.sid)
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

# o1 = vacancy_csv()
# print(o1.printedmsg)
call_twilio()







