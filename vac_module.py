
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
        # print('Most recent update:')
        print('List of vacancies:')
        for status in self.sorted_dic:
            s = self.sorted_dic[status]
            if len(s) > 0:
                print("((("+status+"))):")
                for unit in s:
                    if len(s[unit].notes)>0:
                        print(s[unit].complex+" "+s[unit].unit+"-- "+s[unit].notes)
                    else:
                        print(s[unit].complex + " " +s[unit].unit)

            # for unit in self.dic[prop]:
            #     a = self.dic[prop][unit]
            #     #helper function, so you're not writing it over & over
            #     def printunit():
            #         print(a.complex + ' ' + str(a.unit) + ' (' + str(a.bed) + 'Bd/' \
            #               + str(a.bath) + 'Bth-$' + str(a.price) + ')')
            #         print('Next Steps:' + str(a.notes))
            #
            #     if a.status == 'Trash Needs To Be Cleaned Out':
            #         print('The following units need trash to be cleaned out (trailer):')
            #         printunit()
            #     if a.status == 'Undergoing Turnover':
            #         print('The following units')

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


o1 = vacancy_csv()
o1.txtmsg()
# for i in o1.dic:
#     print(o1.dic[i])
#     for x in o1.dic[i]:
#         print(x)
# print(o1.sorted_dic())
# o1.txtmsg()
# o1.dic['Holiday']['13'].status = 'something'
# o1.txtmsg()
# u= Unit('Holiday','13')
# print(u.setbedbath(3,2))
# print(u.price)
# print(u.setbedbath('?','?'))
# print(u.price)
# print(u.price)
# u.bed = 3
# u.bath = 2
# print(u.bed)
# print(u.price)







