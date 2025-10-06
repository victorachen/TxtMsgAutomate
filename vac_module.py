# To do: include vacant pad category
# communicate to managers: statuses can be changed
import ezgmail, os, csv, ezsheets, glob, shutil, re
from datetime import date, datetime, timedelta
from twilio.rest import Client
from pathlib import Path

os.chdir(r'C:\Users\19097\PycharmProjects\VacancyTextScript')

# =========================
# Special Units Registry
# =========================
# Keyed by canonical property name exactly as used in self.properties (e.g., 'Westwind')
# Values are canonical, display-ready unit strings.
SPECIAL_UNITS = {
    'Westwind': ['Apt B'],
    # Add more as needed, e.g.:
    # 'Westwind': ['Apt A', 'Apt B'],
    # 'Holiday': ['Office'],
}

def normalize_special_unit(raw_unit: str, prop_name: str):
    """
    Normalize input like 'apt b', 'APT  B', 'aptb' to canonical 'Apt B' (if registered).
    Returns canonical unit string if recognized for prop_name, else None.
    """
    if not raw_unit or not prop_name:
        return None
    s = str(raw_unit).strip().lower().replace(' ', '')

    # direct match against registered special units for this property
    for special in SPECIAL_UNITS.get(prop_name, []):
        target = special.lower().replace(' ', '')
        if s == target:
            return special

    # convenience aliases for Westwind/Apt B
    if prop_name == 'Westwind' and s in {'aptb', 'apartmentb', 'apt_b'}:
        return 'Apt B'

    return None

# =========================
# Firestore field-path escaper
# =========================
def fs_field_path(key: str) -> str:
    """
    Firestore's update() parses dict keys as *field paths*. Keys containing spaces or other
    non-alphanumerics must be escaped with backticks.
    """
    k = str(key).replace('`', r'\`')
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
        return k
    return f'`{k}`'


