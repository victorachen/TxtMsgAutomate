# To do: include vacant pad category
# communicate to managers: statuses can be changed

import ezgmail, os, csv, ezsheets, glob, shutil, re
from datetime import date, datetime, timedelta
from twilio.rest import Client
from pathlib import Path

os.chdir(r'C:\Users\19097\PycharmProjects\VacancyTextScript')

# ============================================================
# DEBUG / TEST TOGGLES
# ============================================================
# normal behavior should be False, False, False
DEBUG_MODE = False
FORCE_SEND_DEBUG = False            # True = send regardless of compare()/new vacancy trigger
DEBUG_SEND_TO_VICTOR_ONLY = True    # True = only text Victor for testing


def dbg(msg):
    if DEBUG_MODE:
        print(msg)


# ============================================================
# Special Units Registry
# ============================================================
SPECIAL_UNITS = {
    'Westwind': ['Apt B'],
}

# ============================================================
# Global Property Lists
# ============================================================
ALL_PROPERTIES = [
    'Holiday', 'Mt Vista', 'Westwind', 'Crestview',
    'Hitching Post', 'SFH', 'Patrician', 'Wishing Well',
    'Avalon', 'Aladdin', 'Bonanza'
]

SFH_LIST = [
    'Chestnut', 'Elm', '12398 4th', 'Reedywoods', 'North Grove',
    'Massachusetts', 'Michigan', '906 N 4th', 'Indian School', 'Cottonwood'
]

# ============================================================
# Helpers
# ============================================================
def normalize_special_unit(raw_unit: str, prop_name: str):
    if not raw_unit or not prop_name:
        return None

    s = str(raw_unit).strip().lower().replace(' ', '')

    for special in SPECIAL_UNITS.get(prop_name, []):
        target = special.lower().replace(' ', '')
        if s == target:
            return special

    if prop_name == 'Westwind' and s in {'aptb', 'apartmentb', 'apt_b'}:
        return 'Apt B'

    return None


def fs_field_path(key: str) -> str:
    k = str(key)
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
        return k
    return f'{k}'


def natural_sort_key(s):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', str(s))]


def find_property_in_text(text, all_properties, sfh_list):
    if not text:
        return None

    text_lower = str(text).lower()

    for p in all_properties:
        if p.lower() in text_lower:
            return p

    for s in sfh_list:
        if s.lower() in text_lower:
            return s

    return None


def looks_like_standard_unit(s):
    if s is None:
        return False
    return re.match(r'^\d{1,4}[A-Za-z]?$', str(s).strip()) is not None


def abbr_propname(longpropname):
    d = {
        'Holiday': 'Hol', 'Mt Vista': 'MtV', 'Westwind': 'West', 'Crestview': 'Crest',
        'Hitching Post': 'HP', 'SFH': 'SFH', 'Patrician': 'Pat', 'Wishing Well': 'Wish',
        'Avalon': 'Av', 'Aladdin': 'Al', 'Bonanza': 'Bon',
        'Chestnut': 'Chestnut', 'Elm': 'Elm', '12398 4th': '12398 4th',
        'Reedywoods': 'Reedywd', 'North Grove': 'Grove',
        'Massachusetts': 'Massachu', 'Michigan': 'Mich', '906 N 4th': '906 N 4th',
        'Indian School': 'Indian School', 'Cottonwood': 'Cottonwd'
    }
    return d.get(longpropname, longpropname)


def is_sfh_name(name):
    if not name:
        return False
    name_lower = str(name).lower()
    return any(x.lower() in name_lower for x in SFH_LIST)


def parse_appfolio_csv(filepath):
    """
    Current AppFolio layout:
    - row 0 = header
    - group rows like: ['-> Bonanza ...', '', '', ...]
    - detail rows:
        col 0 = ''
        col 1 = unit
        col 15 = property
    """
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    parsed = []
    current_group_prop = None

    for idx, row in enumerate(rows):
        if not row:
            continue

        first = str(row[0]).strip() if len(row) > 0 else ''
        unit_col = str(row[1]).strip() if len(row) > 1 else ''
        prop_col = str(row[15]).strip() if len(row) > 15 else ''

        if idx == 0 and first == 'Group':
            continue

        if first.startswith('->'):
            current_group_prop = find_property_in_text(first, ALL_PROPERTIES, SFH_LIST)
            continue

        if unit_col in {'', 'Total'}:
            continue

        prop_name = find_property_in_text(prop_col, ALL_PROPERTIES, SFH_LIST) or current_group_prop

        if not prop_name:
            continue

        if prop_name in SFH_LIST or is_sfh_name(prop_name) or is_sfh_name(prop_col):
            parsed.append({
                'prop_name': prop_name,
                'unit': 'House',
                'raw_row': row
            })
            continue

        norm_special = normalize_special_unit(unit_col, prop_name)
        final_unit = norm_special if norm_special else unit_col

        if looks_like_standard_unit(final_unit) or norm_special:
            parsed.append({
                'prop_name': prop_name,
                'unit': str(final_unit).strip(),
                'raw_row': row
            })

    return parsed


