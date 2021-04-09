##install pcscd python-pyscard python-pil
import sys, re, binascii, time
from PIL import Image

# Smart Card Reader
import smartcard.System
from smartcard.util import toHexString, HexListToBinString
from smartcard.ReaderMonitoring import ReaderMonitor, ReaderObserver
from smartcard.CardMonitoring import CardMonitor, CardObserver

# Debug with print function
THAI_ID_CARD_DEBUG = False

class SmartCardReaderObserver(ReaderObserver):

    _reader_added_cb = None
    _reader_removed_cb = None

    def __init__(self, **kwargs):
        super().__init__()
        
        self._reader_added_cb = 'reader_added_callback' in kwargs.keys() and kwargs['reader_added_callback'] or None
        self._reader_removed_cb = 'reader_removed_callback' in kwargs.keys() and kwargs['reader_removed_callback'] or None

    def update(self, observable, actions):
        (added_readers, removed_readers) = actions

        if added_readers:
            if self._reader_added_cb != None:
                self._reader_added_cb(added_readers)

        if removed_readers:
            if self._reader_removed_cb != None:
                self._reader_removed_cb(removed_readers)

class SmartCardObserver(CardObserver):

    _card_insert_cb = None
    _card_remove_cb = None

    def __init__(self, **kwargs):
        super().__init__()
        
        self._card_insert_cb = 'card_insert_callback' in kwargs.keys() and kwargs['card_insert_callback'] or None
        self._card_remove_cb = 'card_remove_callback' in kwargs.keys() and kwargs['card_remove_callback'] or None

    def update(self, observable, actions):
        (added_cards, removed_cards) = actions
        
        for card in added_cards:
            if self._card_insert_cb != None:
                self._card_insert_cb()
        
        for card in removed_cards:
            if self._card_remove_cb != None:
                self._card_remove_cb()