# Aug 6th: 2022 -- we want to add functionality where: if there is a new vacant unit in AppFolio,
# the code sends out a text msg alert to everyone
# we are going to try to do as much of this outside the class as possible (waay too messy inside the class)
def Add_To_Textmsg_Body():
    # first: pull both csv's and store data in lists
    today = date.today()
    yesterday = today - timedelta(days=1)
    path = r'C:\Users\19097\PycharmProjects\VacancyTextScript\module_update'

    def download_csvs():
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        # (1) Download the most recent vacancy csv
        thread[0].messages[0].downloadAllAttachments(downloadFolder=path)
        # (2) Download yesterday's csv
        thread[1].messages[0].downloadAllAttachments(downloadFolder=path)

    # after it's all said and done, clear everything from the "module_update" folder
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

    # helper function: given a date, scrape through gmail to find the corresponding csv file
    # --> and then spit that csv file data into a list (returned)
    def extract_csv_data(date_obj):
        firsthalf = r'C:\Users\19097\PycharmProjects\VacancyTextScript\module_update\unit_vacancy_detail-'
        secondhalf = str(date_obj).replace('-', '') + '.csv'
        filename = firsthalf + secondhalf
        file = open(filename, newline='')
        reader = csv.reader(file)
        data = list(reader)
        return data

    all_properties = ['Holiday', 'Mt Vista', 'Westwind', 'Crestview',
                      'Hitching Post', 'SFH', 'Patrician', 'Wishing Well',
                      'Avalon', 'Aladdin', 'Bonanza']

    SFH = ['Chestnut', 'Elm', '12398 4th', 'Reedywoods', 'North Grove',
           'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood']

    # 1a: given a row (list), return whether that csv row is a unit (handles special units like 'Apt B')
    def isunit(row):
        if len(row) < 2:
            return False

        unit_str = str(row[0]).strip()
        prop_address = str(row[-1])

        # find which property this row belongs to
        def which_prop_from_address(addr):
            for p in all_properties:
                if p in addr:
                    return p
            for sfh in SFH:
                if sfh in addr:
                    return 'SFH'
            return None

        prop_name = which_prop_from_address(prop_address)

        # numeric-ish acceptor (legacy)
        def looks_like_standard_unit(s):
            return re.match(r'^\d{1,4}[A-Za-z]?$', s.strip()) is not None

        # NEW: allow registered special units (e.g., 'Apt B' at Westwind)
        is_special = False
        if prop_name:
            normalized = normalize_special_unit(unit_str, prop_name)
            if normalized:
                is_special = True

        # SFH path
        is_sfh = any(s in prop_address for s in SFH) and (len(row) > 7)

        # tie back to your props to avoid false positives
        in_known_prop = any(p in prop_address for p in all_properties)

        return ((looks_like_standard_unit(unit_str) or is_special) and in_known_prop) or is_sfh

    # 2a: todays_csvoutput --> strips --> todays_vacunits
    def extract_vacunits(csvoutput):

        # Helper: given a long address list "Hitching Post - 34642 Yucaipa Blvd Yucaipa, CA 92399", abbreviate to "HP"
        def abbr_propname(longpropname):
            d = {'Holiday': 'Hol', 'Mt Vista': 'MtV', 'Westwind': 'West', 'Crestview': 'Crest',
                 'Hitching Post': 'HP', 'SFH': 'SFH', 'Patrician': 'Pat', 'Wishing Well': 'Wish',
                 'Avalon': 'Av', 'Aladdin': 'Al', 'Bonanza': 'Bon',
                 'Chestnut': 'Chestnut', 'Elm': 'Elm', '12398 4th': '12398 4th',
                 'Reedywoods': 'Reedywd', 'North Grove': 'Grove',
                 'Massachusetts': 'Massachu', 'Michigan': 'Mich', '906 N 4th': '906 N 4th',
                 'Indian School': 'Indian School', 'Cottonwood': 'Cottonwd'
                 }
            for i in d:
                if i in longpropname:
                    return d[i]
            return 'Uh Oh, No Matches!'

        def is_SFH(longpropname):
            for i in SFH:
                if i in longpropname:
                    return True
            return False

        vacant_list = []
        for row in csvoutput:
            if isunit(row):
                if is_SFH(row[-1]):
                    space_num = ''
                else:
                    space_num = row[0]
                prop_name = abbr_propname(row[-1])
                combined = prop_name + ' ' + str(space_num).strip()
                vacant_list.append(combined)
        return vacant_list

    # 3A: compares today's and yesterday's vacant lists; returns third list of new vacants (in string format)
    def compare(today_lst, yest_lst):
        new_vacants = []
        string = ''
        for unit in today_lst:
            if unit not in yest_lst:
                new_vacants.append(unit)
        for i in new_vacants:
            if new_vacants.index(i) == 0:
                string = i + string
            else:
                string = i + ', ' + string
        return string

    # 3B:
    def are_there_any_new_vacants(today_lst, yest_lst):
        return compare(today_lst, yest_lst) != ''

    download_csvs()
    todays_csvoutput = extract_csv_data(today)
    yest_csvoutput = extract_csv_data(yesterday)
    todays_vacunits = extract_vacunits(todays_csvoutput)
    yest_vacunits = extract_vacunits(yest_csvoutput)
    clear_downloadfolder()
    if are_there_any_new_vacants(todays_vacunits, yest_vacunits):
        text_PtA = "New Vacancy! (Plz Update): "
        text_PtB = compare(todays_vacunits, yest_vacunits)
        return text_PtA + text_PtB + """\n"""
    return ""


# we don't want this to run every 5 minutes if there is a vacancy!
# so we want this to run only if it is between the times of 8am and 8:05 am (Helper Below)
def is_it_time_baby():
    import datetime as _dt
    now = _dt.datetime.now()
    today9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    today905am = now.replace(hour=9, minute=5, second=0, microsecond=0)
    return today9am < now < today905am