def summarize_nonzero_property_counts(dic_obj):
    pieces = []
    for k, v in dic_obj.items():
        if len(v) > 0:
            pieces.append(f"{abbr_propname(k)}={len(v)}")
    return ", ".join(pieces) if pieces else "(none)"


# ============================================================
# New vacancy alert block
# ============================================================
def Add_To_Textmsg_Body():
    today = date.today()
    yesterday = today - timedelta(days=1)
    path = r'C:\Users\19097\PycharmProjects\VacancyTextScript\module_update'

    def download_csvs():
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        if len(thread) < 2:
            raise Exception("Not enough Gmail threads found for today/yesterday vacancy CSV download.")
        thread[0].messages[0].downloadAllAttachments(downloadFolder=path)
        thread[1].messages[0].downloadAllAttachments(downloadFolder=path)

    def clear_downloadfolder():
        removed = 0
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    removed += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    removed += 1
            except Exception as e:
                dbg(f"[DBG] clear_downloadfolder fail: {e}")
        dbg(f"[DBG] module_update cleared: {removed} item(s)")

    def extract_csv_data(date_obj):
        filename = (
            r'C:\Users\19097\PycharmProjects\VacancyTextScript\module_update\unit_vacancy_detail-'
            + str(date_obj).replace('-', '')
            + '.csv'
        )
        parsed = parse_appfolio_csv(filename)
        dbg(f"[DBG] parsed {os.path.basename(filename)} -> {len(parsed)} units")
        return parsed

    def extract_vacunits(parsed_rows):
        vacant_list = []
        for item in parsed_rows:
            prop_name = item['prop_name']
            unit = item['unit']
            combined = abbr_propname(prop_name) + (' ' + unit if unit != 'House' else '')
            vacant_list.append(combined.strip())
        return vacant_list

    def compare(today_lst, yest_lst):
        new_vacants = [u for u in today_lst if u not in yest_lst]
        return ", ".join(new_vacants)

    download_csvs()
    todays_parsed = extract_csv_data(today)
    yest_parsed = extract_csv_data(yesterday)
    todays_vacunits = extract_vacunits(todays_parsed)
    yest_vacunits = extract_vacunits(yest_parsed)
    clear_downloadfolder()

    new_vacants_string = compare(todays_vacunits, yest_vacunits)
    dbg(f"[DBG] new vacancies found: {new_vacants_string if new_vacants_string else '(none)'}")

    if new_vacants_string:
        return "New Vacancy! (Plz Update): " + new_vacants_string + "\n"
    return ""


def is_it_time_baby():
    import datetime as _dt
    now = _dt.datetime.now()
    today9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    today905am = now.replace(hour=9, minute=5, second=0, microsecond=0)
    return today9am < now < today905am


