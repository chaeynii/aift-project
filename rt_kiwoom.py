import re
import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import datetime
import parser
import pandas as pd
from collections import defaultdict
from log_class import *
from kiwoom_errors import KiwoomErrors

class RealtimeRequestItem:
  dummy_code='dummy_code'
  def __init__(self, screen_no, code_list, fid_list, opt_type):
      self.screen_no = screen_no      
      self.code_list = code_list
      self.fid_list = fid_list
      self.opt_type = opt_type

  def build(self):
      return {
          "screen_no": self.screen_no,
          "code_list": ";".join(self.code_list),
          "fid_list": ";".join(self.fid_list),
          "opt_type": self.opt_type
      }
  
  def update_code_fids(self, real_code_fid_dict):
    #예외: "장시작시간"
    # - 빈 리스트를 입력받기 때문에 dummy_code를 붙인다.
    code_list = [RealtimeRequestItem.dummy_code] if len(self.code_list) == 0 else self.code_list
    for code in code_list:
      if self.opt_type == "0":
        real_code_fid_dict[code] = self.fid_list
      else:
        real_code_fid_dict[code] = list(set(real_code_fid_dict[self.code]+self.fid_list))


class RTKiwoom:
  def __init__(self, outside_callback_dict = None):

    self.__log_instance=Logging()
    self.__rt_agent = {}
    self.kiwoom_errors = KiwoomErrors()
    self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
    
    self.__slots_dict = {
      "EventConnect": self.__slot_connect,
      "ReceiveTrData": self.__slot_receive_tr_data,
      "ReceiveRealData": self.__slot_receive_real_data,
      "ReceiveChejanData": self.__slot_receive_chejan_data,
    }

    self.outside_callback_dict = outside_callback_dict

    self.local_event_loop = QEventLoop()
    self.real_code_fid_dict = defaultdict(list)
    self.real_code_data = defaultdict(list)

    self.connected = False

    self.__set_signal_slots(self.__slots_dict)

  def set_rt_agent(self, agent):
    self.__rt_agent = agent
    
  def get_logger(self):
    return self.__log_instance.logger

  def __is_local_event_loop_running(self):
    '''
    로컬 이벤트 루프가 작동 중인지 확인
    '''
    if self.local_event_loop.isRunning():
      return True
    else:
      return False

  def __set_signal_slots(self, slots_dict):
    '''
    시그널과 슬롯을 연결
    slots_dict: {signal: slot, ...}
    '''
    for signal, slot in slots_dict.items():
      getattr(self.ocx, "On" + signal).connect(slot)

  def ComConnect(self, block=True):
    '''
    로그인
    '''
    self.ocx.dynamicCall("CommConnect()")
    if block:
      assert not self.__is_local_event_loop_running()
      self.local_event_loop.exec_()

  def SetInputValue(self, id, value):
    """
    TR 입력값을 설정하는 메서드
    :param id: TR INPUT의 아이템명
    :param value: 입력 값
    :return: None
    """
    self.ocx.dynamicCall("SetInputValue(QString, QString)", id, value)

  def GetRepeatCnt(self, trcode, rqname):
    """
    멀티데이터의 행(row)의 개수를 얻는 메서드
    :param trcode: TR코드
    :param rqname: 사용자가 설정한 요청이름
    :return: 멀티데이터의 행의 개수
    """
    count = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
    return count

  def GetCommData(self, trcode, rqname, index, item):
    """
    수순 데이터를 가져가는 메서드
    :param trcode: TR 코드
    :param rqname: 요청 이름
    :param index: 멀티데이터의 경우 row index
    :param item: 얻어오려는 항목 이름
    :return:
    """
    data = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, index, item)
    return data.strip()

  def __slot_connect(self, err_code):
    '''
    슬롯: 로그인 이벤트
    '''
    if err_code == 0:
      self.connected = True

    self.local_event_loop.exit()

  def GetLoginInfo(self, tag):
    '''
    로그인 정보 반환
    '''
    ret = self.ocx.dynamicCall("GetLoginInfo(QString)", tag)
    return ret

  def CommRqData(self, rqname, trcode, next, screen_no):
    '''
    서버에 데이터 요청 TR 요청 비동기
    '''
    self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen_no)
  
  def block_TR_request(self, trcode, **kwargs):
    '''
    TR 요청을 블록킹
    '''
    #module불러오기 오류여서 복붙
    import zipfile

    DIR_PATH = "C:/OpenAPI/data/"

    def read_enc(opt_fname):
        fpath = DIR_PATH + "{}.enc".format(opt_fname)
        enc = zipfile.ZipFile(fpath)
        dat_name = opt_fname.upper() + ".dat"
        lines = enc.read(dat_name).decode("cp949")
        return lines

    def parse_block(data):
        block_info = data[0]
        block_type = None
        if 'INPUT' in block_info:
            block_type = 'input'
        else:
            block_type = 'output'

        record_line = data[1]
        tokens = record_line.split('_')[1].strip()
        record = tokens.split("=")[0]

        fields = data[2:-1]
        field_name = []
        for line in fields:
            field = line.split("=")[0].strip()
            field_name.append(field)

        ret_data = {}
        ret_data[record] = field_name
        return block_type, ret_data


    def parse_dat(trcode, lines):
        lines = lines.split('\n')
        start_indices = [i for i, x in enumerate(lines) if x.startswith("@START")]
        end_indices = [i for i, x in enumerate(lines) if x.startswith("@END")]

        block_indices = zip(start_indices, end_indices)

        enc_data = {"trcode": trcode, "input": [], "output": []}

        for start, end in block_indices:
            block_data = lines[start-1:end+1]
            block_type, fields = parse_block(block_data)
            if block_type == "input":
                enc_data["input"].append(fields)
            else:
                enc_data["output"].append(fields)

        return enc_data
  #-------------여기까지
    self.tr_items = parse_dat(trcode, read_enc(trcode))
    self.tr_record = kwargs["output"]
    next = kwargs["next"]

    # set input
    assert len(self.tr_items['input']) == 1
    for key, ids in self.tr_items['input'][0].items():
      for id in ids:
        self.SetInputValue(id, kwargs[id])

    # initialize
    # TODO: 밖으로 빼기
    self.received = False
    self.tr_remained = False
    self.tr_has_no_single = True if "has_no_single" in kwargs and kwargs["has_no_single"] else False

    # request
    self.CommRqData(trcode, trcode, next, "0101")
    assert not self.__is_local_event_loop_running()
    self.local_event_loop.exec_()

    return self.tr_data

  def RegisterRealtimeRequest(self, rqItem: RealtimeRequestItem):
    '''
    실시간 데이터 요청 등록
    '''
    rqItem.update_code_fids(self.real_code_fid_dict)
    self.__set_real_reg(**rqItem.build())

  def __set_real_reg(self, screen_no, code_list, fid_list, opt_type):
    self.ocx.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_no, code_list, fid_list, opt_type)

  def __slot_receive_real_data(self, sCode, sRealType, sRealData):
    '''
    슬롯: 실시간 데이터 수신 이벤트
    '''
    real_data = {"code": sCode, "type": sRealType}
    if sRealType == '장시작시간':
      # sCode가 '09'로 입수. 하지만 요청시 지정하지 않았기 때문에
      # RealtimeRequestItem.dummy_code로 구분한다.
      if RealtimeRequestItem.dummy_code in self.real_code_fid_dict: 
        for fid in self.real_code_fid_dict[RealtimeRequestItem.dummy_code]:
          val = self.__get_com_real_data(sCode, fid)
          real_data[fid] = val
          self.real_code_data[sCode].append(real_data)
        self.__rt_agent.realtime_callbacks["장시작시간"].apply(real_data)
    elif sRealType == '주식체결':
      if sCode in self.real_code_fid_dict:
        for fid in self.real_code_fid_dict[sCode]:
          val = self.__get_com_real_data(sCode, fid)
          real_data[fid] = val
          self.real_code_data[sCode].append(real_data)
        self.__rt_agent.realtime_callbacks["주식체결"].apply(real_data)
    elif sRealType == '업종지수':
      if sCode in self.real_code_fid_dict:
        for fid in self.real_code_fid_dict[sCode]:
          val = self.__get_com_real_data(sCode, fid)
          real_data[fid] = val
          self.real_code_data[sCode].append(real_data)
        self.__rt_agent.realtime_callbacks["업종지수"].apply(real_data)
    else:
      return
    # self.get_logger().debug(real_data)

  def __get_com_real_data(self, sCode, fid):
    '''
    실시간 데이터 반환
    '''
    ret = self.ocx.dynamicCall("GetCommRealData(QString, int)", sCode, fid)
    return ret

  def __get_chejan_data(self, fid):
    ret = self.ocx.dynamicCall("GetChejanData(int)", fid)
    return ret

  def __determine_output_type(self, output_name):
    for i, output in enumerate(self.tr_items['output']):
      key = list(output.keys())[0]
      items = list(output.values())[0]
      if key == output_name:
        return i, items
    return -1, None

  def __slot_receive_chejan_data(self, gubun, item_cnt, fid_list):
    """
    슬롯: 체결잔고 데이터 수신 이벤트
    Args:
        gubun (str): '0': 접수, 체결, '1': 잔고 변경
        item_cnt (int): 아이템 갯수
        fid_list (str): fid list    
    """
    chejan_data = {'gubun': gubun}
    for fid in fid_list.split(';'):
      item = self.__get_chejan_data(fid)
      chejan_data[fid]=item

    if gubun == '0':
      self.__rt_agent.realtime_callbacks["체잔:주문체결"].apply(chejan_data)
    elif gubun == '1':
      self.__rt_agent.realtime_callbacks["체잔:잔고"].apply(chejan_data)

  def __slot_receive_tr_data(self, screen, rqname, trcode, record, next):
    '''
    슬롯: TR 데이터 수신 이벤트
    tr_items['output']
    '''
    record = None
    items = None

    # remained data
    if next == '2':
      self.tr_remained = True
    else:
      self.tr_remained = False

    # i == 0 일때는 싱글 데이터 요청에 대한 응답이다.
    i, items = self.__determine_output_type(self.tr_record)
    assert i != -1, 'invalid output name'
    is_single_data = True if i == 0 and not self.tr_has_no_single else False

    if is_single_data:
      rows = 1
    else:
      rows = self.GetRepeatCnt(trcode, rqname)

    data_list = []
    for row in range(rows):
      row_data = []
      for item in items:
        data = self.GetCommData(trcode, rqname, row, item)
        row_data.append(data)
      data_list.append(row_data)

    # data to DataFrame
    df = pd.DataFrame(data=data_list, columns=items)
    self.tr_data = df
    self.received = True

    # 블록킹 종료
    if self.local_event_loop.isRunning():
      self.local_event_loop.exit()

  def SendOrder(self, rqname, screen, accno, order_type, code, quantity, price, hoga, order_no):
    """
    주식 주문을 서버로 전송하는 메서드
    시장가 주문시 주문단가는 0으로 입력해야 함 (가격을 입력하지 않음을 의미)
    :param rqname: 사용자가 임의로 지정할 수 있는 요청 이름
    :param screen: 화면번호 ('0000' 또는 '0' 제외한 숫자값으로 200개로 한정된 값
    :param accno: 계좌번호 10자리
    :param order_type: 1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도정정
    :param code: 종목코드
    :param quantity: 주문수량
    :param price: 주문단가
    :param hoga: 00: 지정가, 03: 시장가,
                  05: 조건부지정가, 06: 최유리지정가, 07: 최우선지정가,
                  10: 지정가IOC, 13: 시장가IOC, 16: 최유리IOC,
                  20: 지정가FOK, 23: 시장가FOK, 26: 최유리FOK,
                  61: 장전시간외종가, 62: 시간외단일가, 81: 장후시간외종가
    :param order_no: 원주문번호로 신규 주문시 공백, 정정이나 취소 주문시에는 원주문번호를 입력
    :return:
    """
    ret = self.ocx.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                [rqname, screen, accno, order_type, code, quantity, price, hoga, order_no])
    return ret