class vacancy_csv(object):
    # returns Data set from AppFolio Vacancy (using def read_csv)
    def __init__(self):
        self.beginning = Add_To_Textmsg_Body()
        self.printedmsg = ""
        self.tosendornot = False
        self.data = []
        self.d = {}
        self.vac_list = []
        self.properties = ['Holiday', 'Mt Vista', 'Westwind', 'Crestview',
                           'Hitching Post', 'SFH', 'Patrician', 'Wishing Well',
                           'Avalon', 'Aladdin', 'Bonanza']
        self.SFH = ['Chestnut', 'Elm', '12398 4th', 'Reedywoods', 'North Grove',
                    'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood']
        self.dic = {'Holiday': {}, 'Mt Vista': {}, 'Westwind': {},
                    'Avalon': {}, 'Aladdin': {}, 'Bonanza': {},
                    'Crestview': {}, 'Hitching Post': {}, 'SFH': {}, 'Patrician': {}, 'Wishing Well': {},
                    'Chestnut': {}, 'Elm': {}, '12398 4th': {}, 'Reedywoods': {}, 'North Grove': {},
                    'Massachusetts': {}, 'Michigan': {}, '906 N 4th': {}, 'Indian School': {}, 'Cottonwood': {}}
        self.statuslist = ['Rent Ready', 'Recently Vacated - Needs Work', 'Rented',
                           'New Coach/Construction', 'Empty Lot', 'No Status (Please Update)']
        self.ss = ezsheets.Spreadsheet('1Jn3vSrRxB3j1oZab3QZd1gnFczyndmLEbeUqn_JaEkU')
        self.scrapegmail()
        self.read_csv()
        self.create_dic()
        self.gsheets()
        self.sorted_dic()
        self.compare()
        self.txtmsg()
        self.firestore()
        self.skimthefat()

    def scrapegmail(self):
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        thread[0].messages[0].downloadAllAttachments(downloadFolder=r'C:\Users\19097\PycharmProjects\VacancyTextScript')
        return None

    def read_csv(self):
        s1 = "unit_vacancy_detail-"
        today = date.today()
        s2 = str(today).replace('-', '') + '.csv'
        s3 = s1 + s2
        file = open(s3, newline='')
        reader = csv.reader(file)
        self.data = list(reader)
        return self.data

    def is_SFH(self, string):
        SFH_list = ['Chestnut', 'Elm', '12398 4th', 'Reedywoods', 'North Grove',
                    'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood']
        for i in SFH_list:
            if i in string:
                return True
        return False

    def is_unit(self, unit_str, prop_name=None):
        """
        Accepts standard numeric units (e.g., 12, 12A) OR registered special units (e.g., 'Apt B' at Westwind).
        prop_name can be passed if known for special-unit matching.
        """
        if not unit_str:
            return False
        s = str(unit_str).strip()
        if re.match(r'^\d{1,4}[A-Za-z]?$', s):
            return True
        if prop_name:
            if normalize_special_unit(s, prop_name):
                return True
        else:
            for p in SPECIAL_UNITS:
                if normalize_special_unit(s, p):
                    return True
        return False

    def is_prop(self, string):
        for i in self.properties:
            if i in string:
                return True
        return False

    # 2.21.25 update: case sensitive
    def which_prop(self, string):
        if not string:
            return None
        string_lower = string.lower().strip()
        for i in self.properties:
            if i.lower() in string_lower:
                return i
        for x in self.SFH:
            if x.lower() in string_lower:
                return x
        print(f"which_prop() returning None for unexpected string: '{string}'")
        return None

    def create_dic(self):
        for i in self.data:
            if len(i) > 2:
                unit_raw = i[0]
                prop = i[-1]

                if not prop:
                    print(f"Skipping entry due to missing property name: {i}")
                    continue

                prop_name = self.which_prop(prop)
                if prop_name is None:
                    print(f"Warning: No match found for property '{prop}', skipping entry.")
                    continue

                # Normalize special units (e.g., 'apt b' -> 'Apt B') if applicable
                normalized_special = normalize_special_unit(unit_raw, prop_name)
                unit = normalized_special if normalized_special else str(unit_raw).strip()

                # Standard/unit path
                if self.is_unit(unit, prop_name) and self.is_prop(prop):
                    obj = Unit(prop_name, unit)
                    self.dic[prop_name].update({unit: obj})

                # SFH path
                if self.is_SFH(unit_raw):
                    obj = Unit(prop_name, 'House')
                    self.dic[prop_name].update({'House': obj})

    def in_dic(self, complex, unit):
        try:
            self.dic[complex][unit]
        except:
            return False
        return True

    def gsheets(self):
        sheet = self.ss[0]
        for i in sheet:
            if self.is_SFH(i[1]):
                complex = i[1].replace(" House", "")
                unit = 'House'
            else:
                complex = i[1]
                unit = i[2]

            # Normalize special unit text coming from Google Forms/Sheets
            norm = normalize_special_unit(unit, complex)
            if norm:
                unit = norm

            if len(i[0]) > 0 and self.in_dic(complex, unit):
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
        old_file = open('old.csv', newline='')
        reader1 = csv.reader(old_file)
        data1 = list(reader1)

        self.ss.downloadAsCSV()
        new_file = open('new.csv', newline='')
        reader2 = csv.reader(new_file)
        data2 = list(reader2)
        self.newdata = data2

        oldstamps = []
        newstamps = []
        for i in data1:
            oldstamps.append(i[0])
        for i in data2:
            newstamps.append(i[0])

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
                    if len(i[0]) > 0:
                        ind = oldstamps.index(i)
                except:
                    x = 'do nothing'
            self.updated_lines.extend(data2[ind + 1:])
            self.update_old()
            self.update_announcement()
            return True

    def update_old(self):
        outputFile = open('old.csv', 'w', newline='')
        outputWriter = csv.writer(outputFile)
        for i in self.newdata:
            outputWriter.writerow(i)
        return None

    def update_announcement(self):
        s = """"""
        personlist = []
        for i in self.updated_lines:
            person = i[8]
            if person not in personlist:
                personlist.append(person)

        for i in range(len(personlist)):
            if i < len(personlist) - 1:
                s += personlist[i] + ", "
            else:
                s += personlist[i]

        s += " updated: "

        count = 0
        for i in self.updated_lines:
            count += 1
            if self.is_SFH(i[1]):
                prop = self.abbr_complex(i[1].replace(" House", ""))
                space = "House"
            else:
                prop = self.abbr_complex(i[1])
                # Normalize unit here as well for consistency
                norm_unit = normalize_special_unit(i[2], i[1]) or i[2]
                space = str(norm_unit).strip()
            if count < len(self.updated_lines):
                s += prop + " " + space + ", "
            else:
                s += prop + " " + space

        self.printedmsg = s + '\n' + self.printedmsg
        return None

    def sorted_dic(self):
        self.sorted_dic = {}
        for i in self.statuslist:
            self.sorted_dic.update({i: {}})
        for prop in self.dic:
            for unit in self.dic[prop]:
                a = self.dic[prop][unit]
                try:
                    self.sorted_dic[a.status].update({a.complex + ' ' + a.unit: a})
                except:
                    print("the object's (that you're looping thru) status does not exist")
        return self.sorted_dic

    def abbr_complex(self, complex):
        d = {'Holiday': 'Hol', 'Mt Vista': 'MtV', 'Westwind': 'West', 'Crestview': 'Crest',
             'Avalon': 'Av', 'Aladdin': 'Al', 'Bonanza': 'Bon',
             'Hitching Post': 'HP', 'SFH': 'SFH', 'Patrician': 'Pat', 'Wishing Well': 'Wish',
             'Chestnut': 'Chestnut', 'Elm': 'Elm', '12398 4th': '12398 4th', 'Reedywoods': 'Reedywd', 'North Grove': 'Grove',
             'Massachusetts': 'Massachu', 'Michigan': 'Mich', '906 N 4th': '906 N 4th', 'Indian School': 'Indian School', 'Cottonwood': 'Cottonwd'
             }
        return d[complex]

    def abbr_type(self, unittype):
        txt = unittype
        L = [s for s in str(txt).split() if str(s).isdigit()]
        if txt == 'N/A' or len(L) < 2:
            s2 = "(?/?)"
        else:
            s2 = "(" + L[0] + "/" + L[1] + ")"
        return s2

    # Oct 5th firestore code baby!
    def firestore(self):
        import firebase_admin
        from firebase_admin import credentials
        from firebase_admin import firestore as _firestore
        cred = credentials.Certificate(r'C:\Users\19097\PycharmProjects\VacancyTextScript\serviceaccountkey.json')
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(cred)
        db = _firestore.client()

        # first: delete all existing documents (Hierarchy: collection ('vacancy') --> document ('rent_ready') --> fields )
        L = ['just_rented', 'no_status', 'recently_updated', 'rent_ready', 'under_construction', 'empty_lots', 'unit_turns']
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

            raw_key = self.abbr_complex(complex) + "_" + unit
            key = fs_field_path(raw_key)
            value = self.abbr_type(unittype) + "-$" + askingrent

            db.collection('Vacancy').document('rent_ready').update({key: value})

        # Unit Turns
        for i in self.sorted_dic['Recently Vacated - Needs Work']:
            complex = self.sorted_dic['Recently Vacated - Needs Work'][i].complex
            unit = self.sorted_dic['Recently Vacated - Needs Work'][i].unit
            unittype = self.sorted_dic['Recently Vacated - Needs Work'][i].unittype

            raw_key = self.abbr_complex(complex) + "_" + unit
            key = fs_field_path(raw_key)
            value = self.abbr_type(unittype)
            db.collection('Vacancy').document('unit_turns').update({key: value})

        # Just Rented
        for i in self.sorted_dic['Rented']:
            complex = self.sorted_dic['Rented'][i].complex
            unit = self.sorted_dic['Rented'][i].unit
            actualrent = self.sorted_dic['Rented'][i].actualrent
            unittype = self.sorted_dic['Rented'][i].unittype

            raw_key = self.abbr_complex(complex) + "_" + unit
            key = fs_field_path(raw_key)
            value = self.abbr_type(unittype) + "-$" + actualrent

            db.collection('Vacancy').document('just_rented').update({key: value})

        # Under Construction
        for i in self.sorted_dic['New Coach/Construction']:
            complex = self.abbr_complex(self.sorted_dic['New Coach/Construction'][i].complex)
            unit = self.sorted_dic['New Coach/Construction'][i].unit

            raw_key = complex + "_" + unit
            key = fs_field_path(raw_key)
            value = ""
            db.collection('Vacancy').document('under_construction').update({key: value})

        # Empty Lots
        for i in self.sorted_dic['Empty Lot']:
            complex = self.abbr_complex(self.sorted_dic['Empty Lot'][i].complex)
            unit = self.sorted_dic['Empty Lot'][i].unit

            raw_key = complex + "_" + unit
            key = fs_field_path(raw_key)
            value = ""
            db.collection('Vacancy').document('empty_lots').update({key: value})

        # No Status
        for i in self.sorted_dic['No Status (Please Update)']:
            complex = self.abbr_complex(self.sorted_dic['No Status (Please Update)'][i].complex)
            unit = self.sorted_dic['No Status (Please Update)'][i].unit

            raw_key = complex + "_" + unit
            key = fs_field_path(raw_key)
            value = ""
            db.collection('Vacancy').document('no_status').update({key: value})

    def txtmsg(self):
        string = """"""
        string += "\n"
        string += "Rent Ready:\n"
        string += "-  -  -  -  -  -\n"

        def natural_sort_key(s):
            return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', s)]

        def alphabetize_nested_dict(nested_dict):
            for key, value in nested_dict.items():
                if isinstance(value, dict):
                    nested_dict[key] = alphabetize_nested_dict(value)
            return dict(sorted(nested_dict.items(), key=lambda x: natural_sort_key(x[0])))

        rentready = alphabetize_nested_dict(self.sorted_dic['Rent Ready'])
        unitturns = alphabetize_nested_dict(self.sorted_dic['Recently Vacated - Needs Work'])
        rented = alphabetize_nested_dict(self.sorted_dic['Rented'])
        newcoach = alphabetize_nested_dict(self.sorted_dic['New Coach/Construction'])
        emptylot = alphabetize_nested_dict(self.sorted_dic['Empty Lot'])
        nostatus = alphabetize_nested_dict(self.sorted_dic['No Status (Please Update)'])

        for i in rentready:
            complex = rentready[i].complex
            unit = rentready[i].unit
            askingrent = rentready[i].askingrent
            unittype = rentready[i].unittype
            string += self.abbr_complex(complex) + " " + unit + self.abbr_type(unittype) + "- $" + askingrent + "\n"

        string += " \n"
        string += "Unit Turns:\n"
        string += "-  -  -  -  -  -\n"
        for i in unitturns:
            complex = unitturns[i].complex
            unit = unitturns[i].unit
            nextsteps = unitturns[i].notes
            if nextsteps == "":
                nextsteps = "What's next?"
            string += self.abbr_complex(complex) + " " + unit + ", "

        string += "\n"
        string += "\nRented!:\n"
        string += "-  -  -  -  -  -\n"

        for i in rented:
            complex = rented[i].complex
            unit = rented[i].unit
            actualrent = rented[i].actualrent
            unittype = rented[i].unittype
            string += self.abbr_complex(complex) + " " + unit + self.abbr_type(unittype) + "- $" + actualrent + "\n"

        string += "\n"
        string += "New Coach/Constr:\n"
        string += "-  -  -  -  -  -\n"
        L = []
        for i in newcoach:
            complex = self.abbr_complex(newcoach[i].complex)
            unit = newcoach[i].unit
            combined = complex + " " + unit
            L.append(combined)
        liststring = ''
        for x in L:
            liststring += x + ", "
        string += liststring + "\n"

        string += "\n"

        string += "Empty Lots:\n"
        string += "-  -  -  -  -  -\n"
        L = []
        for i in emptylot:
            complex = self.abbr_complex(emptylot[i].complex)
            unit = emptylot[i].unit
            combined = complex + " " + unit
            L.append(combined)
        liststring = ''
        for x in L:
            liststring += x + ", "
        string += liststring + "\n"

        string += "\n"

        string += "No Status:\n"
        string += "-  -  -  -  -  -\n"
        L2 = []
        for i in nostatus:
            complex = self.abbr_complex(nostatus[i].complex)
            unit = nostatus[i].unit
            combined = complex + " " + unit
            L2.append(combined)
        liststring2 = ''
        for x in L2:
            liststring2 += x + ", "
        string += liststring2 + "\n"

        string += "\n"
        string += "https://forms.gle/ZJminE5umWn9E8YM6"
        string += "\n"

        if is_it_time_baby():
            self.printedmsg = self.beginning + self.printedmsg + string
        else:
            self.printedmsg = self.printedmsg + string

        return None

    def skimthefat(self):
        path = r'C:\Users\19097\PycharmProjects\VacancyTextScript\*.csv'
        count = 0
        for fname in glob.glob(path):
            if 'unit_vacancy_detail' in fname:
                datestr = fname[-12:-4]
                year = datestr[2:4]
                month = datestr[4:6]
                day = datestr[6:]
                s = day + '/' + month + '/' + year
                mightbeold = datetime.strptime(s, '%d/%m/%y')
                year2 = str(date.today().year - 2000)
                month2 = str(date.today().month)
                day2 = str(date.today().day)
                s2 = day2 + '/' + month2 + '/' + year2
                todayobj = datetime.strptime(s2, '%d/%m/%y')
                if todayobj > mightbeold:
                    count += 1
                    os.remove(fname)
                    print('removed ' + fname)
        if count == 0:
            print('No milk to skim!')