#
# Thailand National ID Card Class
#
class ThaiIDCard:

    status = None

    smart_card_reader_monitor = None
    smart_card_reader_observer = None

    smart_card_monitor = None
    smart_card_observer = None

    #
    # Thailand National ID Card Address
    #

    # Select & Thai MOI
    SELECT = [0x00, 0xA4, 0x04, 0x00, 0x08]

    AID_MOI = [0xA0, 0x00, 0x00, 0x00, 0x54, 0x48, 0x00, 0x01]

    # APDU Type
    APDU_THAILAND_IDCARD_TYPE_01 = [0x00, 0xc0, 0x00, 0x01]
    APDU_THAILAND_IDCARD_TYPE_02 = [0x00, 0xc0, 0x00, 0x00]

    # TH Citizen ID
    CMD_CITIZEN = [0x80, 0xb0, 0x00, 0x04, 0x02, 0x00, 0x0d]
    # TH Full Name
    CMD_THFULLNAME = [0x80, 0xb0, 0x00, 0x11, 0x02, 0x00, 0x64]
    # EN Full Name
    CMD_ENFULLNAME = [0x80, 0xb0, 0x00, 0x75, 0x02, 0x00, 0x64]
    # Date of birth
    CMD_BIRTH = [0x80, 0xb0, 0x00, 0xD9, 0x02, 0x00, 0x08]
    # Gender
    CMD_GENDER = [0x80, 0xb0, 0x00, 0xE1, 0x02, 0x00, 0x01]
    # Card Issuer
    CMD_ISSUER = [0x80, 0xb0, 0x00, 0xF6, 0x02, 0x00, 0x64]
    # Issue Date
    CMD_ISSUE = [0x80, 0xb0, 0x01, 0x67, 0x02, 0x00, 0x08]
    # Expire Date
    CMD_EXPIRE = [0x80, 0xb0, 0x01, 0x6F, 0x02, 0x00, 0x08]
    # Address
    CMD_ADDRESS = [0x80, 0xb0, 0x15, 0x79, 0x02, 0x00, 0x64]

    # Photo_Part1/20
    CMD_PHOTO01 = [0x80, 0xb0, 0x01, 0x7B, 0x02, 0x00, 0xFF]
    # Photo_Part2/20
    CMD_PHOTO02 = [0x80, 0xb0, 0x02, 0x7A, 0x02, 0x00, 0xFF]
    # Photo_Part3/20
    CMD_PHOTO03 = [0x80, 0xb0, 0x03, 0x79, 0x02, 0x00, 0xFF]
    # Photo_Part4/20
    CMD_PHOTO04 = [0x80, 0xb0, 0x04, 0x78, 0x02, 0x00, 0xFF]
    # Photo_Part5/20
    CMD_PHOTO05 = [0x80, 0xb0, 0x05, 0x77, 0x02, 0x00, 0xFF]
    # Photo_Part6/20
    CMD_PHOTO06 = [0x80, 0xb0, 0x06, 0x76, 0x02, 0x00, 0xFF]
    # Photo_Part7/20
    CMD_PHOTO07 = [0x80, 0xb0, 0x07, 0x75, 0x02, 0x00, 0xFF]
    # Photo_Part8/20
    CMD_PHOTO08 = [0x80, 0xb0, 0x08, 0x74, 0x02, 0x00, 0xFF]
    # Photo_Part9/20
    CMD_PHOTO09 = [0x80, 0xb0, 0x09, 0x73, 0x02, 0x00, 0xFF]
    # Photo_Part10/20
    CMD_PHOTO10 = [0x80, 0xb0, 0x0A, 0x72, 0x02, 0x00, 0xFF]
    # Photo_Part11/20
    CMD_PHOTO11 = [0x80, 0xb0, 0x0B, 0x71, 0x02, 0x00, 0xFF]
    # Photo_Part12/20
    CMD_PHOTO12 = [0x80, 0xb0, 0x0C, 0x70, 0x02, 0x00, 0xFF]
    # Photo_Part13/20
    CMD_PHOTO13 = [0x80, 0xb0, 0x0D, 0x6F, 0x02, 0x00, 0xFF]
    # Photo_Part14/20
    CMD_PHOTO14 = [0x80, 0xb0, 0x0E, 0x6E, 0x02, 0x00, 0xFF]
    # Photo_Part15/20
    CMD_PHOTO15 = [0x80, 0xb0, 0x0F, 0x6D, 0x02, 0x00, 0xFF]
    # Photo_Part16/20
    CMD_PHOTO16 = [0x80, 0xb0, 0x10, 0x6C, 0x02, 0x00, 0xFF]
    # Photo_Part17/20
    CMD_PHOTO17 = [0x80, 0xb0, 0x11, 0x6B, 0x02, 0x00, 0xFF]
    # Photo_Part18/20
    CMD_PHOTO18 = [0x80, 0xb0, 0x12, 0x6A, 0x02, 0x00, 0xFF]
    # Photo_Part19/20
    CMD_PHOTO19 = [0x80, 0xb0, 0x13, 0x69, 0x02, 0x00, 0xFF]
    # Photo_Part20/20
    CMD_PHOTO20 = [0x80, 0xb0, 0x14, 0x68, 0x02, 0x00, 0xFF]

    # Expire time of data -- seconds
    _read_expire_time = 5 #

    # Thai Citizen ID
    _citizen = None
    _citizen_t = 0
    # Thai Full Name
    _full_name_th = None
    _full_name_th_t = 0
    # English Full Name
    _full_name_en = None
    _full_name_en_th = 0
    # Date of birth
    _birth = None
    _birth_t = 0
    # Gender
    _gender = None
    _gender_t = 0
    # Card Issuer
    _issuer = None
    _issuer_t = 0
    # Issue Date
    _issue = None
    _issue_t = 0
    # Expire Date
    _expire = None
    _expire_t = 0
    # Address
    _address = None
    _address_t = 0
    # Photo
    _photo = None
    _photo_t = 0

    def __init__(self):
        self.readerList = []

        if(len(self.getReaders()) > 0):
            self.connect(0)

    def readerMonitor(self, reader_added_cb, reader_removed_cb):
        self.reader_added_cb = reader_added_cb
        self.reader_removed_cb = reader_removed_cb
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: Add SmartCard reader observer")
        self.smart_card_reader_monitor = ReaderMonitor()
        self.smart_card_reader_observer = SmartCardReaderObserver(
            reader_added_callback=self.reader_removed_cb,
            reader_removed_callback=self.reader_removed_cb
        )
        self.smart_card_reader_monitor.addObserver(self.smart_card_reader_observer)

    def readerUnmonitor(self):
        try:
            if THAI_ID_CARD_DEBUG:
                print("ThaiIDCard: Remove SmartCard reader observer")
            self.smart_card_reader_monitor.deleteObserver(self.smart_card_reader_observer)
        except: pass

    def cardMonitor(self, smart_card_insert_cb, smart_card_remove_cb):
        self.smart_card_insert_cb = smart_card_insert_cb
        self.smart_card_remove_cb = smart_card_remove_cb
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: Add SmartCard observer")
        self.smart_card_monitor = CardMonitor()
        self.smart_card_observer = SmartCardObserver(
            card_insert_callback=self.smart_card_insert_cb,
            card_remove_callback=self.smart_card_remove_cb
        )
        self.smart_card_monitor.addObserver(self.smart_card_observer)

    def cardUnmonitor(self):
        try:
            if THAI_ID_CARD_DEBUG:
                print("ThaiIDCard: Remove SmartCard observer")
            self.smart_card_monitor.deleteObserver(self.smart_card_observer)
        except: pass

    # Get SmartCard reader list
    def getReaders(self):
        # Get all the available readers
        self.readerList = smartcard.System.readers()
        #if len(self.readerList) > 0:
        #    print ("Found SmartCard readers:")
        #    for readerIndex,readerItem in enumerate(self.readerList):
        #        print(" - %d, '%s'"%(readerIndex, readerItem))
        #else:
        #    print ("No SmartCard reader")
        self.readerIndex = 0
        return self.readerList

    # Connect to SmartCard reader
    def connect(self, index = 0):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: Connecting to SmartCard")
        if len(self.readerList)==0:
            if len(self.getReaders()) == 0:
                return None

        if index < 0 or index >= len(self.readerList):
            return None

        # Select reader
        self.readerIndex = index
        self.reader = self.readerList[self.readerIndex]
        if THAI_ID_CARD_DEBUG:
            print("Using SmartCard reader:", self.reader)

        try:
            self.connection = self.reader.createConnection()
            self.connection.connect()

            atr = self.connection.getATR()
            if THAI_ID_CARD_DEBUG:
                print (" - Card type: " + toHexString(atr))
            if (atr[0] == 0x3B & atr[1] == 0x67):
                # Corruption Card
                self._apdu = self.APDU_THAILAND_IDCARD_TYPE_01
            else:
                self._apdu = self.APDU_THAILAND_IDCARD_TYPE_02
            if THAI_ID_CARD_DEBUG:
                print(" - Connect to SmartCard success")
            self.status = True
            response, sw1, sw2 = self.selectApplet()
            # [], 61, 0A
            time.sleep(0.1)
            if sw1 == 0x61 and sw2 == 0x0A:
                return True
            self.status = None
            return None
        except:
            if THAI_ID_CARD_DEBUG:
                print(" - Failed to connect to SmartCard")
            self.status = None
            return None

    def disconnect(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: Closing connection from SmartCard")
        try:
            self.connection.disconnect()
        except: pass

    # Select MOI Applet
    def selectApplet(self):
        if self.status == None:
            if self.connect(self.readerIndex) == None:
                return [None, None, None]

        response, sw1, sw2 = self.connection.transmit(self.SELECT + self.AID_MOI)
        #print ("Select Applet: %02X %02X" % (sw1, sw2))
        return [response, sw1, sw2]

    # Read data from SmartCard
    def read(self, cmd, apdu = None):
        if self.status == None:
            if self.connect(self.readerIndex) == None:
                return [None, None, None]

        if apdu == None:
            apdu = self._apdu

        try:
            response, sw1, sw2 = self.connection.transmit(cmd)
            response, sw1, sw2 = self.connection.transmit(apdu + [cmd[-1]])
            return [response, sw1, sw2]
        except Exception as w:
            return [None, None, None]

    # Read photo from SmartCard
    def readPhoto(self):
        if self.status == None:
            if self.connect(self.readerIndex) == None:
                return None

        photo =  self.read(self.CMD_PHOTO01)[0]
        photo += self.read(self.CMD_PHOTO02)[0]
        photo += self.read(self.CMD_PHOTO03)[0]
        photo += self.read(self.CMD_PHOTO04)[0]
        photo += self.read(self.CMD_PHOTO05)[0]
        photo += self.read(self.CMD_PHOTO06)[0]
        photo += self.read(self.CMD_PHOTO07)[0]
        photo += self.read(self.CMD_PHOTO08)[0]
        photo += self.read(self.CMD_PHOTO09)[0]
        photo += self.read(self.CMD_PHOTO10)[0]
        photo += self.read(self.CMD_PHOTO11)[0]
        photo += self.read(self.CMD_PHOTO12)[0]
        photo += self.read(self.CMD_PHOTO13)[0]
        photo += self.read(self.CMD_PHOTO14)[0]
        photo += self.read(self.CMD_PHOTO15)[0]
        photo += self.read(self.CMD_PHOTO16)[0]
        photo += self.read(self.CMD_PHOTO17)[0]
        photo += self.read(self.CMD_PHOTO18)[0]
        photo += self.read(self.CMD_PHOTO19)[0]
        photo += self.read(self.CMD_PHOTO20)[0]
        response = HexListToBinString(photo)
        return response

    def thai2unicode(self, data):
        result = ''
        result = bytes(data).decode('tis-620')
        return result.strip();

    # Citizen ID
    @property
    def citizen(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: citizen=", end=' ')
        if(self._citizen!=None):
            if((time.time()-self._citizen_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._citizen)
                return self._citizen
        response, sw1, sw2 = self.read(self.CMD_CITIZEN)
        if(response != None):
            self._citizen = self.thai2unicode(response)
            self._citizen_t = time.time()
        else:
            self._citizen = None
        if THAI_ID_CARD_DEBUG:
            print(self._citizen)
        return self._citizen

    # Thai Name
    @property
    def full_name_th(self):
        #if THAI_ID_CARD_DEBUG:
        #    print("ThaiIDCard: full_name_th")
        if(self._full_name_th!=None):
            if((time.time()-self._full_name_th_t) < self._read_expire_time):
                return self._full_name_th
        response, sw1, sw2 = self.read(self.CMD_THFULLNAME)
        if(response != None):
            self._full_name_th = self.thai2unicode(response)
            self._full_name_th_t = time.time()
            self._first_name_th, self._last_name_th = self._full_name_th.split('##')
            self._prefix_th, self._first_name_th = self._first_name_th.split('#')
        else:
            self._full_name_th = None
        return self._full_name_th

    @property
    def prefix_th(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: prefix_th=", end=' ')
        if(self._full_name_th!=None):
            if((time.time()-self._full_name_th_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._prefix_th)
                return self._prefix_th
        if(self.full_name_th != None):
            if THAI_ID_CARD_DEBUG:
                print(self._prefix_th)
            return self._prefix_th
        return None

    @property
    def first_name_th(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: first_name_th=", end=' ')
        if(self._full_name_th!=None):
            if((time.time()-self._full_name_th_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._first_name_th)
                return self._first_name_th
        if(self.full_name_th != None):
            if THAI_ID_CARD_DEBUG:
                print(self._first_name_th)
            return self._first_name_th
        return None

    @property
    def last_name_th(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: last_name_th=", end=' ')
        if(self._full_name_th!=None):
            if((time.time()-self._full_name_th_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._last_name_th)
                return self._last_name_th
        if(self.full_name_th != None):
            if THAI_ID_CARD_DEBUG:
                print(self._last_name_th)
            return self._last_name_th
        return None

    # English Name
    @property
    def full_name_en(self):
        #if THAI_ID_CARD_DEBUG:
        #    print("ThaiIDCard: full_name_en")
        if(self._full_name_en!=None):
            if((time.time()-self._full_name_en_t) < self._read_expire_time):
                return self._full_name_en
        response, sw1, sw2 = self.read(self.CMD_ENFULLNAME)
        if(response != None):
            self._full_name_en = self.thai2unicode(response)
            self._full_name_en_t = time.time()
            self._first_name_en, self._last_name_en = self._full_name_en.split('##')
            self._prefix_en, self._first_name_en = self._first_name_en.split('#')
        else:
            self._full_name_en = None
        return self._full_name_en

    @property
    def prefix_en(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: prefix_en=", end=' ')
        if(self._full_name_en!=None):
            if((time.time()-self._full_name_en_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._prefix_en)
                return self._prefix_en
        if(self.full_name_en != None):
            if THAI_ID_CARD_DEBUG:
                print(self._prefix_en)
            return self._prefix_en
        return None

    @property
    def first_name_en(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: first_name_en=", end=' ')
        if(self._full_name_en!=None):
            if((time.time()-self._full_name_en_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._first_name_en)
                return self._first_name_en
        if(self.full_name_en != None):
            if THAI_ID_CARD_DEBUG:
                print(self._first_name_en)
            return self._first_name_en
        return None

    @property
    def last_name_en(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: last_name_en=", end=' ')
        if(self._full_name_en!=None):
            if((time.time()-self._full_name_en_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._last_name_en)
                return self._last_name_en
        if(self.full_name_en != None):
            if THAI_ID_CARD_DEBUG:
                print(self._last_name_en)
            return self._last_name_en
        return None

    # Date of birth
    @property
    def birth(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: birth=", end=' ')
        if(self._birth!=None):
            if((time.time()-self._birth_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._birth)
                return self._birth
        response, sw1, sw2 = self.read(self.CMD_BIRTH)
        if(response != None):
            self._birth = self.thai2unicode(response)
            self._birth_t = time.time()
            self._birth = self._birth[0:4]+'-'+self._birth[4:6]+'-'+self._birth[6:8]
        else:
            self._birth = None
        if THAI_ID_CARD_DEBUG:
            print(self._birth)
        return self._birth

    # Gender
    @property
    def gender(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: gender=", end=' ')
        if(self._gender!=None):
            if((time.time()-self._gender_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._gender)
                return self._gender
        response, sw1, sw2 = self.read(self.CMD_GENDER)
        if(response != None):
            self._gender = self.thai2unicode(response)
            self._gender_t = time.time()
        else:
            self._gender = None
        if THAI_ID_CARD_DEBUG:
            print(self._gender)
        return self._gender

    # Issue date
    @property
    def issue(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: issue=", end=' ')
        if(self._issue!=None):
            if((time.time()-self._issue_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._issue)
                return self._issue
        response, sw1, sw2 = self.read(self.CMD_ISSUE)
        if(response != None):
            self._issue = self.thai2unicode(response)
            self._issue_t = time.time()
            self._issue = self._issue[0:4]+'-'+self._issue[4:6]+'-'+self._issue[6:8]
        else:
            self._issue = None
        if THAI_ID_CARD_DEBUG:
            print(self._issue)
        return self._issue

    # Expire date
    @property
    def expire(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: expire=", end=' ')
        if(self._expire!=None):
            if((time.time()-self._expire_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._expire)
                return self._expire
        response, sw1, sw2 = self.read(self.CMD_EXPIRE)
        if(response != None):
            self._expire = self.thai2unicode(response)
            self._expire_t = time.time()
            self._expire = self._expire[0:4]+'-'+self._expire[4:6]+'-'+self._expire[6:8]
        else:
            self._expire = None
        if THAI_ID_CARD_DEBUG:
            print(self._expire)
        return self._expire

    # Address
    @property
    def address(self):
        #if THAI_ID_CARD_DEBUG:
        #    print("ThaiIDCard: address")
        if(self._address!=None):
            if((time.time()-self._address_t) < self._read_expire_time):
                return self._address
        response, sw1, sw2 = self.read(self.CMD_ADDRESS)
        if(response != None):
            self._address = self.thai2unicode(response)
            self._address_t = time.time()
            #self._address = self._address[0:4]+'-'+self._address[4:6]+'-'+self._address[6:8]
            self._address = re.sub(r'#', ' ', self._address)
            self._address = re.sub(r'  ', ' ', self._address)
            self._address = re.sub(r'  ', ' ', self._address)
            x = self._address.rsplit()
            self._city = x[len(x)-2]
            self._province = x[len(x)-1]
        else:
            self._address = None
        return self._address

    @property
    def city(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: city=", end=' ')
        if(self._address!=None):
            if((time.time()-self._address_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._city)
                return self._city
        if(self.address != None):
            if THAI_ID_CARD_DEBUG:
                print(self._city)
            return self._city
        return None

    @property
    def province(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: province=", end=' ')
        if(self._address!=None):
            if((time.time()-self._address_t) < self._read_expire_time):
                if THAI_ID_CARD_DEBUG:
                    print(self._province)
                return self._province
        if(self.address != None):
            if THAI_ID_CARD_DEBUG:
                print(self._province)
            return self._province
        return None

    # Photo
    @property
    def photo(self):
        if THAI_ID_CARD_DEBUG:
            print("ThaiIDCard: photo")
        if(self._photo!=None):
            if((time.time()-self._photo_t) < self._read_expire_time):
                return self._photo
        self._photo = self.readPhoto()
        return self._photo

    # Example code, read all attributes
    def example(self):
        if(len(self.readerList) < 0):
            return None

        # Reader list
        print(self.getReaders())

        print(f'Citizen ID:', self.citizen)
        print(f'Thai Full Name: ' + self.full_name_th)
        print(f'Thai Prefix: ' + self.prefix_th)
        print(f'Thai First Name: ' + self.first_name_th)
        print(f'Thai Last Name: ' + self.last_name_th)
        print(f'English Full Name: ' + self.full_name_en)
        print(f'English Prefix: ' + self.prefix_en)
        print(f'English First Name: ' + self.first_name_en)
        print(f'English Last Name: ' + self.last_name_en)
        print(f'Date of birth: ' + self.birth)
        print(f'Gender: ' + self.gender)
        print(f'Issue date: ' + self.issue)
        print(f'Expire date: ' + self.expire)
        print(f'Address: ' + self.address)
        print(f'City: ' + self.city)
        print(f'Province: ' + self.province)
        #print(f'Photo file size: ' + self.photo)
        return


if __name__ == "__main__":
    tsc = ThaiIDCard()
    tsc.example()

    while True:
        time.sleep(2)
        if tsc.connect(tsc.readerIndex) != None:
            tsc.example()

    # Exit program
    sys.exit()