class vacancy_csv(object):
    def __init__(self):
        self.beginning = Add_To_Textmsg_Body()

        self.printedmsg = ""
        self.printedmsg_number2 = ""

        self._sms2_update_lines = []
        self._sms2_rent_ready_block = ""
        self._sms2_footer = "Full vacancy details can be found on the new website!: https://vacant.streamlit.app/"

        self.tosendornot = False
        self.data = []
        self.parsed_units = []
        self.vac_list = []
        self.properties = ALL_PROPERTIES[:]
        self.SFH = SFH_LIST[:]
        self.dic = {
            'Holiday': {}, 'Mt Vista': {}, 'Westwind': {},
            'Avalon': {}, 'Aladdin': {}, 'Bonanza': {},
            'Crestview': {}, 'Hitching Post': {}, 'SFH': {}, 'Patrician': {}, 'Wishing Well': {},
            'Chestnut': {}, 'Elm': {}, '12398 4th': {}, 'Reedywoods': {}, 'North Grove': {},
            'Massachusetts': {}, 'Michigan': {}, '906 N 4th': {}, 'Indian School': {}, 'Cottonwood': {}
        }
        self.statuslist = [
            'Rent Ready', 'Recently Vacated - Needs Work', 'Rented',
            'New Coach/Construction', 'Empty Lot', 'No Status (Please Update)'
        ]

        self.ss = ezsheets.Spreadsheet('1Jn3vSrRxB3j1oZab3QZd1gnFczyndmLEbeUqn_JaEkU')

        self.scrapegmail()
        self.read_csv()
        self.create_dic()
        self.gsheets()
        self.sorted_dic_func()
        self._build_sms2_rent_ready_block()
        self.compare()
        self._finalize_sms2()
        self.txtmsg()
        self.firestore()
        self.skimthefat()

    def scrapegmail(self):
        ezgmail.init()
        thread = ezgmail.search('Batcave located in vacancy')
        if len(thread) == 0:
            raise Exception("No Gmail threads found for vacancy CSV download.")
        thread[0].messages[0].downloadAllAttachments(
            downloadFolder=r'C:\Users\19097\PycharmProjects\VacancyTextScript'
        )

    def read_csv(self):
        s3 = "unit_vacancy_detail-" + str(date.today()).replace('-', '') + '.csv'
        with open(s3, newline='', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            self.data = list(reader)

        self.parsed_units = parse_appfolio_csv(s3)

        dbg(f"[DBG] CSV rows={len(self.data)} | parsed units={len(self.parsed_units)}")
        return self.data

    def is_SFH(self, string):
        if not string:
            return False
        string_lower = str(string).lower()
        for i in self.SFH:
            if i.lower() in string_lower:
                return True
        return False

    def is_unit(self, unit_str, prop_name=None):
        if not unit_str:
            return False
        s = str(unit_str).strip()
        if re.match(r'^\d{1,4}[A-Za-z]?$', s):
            return True
        if prop_name and normalize_special_unit(s, prop_name):
            return True
        return False

    def is_prop(self, string):
        if not string:
            return False
        return find_property_in_text(string, self.properties, self.SFH) is not None

    def which_prop(self, string):
        if not string:
            return None
        return find_property_in_text(string, self.properties, self.SFH)

    def create_dic(self):
        created_count = 0
        duplicate_count = 0

        for item in self.parsed_units:
            prop_name = item['prop_name']
            unit = item['unit']

            if prop_name not in self.dic:
                continue

            if unit in self.dic[prop_name]:
                duplicate_count += 1

            obj = Unit(prop_name, unit)
            self.dic[prop_name][unit] = obj
            created_count += 1

        dbg(f"[DBG] create_dic created={created_count} duplicates_overwritten={duplicate_count}")
        dbg(f"[DBG] create_dic nonzero props: {summarize_nonzero_property_counts(self.dic)}")

    def in_dic(self, complex, unit):
        try:
            self.dic[complex][unit]
        except:
            return False
        return True

    def gsheets(self):
        sheet = self.ss[0]
        matched_rows = 0
        unmatched_rows = 0

        for i in sheet:
            if len(i) < 9:
                continue

            if len(i[0]) > 0 and str(i[0]).strip() == 'Timestamp':
                continue

            if self.is_SFH(i[1]):
                complex = i[1].replace(" House", "")
                unit = 'House'
            else:
                complex = i[1]
                unit = i[2]

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
                matched_rows += 1
            else:
                if len(i[0]) > 0:
                    unmatched_rows += 1

        dbg(f"[DBG] gsheets matched={matched_rows} unmatched={unmatched_rows}")
        return self.dic

    def compare(self):
        with open('old.csv', newline='', encoding='utf-8-sig') as old_file:
            reader1 = csv.reader(old_file)
            data1 = list(reader1)

        self.ss.downloadAsCSV()

        with open('new.csv', newline='', encoding='utf-8-sig') as new_file:
            reader2 = csv.reader(new_file)
            data2 = list(reader2)

        self.newdata = data2

        oldstamps = [(i[0] if len(i) > 0 else "") for i in data1]
        newstamps = [(i[0] if len(i) > 0 else "") for i in data2]

        dbg(f"[DBG] compare old rows={len(oldstamps)} new rows={len(newstamps)}")
        dbg(f"[DBG] compare last old stamp={oldstamps[-1] if oldstamps else '(none)'}")
        dbg(f"[DBG] compare last new stamp={newstamps[-1] if newstamps else '(none)'}")

        if oldstamps == newstamps:
            self.tosendornot = False
            self.updated_lines = []
            dbg("[DBG] compare: no form updates")
            return False

        self.updated_lines = []
        self.tosendornot = True

        ind = -1
        for stamp in oldstamps:
            try:
                if len(stamp) > 0:
                    ind = oldstamps.index(stamp)
            except:
                pass

        self.updated_lines.extend(data2[ind + 1:])
        self.update_old()
        self.update_announcement()
        dbg(f"[DBG] compare: updates found={len(self.updated_lines)}")
        return True

    def update_old(self):
        with open('old.csv', 'w', newline='', encoding='utf-8-sig') as outputFile:
            outputWriter = csv.writer(outputFile)
            for i in self.newdata:
                outputWriter.writerow(i)

    def update_announcement(self):
        s = ""
        personlist = []
        for i in self.updated_lines:
            person = i[8] if len(i) > 8 else ""
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
                norm_unit = normalize_special_unit(i[2], i[1]) or i[2]
                space = str(norm_unit).strip()

            if count < len(self.updated_lines):
                s += prop + " " + space + ", "
            else:
                s += prop + " " + space

        self.printedmsg = s + '\n' + self.printedmsg

        lines = []
        seen = set()

        for row in self.updated_lines:
            person = str(row[8]).strip() if len(row) > 8 else ""
            if not person:
                person = "Someone"

            if self.is_SFH(row[1]):
                prop_abbr = self.abbr_complex(row[1].replace(" House", ""))
                unit_disp = "House"
            else:
                prop_abbr = self.abbr_complex(row[1])
                unit_norm = normalize_special_unit(row[2], row[1]) or row[2]
                unit_disp = str(unit_norm).strip()

            line = f"{person} updated {prop_abbr} {unit_disp}"
            if line not in seen:
                seen.add(line)
                lines.append(line)

        self._sms2_update_lines = lines

    def sorted_dic_func(self):
        self.sorted_dic = {}
        for i in self.statuslist:
            self.sorted_dic[i] = {}

        for prop in self.dic:
            for unit in self.dic[prop]:
                a = self.dic[prop][unit]
                try:
                    self.sorted_dic[a.status][a.complex + ' ' + a.unit] = a
                except:
                    pass

        dbg(
            "[DBG] status counts | "
            + " | ".join([
                f"RR={len(self.sorted_dic['Rent Ready'])}",
                f"UT={len(self.sorted_dic['Recently Vacated - Needs Work'])}",
                f"R={len(self.sorted_dic['Rented'])}",
                f"NC={len(self.sorted_dic['New Coach/Construction'])}",
                f"EL={len(self.sorted_dic['Empty Lot'])}",
                f"NS={len(self.sorted_dic['No Status (Please Update)'])}"
            ])
        )
        return self.sorted_dic

    def abbr_complex(self, complex):
        d = {
            'Holiday': 'Hol', 'Mt Vista': 'MtV', 'Westwind': 'West', 'Crestview': 'Crest',
            'Avalon': 'Av', 'Aladdin': 'Al', 'Bonanza': 'Bon',
            'Hitching Post': 'HP', 'SFH': 'SFH', 'Patrician': 'Pat', 'Wishing Well': 'Wish',
            'Chestnut': 'Chestnut', 'Elm': 'Elm', '12398 4th': '12398 4th',
            'Reedywoods': 'Reedywd', 'North Grove': 'Grove',
            'Massachusetts': 'Massachu', 'Michigan': 'Mich',
            '906 N 4th': '906 N 4th', 'Indian School': 'Indian School', 'Cottonwood': 'Cottonwd'
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

    def _build_sms2_rent_ready_block(self, max_lines=40):
        try:
            rentready = self.sorted_dic.get('Rent Ready', {})
        except Exception:
            rentready = {}

        if not rentready or len(rentready) == 0:
            self._sms2_rent_ready_block = "Current Rent Ready Units:\n(None)\n"
            return self._sms2_rent_ready_block

        items = sorted(rentready.items(), key=lambda kv: natural_sort_key(kv[0]))

        lines = ["Current Rent Ready Units:"]
        count = 0
        for _, obj in items:
            count += 1
            if count > max_lines:
                remaining = max(0, len(items) - max_lines)
                lines.append(f"...and {remaining} more")
                break

            complex_abbr = self.abbr_complex(obj.complex)
            unit = obj.unit
            try:
                type_part = self.abbr_type(obj.unittype)
            except Exception:
                type_part = "(?/?)"

            asking = str(obj.askingrent).strip()
            if asking == "" or asking.lower() == "empty":
                asking = "?"

            lines.append(f"- {complex_abbr} {unit} {type_part} - ${asking}")

        self._sms2_rent_ready_block = "\n".join(lines) + "\n"
        return self._sms2_rent_ready_block

    def _finalize_sms2(self):
        parts = []

        if self._sms2_update_lines:
            parts.append("\n".join(self._sms2_update_lines))

        if self._sms2_update_lines and self._sms2_rent_ready_block:
            parts.append(self._sms2_rent_ready_block.rstrip())

        if self._sms2_update_lines:
            parts.append(self._sms2_footer)

        self.printedmsg_number2 = "\n\n".join([p for p in parts if str(p).strip()]) if parts else ""
        return self.printedmsg_number2

    def firestore(self):
        import firebase_admin
        from firebase_admin import credentials
        from firebase_admin import firestore as _firestore

        cred_path = r'C:\Users\19097\PycharmProjects\VacancyTextScript\serviceaccountkey.json'
        cred = credentials.Certificate(cred_path)

        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(cred)

        db = _firestore.client()

        dbg(f"[DBG] firestore using cred file: {cred_path}")
        try:
            dbg(f"[DBG] firebase project id: {app.project_id}")
        except Exception as e:
            dbg(f"[DBG] could not read firebase project id: {e}")

        L = ['just_rented', 'no_status', 'recently_updated', 'rent_ready', 'under_construction', 'empty_lots',
             'unit_turns']

        for i in L:
            db.collection('Vacancy').document(i).delete()
        for i in L:
            db.collection('Vacancy').document(i).set({'type': i})

        rr_count = 0
        ut_count = 0
        jr_count = 0
        uc_count = 0
        el_count = 0
        ns_count = 0

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
            rr_count += 1

        # Unit Turns
        for i in self.sorted_dic['Recently Vacated - Needs Work']:
            complex = self.sorted_dic['Recently Vacated - Needs Work'][i].complex
            unit = self.sorted_dic['Recently Vacated - Needs Work'][i].unit
            unittype = self.sorted_dic['Recently Vacated - Needs Work'][i].unittype

            raw_key = self.abbr_complex(complex) + "_" + unit
            key = fs_field_path(raw_key)
            value = self.abbr_type(unittype)
            db.collection('Vacancy').document('unit_turns').update({key: value})
            ut_count += 1

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
            jr_count += 1

        # Under Construction
        for i in self.sorted_dic['New Coach/Construction']:
            complex = self.abbr_complex(self.sorted_dic['New Coach/Construction'][i].complex)
            unit = self.sorted_dic['New Coach/Construction'][i].unit

            raw_key = complex + "_" + unit
            key = fs_field_path(raw_key)
            value = self.sorted_dic['New Coach/Construction'][i].notes if str(
                self.sorted_dic['New Coach/Construction'][i].notes
            ).strip() not in {'', 'Empty'} else ""
            db.collection('Vacancy').document('under_construction').update({key: value})
            uc_count += 1

        # Empty Lots
        for i in self.sorted_dic['Empty Lot']:
            complex = self.abbr_complex(self.sorted_dic['Empty Lot'][i].complex)
            unit = self.sorted_dic['Empty Lot'][i].unit

            raw_key = complex + "_" + unit
            key = fs_field_path(raw_key)
            value = ""
            db.collection('Vacancy').document('empty_lots').update({key: value})
            el_count += 1

        # No Status
        for i in self.sorted_dic['No Status (Please Update)']:
            complex = self.abbr_complex(self.sorted_dic['No Status (Please Update)'][i].complex)
            unit = self.sorted_dic['No Status (Please Update)'][i].unit

            raw_key = complex + "_" + unit
            key = fs_field_path(raw_key)
            value = ""
            db.collection('Vacancy').document('no_status').update({key: value})
            ns_count += 1

        dbg(f"[DBG] firestore writes RR={rr_count} UT={ut_count} R={jr_count} NC={uc_count} EL={el_count} NS={ns_count}")

        # READ-BACK VERIFICATION
        try:
            rr_doc = db.collection('Vacancy').document('rent_ready').get()
            ut_doc = db.collection('Vacancy').document('unit_turns').get()
            jr_doc = db.collection('Vacancy').document('just_rented').get()
            uc_doc = db.collection('Vacancy').document('under_construction').get()
            el_doc = db.collection('Vacancy').document('empty_lots').get()
            ns_doc = db.collection('Vacancy').document('no_status').get()

            rr_data = rr_doc.to_dict() or {}
            ut_data = ut_doc.to_dict() or {}
            jr_data = jr_doc.to_dict() or {}
            uc_data = uc_doc.to_dict() or {}
            el_data = el_doc.to_dict() or {}
            ns_data = ns_doc.to_dict() or {}

            dbg(
                "[DBG] firestore readback | "
                f"RR={max(0, len(rr_data) - 1)} "
                f"UT={max(0, len(ut_data) - 1)} "
                f"R={max(0, len(jr_data) - 1)} "
                f"NC={max(0, len(uc_data) - 1)} "
                f"EL={max(0, len(el_data) - 1)} "
                f"NS={max(0, len(ns_data) - 1)}"
            )

            dbg(f"[DBG] firestore sample RR keys: {list(rr_data.keys())[:8]}")
        except Exception as e:
            dbg(f"[DBG] firestore readback failed: {e}")

    def txtmsg(self):
        string = ""
        string += "\n"
        string += "Rent Ready:\n"
        string += "-  -  -  -  -  -\n"

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
            L.append(complex + " " + unit)
        string += ", ".join(L) + "\n"

        string += "\n"
        string += "Empty Lots:\n"
        string += "-  -  -  -  -  -\n"
        L = []
        for i in emptylot:
            complex = self.abbr_complex(emptylot[i].complex)
            unit = emptylot[i].unit
            L.append(complex + " " + unit)
        string += ", ".join(L) + "\n"

        string += "\n"
        string += "No Status:\n"
        string += "-  -  -  -  -  -\n"
        L2 = []
        for i in nostatus:
            complex = self.abbr_complex(nostatus[i].complex)
            unit = nostatus[i].unit
            L2.append(complex + " " + unit)
        string += ", ".join(L2) + "\n"

        string += "\n"
        string += "https://forms.gle/ZJminE5umWn9E8YM6"
        string += "\n"

        if is_it_time_baby():
            self.printedmsg = self.beginning + self.printedmsg + string
        else:
            self.printedmsg = self.printedmsg + string

        dbg(f"[DBG] SMS lengths | sms1={len(self.printedmsg)} sms2={len(self.printedmsg_number2)}")

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
        dbg(f"[DBG] skimthefat removed={count}")


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
    d = {
        'Victor': '+19098163161', 'Jian': '+19092101491', 'Karla': '+19097677208',
        'Bathshua': '+19097140840', 'Richard': '+19516639308', 'Jeff': '+19092228209',
        'Hector': '+19094897033', 'Rick': '+19092541913', 'Debbie': '+17605141103',
        'Megan': '+13237192726', 'Alexandra': '+19513509693', 'Brian': '+19092678862'
    }
    if DEBUG_SEND_TO_VICTOR_ONLY:
        return [d['Victor']]
    return list(d.values())


def call_twilio():
    def are_there_new_vacs():
        return Add_To_Textmsg_Body() != "" and is_it_time_baby()

    L = numberstomessage()
    account_sid = readtxtfile()['sid']
    auth_token = readtxtfile()['token']
    client = Client(account_sid, auth_token)
    o1 = vacancy_csv()

    text = o1.printedmsg
    text2 = o1.printedmsg_number2

    dbg("[DBG] ----- SMS1 START -----")
    dbg(text)
    dbg("[DBG] ----- SMS1 END -----")

    dbg("[DBG] ----- SMS2 START -----")
    dbg(text2 if text2.strip() else "(empty)")
    dbg("[DBG] ----- SMS2 END -----")

    current_new_vacs = are_there_new_vacs()
    should_send = FORCE_SEND_DEBUG or o1.tosendornot or current_new_vacs

    dbg(f"[DBG] send? force={FORCE_SEND_DEBUG} tosendornot={o1.tosendornot} new_vacs_now={current_new_vacs}")
    dbg(f"[DBG] final should_send={should_send}")
    dbg(f"[DBG] recipients={L}")

    if should_send:
        for number in L:
            client.messages.create(
                body=text,
                from_=readtxtfile()['from'],
                to=number
            )
            if text2.strip():
                client.messages.create(
                    body=text2,
                    from_=readtxtfile()['from'],
                    to=number
                )
        dbg("[DBG] texts sent")
    else:
        dbg("[DBG] texts not sent")

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


call_twilio()