class Unit(object):
    def __init__(self, complex, unit):
        self.complex = complex
        self.unit = unit
        self.unittype = 'Empty'
        self.status = 'No Status (Please Update)'
        self.notes = 'Empty'
        self.person = 'Empty'
        self.askingrent = 'Empty'
        self.actualrent = 'Empty'


def numberstomessage():
    d = {'Victor': '+19098163161', 'Jian': '+19092101491', 'Karla': '+19097677208', 'Bathshua': '+19097140840',
         'Richard': '+19516639308', 'Jeff': '+19092228209', 'Hector': '+19094897033',
         'Rick': '+19092541913', 'Debbie': '+17605141103', 'Megan': '+13237192726', 'Alexandra': '+19513509693',
         'Brian': '+19092678862'}
    L = []
    for i in d:
        L.append(d[i])
    return L


def call_twilio():
    def are_there_new_vacs():
        if Add_To_Textmsg_Body() != "" and is_it_time_baby():
            return True
        return False

    L = numberstomessage()
    account_sid = readtxtfile()['sid']
    auth_token = readtxtfile()['token']
    client = Client(account_sid, auth_token)
    o1 = vacancy_csv()
    text = o1.printedmsg
    print(text)
    numbers_to_message = L
    print(L)

    if o1.tosendornot or are_there_new_vacs():
        for number in numbers_to_message:
            client.messages.create(
                body=text,
                from_=readtxtfile()['from'],
                to=number
            )
        print('txt msg sent:')
    else:
        print('txt msg should not have sent: there are no updates so no need for a txt msg')
    return 'nothing'


def readtxtfile():
    p = Path('twiliocreds.txt')
    text = p.read_text()
    start = text.index('sid')
    sid = text[start + 5: start + 4 + 35]
    start = text.index('token')
    token = text[start + 7: start + 6 + 33]
    start = text.index('phone_from')
    phone_from = text[start + 11: start + 11 + 13]
    start = text.index('phone_to')
    phone_to = text[start + 9: start + 9 + 13]
    d = {'sid': sid, 'token': token, 'from': phone_from, 'to': phone_to}
    return d


# o1 = vacancy_csv()
# print(o1.printedmsg)
# print(o1.beginning)
# print(o1.dic)
# print(o1.sorted_dic)
# print(o1.printedmsg)

call_twilio()
