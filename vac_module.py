
import ezgmail, os, csv, ezsheets
from datetime import date
os.chdir(r'C:\Python Files\Vacant Units')

class vacancy_csv(object):
#returns Data set from AppFolio Vacancy (using def read_csv)
    def __init__(self):
        self.data = []
        self.d = {}
        self.vac_list = []
        self.properties = ['Holiday', 'Mt Vista', 'Westwind', 'Wilson Gardens', 'Crestview',\
                            'Hitching Post', 'SFH', 'Patrician']
        self.pricing = {} #todfo
        self.dic = {'Holiday':{},'Mt Vista': {},'Westwind':{},'Wilson Gardens':{},\
                    'Crestview':{},'Hitching Post':{},'SFH':{},'Patrician':{}}
        self.ss = ezsheets.Spreadsheet('1Jn3vSrRxB3j1oZab3QZd1gnFczyndmLEbeUqn_JaEkU')
        #action items: calling helper functions
        self.scrapegmail()
        self.read_csv()
        self.create_dic()
    def scrapegmail(self):
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        thread[0].messages[0].downloadAllAttachments(downloadFolder=r'C:\Python Files\Vacant Units')
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
            if len(i)>1:
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
                notes = i[4]
                person = i[5]
                self.dic[complex][unit].status = status
                self.dic[complex][unit].notes = notes
                self.dic[complex][unit].person = person
        return None
    def txtmsg(self):
        #create print statement for mass text distribution
        return None

class Unit(object):
    def __init__(self, complex, unit):
        self.complex = complex
        self.unit = unit
        self.bed = 0
        self.bath = 0
        self.status = ''
        self.notes = ''
        self.person = ''
        self.price = 1000


    #s2: print statement


o1 = vacancy_csv()
o1.gsheets()
print(o1.dic)
print(o1.dic['Holiday']['13'].status)
print(o1.dic['Holiday']['13'].notes)
print(o1.dic['Holiday']['13'].person)
print(o1.dic['Hitching Post']['25'].status)
print(o1.dic['Hitching Post']['25'].notes)
print(o1.dic['Hitching Post']['25'].person)