# ---------------------------------------------
#config의 logclass 복붙
import logging.config
from datetime import datetime

class Logging():
    def __init__(self, config_path='config/logging.conf', log_path='log'):
        self.config_path = config_path
        self.log_path = log_path

        logging.config.fileConfig(self.config_path)
        self.__logger = logging.getLogger('Kiwoom')
        self.kiwoom_log()
    
    @property
    def logger(self):
        return self.__logger

    #로그설정
    def kiwoom_log(self):
        fh = logging.FileHandler(self.log_path+'/{:%Y-%m-%d}.log'.format(datetime.now()), encoding="utf-8")
        formatter = logging.Formatter('[%(asctime)s] I %(filename)s | %(name)s-%(funcName)s-%(lineno)04d I %(levelname)-8s > %(message)s')

        fh.setFormatter(formatter)
        self.__logger.addHandler(fh)


#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
#kiwoom errors 복붙
class KiwoomErrors:
  def __init__(self):
    self.errors = {
        0: "OP_ERR_NONE",
        -10: "OP_ERR_FAIL",
        -100: "OP_ERR_LOGIN",
        -101: "OP_ERR_CONNECT",
        -102: "OP_ERR_VERSION",
        -103: "OP_ERR_FIREWALL",
        -104: "OP_ERR_MEMORY",
        -105: "OP_ERR_INPUT",
        -106: "OP_ERR_SOCKET_CLOSED",
        -200: "OP_ERR_SISE_OVERFLOW",
        -201: "OP_ERR_RQ_STRUCT_FAIL",
        -202: "OP_ERR_RQ_STRING_FAIL",
        -203: "OP_ERR_NO_DATA",
        -204: "OP_ERR_OVER_MAX_DATA",
        -205: "OP_ERR_DATA_RCV_FAIL",
        -206: "OP_ERR_OVER_MAX_FID",
        -207: "OP_ERR_REAL_CANCEL",
        -300: "OP_ERR_ORD_WRONG_INPUT",
        -301: "OP_ERR_ORD_WRONG_ACCTNO",
        -302: "OP_ERR_OTHER_ACC_USE",
        -303: "OP_ERR_MIS_2BILL_EXC",
        -304: "OP_ERR_MIS_5BILL_EXC",
        -305: "OP_ERR_MIS_1PER_EXC",
        -306: "OP_ERR_MIS_3PER_EXC",
        -307: "OP_ERR_SEND_FAIL",
        -308: "OP_ERR_ORD_OVERFLOW",
        -309: "OP_ERR_MIS_300CNT_EXC",
        -310: "OP_ERR_MIS_500CNT_EXC",
        -340: "OP_ERR_ORD_WRONG_ACCTINFO",
        -500: "OP_ERR_ORD_SYMCODE_EMPTY",
    }

  def __getitem__(self, key):
    try:
        return self.errors[key]
    except KeyError:
        return "OP_ERR_UNKNOWN"