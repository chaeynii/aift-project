#비 실시간 구현
#분봉 데이터

import pickle
from pykiwoom.kiwoom import *
import datetime
import time

import pandas as pd
from pykiwoom.kiwoom import *
from tqdm.auto import tqdm


'''
 몇가지 ETF 종목과 업종 
'''
#etf 몇가지 종목 데이터 수집
tr_dic = {
  'opt20005': {'001': 'kospi', '201': 'kospi200'},
  'opt10080': {'069500':'kodex_200', '114800':'kodex_inverse', '226490':'kodex_kospi'}
}
def make_argument_dic(tr_code, code, is_next=False):
  '''
    tr_code에 따라 적절한 arg_dic을 만들어서 반환한다.
  '''

  arg_dic = {'틱범위': "1", 'next':2 if is_next else 0}
  if tr_code == 'opt10080':
    arg_dic.update({'종목코드': code, 'output': "주식분봉차트조회", '수정주가구분': "1"})
  elif tr_code == 'opt20005':
    arg_dic.update({'업종코드': code, 'output': "업종분봉차트조회"})
  else:
    assert False, "Unknown tr_code"
  return arg_dic

def main_job(kiwoom, tr_code, code, name):
  dfs = []
  with tqdm(total=106) as pbar:
    df = kiwoom.block_request(tr_code,**make_argument_dic(tr_code, code, is_next=False))
    dfs.append(df)
    nCalls = 1
    pbar.set_description(f'{code}/{name}')
    pbar.update(1)

    while kiwoom.tr_remained:
      time.sleep(3.8)
      df = kiwoom.block_request(tr_code,**make_argument_dic(tr_code, code, is_next=False))
      dfs.append(df)
      nCalls += 1
      pbar.update(1)

  return pd.concat(dfs)

if __name__ == "__main__":
  kiwoom = Kiwoom()
  kiwoom.CommConnect(block=True)

  for tr_code, dic in tr_dic.items():
    for code, name in dic.items():
      df = main_job(kiwoom, tr_code, code, name)
      df.to_csv(f'data/{name}.csv', index=False)
      print(f'{name} saved.')

# 전종목 종목코드
kospi = kiwoom.GetCodeListByMarket('0')
kosdaq = kiwoom.GetCodeListByMarket('10')
codes = kospi + kosdaq

# 문자열로 오늘 날짜 얻기
now = datetime.datetime.now()
today = now.strftime("%Y%m%d")

# 전 종목의 일봉 데이터
for i, code in enumerate(codes):
    print(f"{i}/{len(codes)} {code}")
    df = kiwoom.block_request("opt10080",
                              종목코드=code,
                              기준일자=today,
                              수정주가구분=1,
                              output="주식분봉차트조회",
                              next=0)

    out_name = f"{code}.xlsx"
    df.to_excel(out_name)
    time.sleep(3.6)


class Kiwoom:
    def __init__(self,
                 login=False,
                 tr_dqueue=None,
                 real_dqueues=None,
                 tr_cond_dqueue=None,
                 real_cond_dqueue=None,
                 chejan_dqueue=None):
        # OCX instance
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")

        # queues
        self.tr_dqueue          = tr_dqueue          # tr data queue
        self.real_dqueues       = real_dqueues       # real data queue list
        self.tr_cond_dqueue     = tr_cond_dqueue
        self.real_cond_dqueue   = real_cond_dqueue
        self.chejan_dqueue      = chejan_dqueue

        self.connected          = False              # for login event
        self.received           = False              # for tr event
        self.tr_items           = None               # tr input/output items
        self.tr_data            = None               # tr output data
        self.tr_record          = None
        self.tr_remained        = False
        self.condition_loaded   = False

        self._set_signals_slots()

        self.tr_output = {}
        self.real_fid = {}

        if login:
            self.CommConnect()

    #-------------------------------------------------------------------------------------------------------------------
    # callback functions
    #-------------------------------------------------------------------------------------------------------------------
    def OnEventConnect(self, err_code):
        """Login Event
        Args:
            err_code (int): 0: login success
        """
        if err_code == 0:
            self.connected = True

    def OnReceiveConditionVer(self, ret, msg):
        if ret == 1:
            self.condition_loaded = True

    def OnReceiveRealCondition(self, code, id_type, cond_name, cond_index):
        """이벤트 함수로 편입, 이탈 종목이 실시간으로 들어오는 callback 함수
        Args:
            code (str): 종목코드
            id_type (str): 편입('I'), 이탈('D')
            cond_name (str): 조건명
            cond_index (str): 조건명 인덱스
        """
        output = {
            'code': code,
            'type': id_type,
            'cond_name': cond_name,
            'cond_index': cond_index
        }
        self.real_cond_dqueue.put(output)

    def OnReceiveTrCondition(self, screen_no, code_list, cond_name, cond_index, next):
        """일반조회 TR에 대한 callback 함수
        Args:
            screen_no (str): 종목코드
            code_list (str): 종목리스트(";"로 구분)
            cond_name (str): 조건명
            cond_index (int): 조건명 인덱스
            next (int): 연속조회(0: 연속조회 없음, 2: 연속조회)
        """
        # legacy interface
        codes = code_list.split(';')[:-1]
        self.tr_condition_data = codes
        self.tr_condition_loaded= True

        # queue
        if self.tr_cond_dqueue is not None:
            output = {
                'screen_no': screen_no,
                'code_list': codes,
                'cond_name': cond_name,
                'cond_index': cond_index,
                'next': next
            }
            self.tr_cond_dqueue.put(output)

    def get_data(self, trcode, rqname, items):
        rows = self.GetRepeatCnt(trcode, rqname)
        if rows == 0:
            rows = 1

        data_list = []
        for row in range(rows):
            row_data = []
            for item in items:
                data = self.GetCommData(trcode, rqname, row, item)
                row_data.append(data)
            data_list.append(row_data)

        # data to DataFrame
        df = pd.DataFrame(data=data_list, columns=items)
        return df

    def OnReceiveTrData(self, screen, rqname, trcode, record, next):
        #print(screen, rqname, trcode, record, next)
        # order
        # - KOA_NORMAL_BUY_KP_ORD  : 코스피 매수
        # - KOA_NORMAL_SELL_KP_ORD : 코스피 매도
        # - KOA_NORMAL_KP_CANCEL   : 코스피 주문 취소
        # - KOA_NORMAL_KP_MODIFY   : 코스피 주문 변경
        # - KOA_NORMAL_BUY_KQ_ORD  : 코스피 매수
        # - KOA_NORMAL_SELL_KQ_ORD : 코스피 매도
        # - KOA_NORMAL_KQ_CANCEL   : 코스피 주문 취소
        # - KOA_NORMAL_KQ_MODIFY   : 코스피 주문 변경
        if self.tr_dqueue is not None:
            if trcode in ('KOA_NORMAL_BUY_KP_ORD', 'KOA_NORMAL_SELL_KP_ORD',
                'KOA_NORMAL_KP_CANCEL', 'KOA_NORMAL_KP_MODIFY',
                'KOA_NORMAL_BUY_KQ_ORD', 'KOA_NORMAL_SELL_KQ_ORD',
                'KOA_NORMAL_KQ_CANCEL', 'KOA_NORMAL_KQ_MODIFY'):
                return None
            items = self.tr_output[trcode]
            data = self.get_data(trcode, rqname, items)

            remain = 1 if next == '2' else 0
            self.tr_dqueue.put((data, remain))
        else:
            print(self.tr_items)
            try:
                record = None
                items = None

                # remained data
                if next == '2':
                    self.tr_remained = True
                else:
                    self.tr_remained = False

                for output in self.tr_items['output']:
                    record = list(output.keys())[0]
                    items = list(output.values())[0]
                    if record == self.tr_record:
                        break

                rows = self.GetRepeatCnt(trcode, rqname)
                if rows == 0:
                    rows = 1

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

            except:
                pass

    def OnReceiveMsg(self, screen, rqname, trcode, msg):
        pass

    def OnReceiveChejanData(self, gubun, item_cnt, fid_list):
        """주문접수, 체결, 잔고 변경시 이벤트가 발생
        Args:
            gubun (str): '0': 접수, 체결, '1': 잔고 변경
            item_cnt (int): 아이템 갯수
            fid_list (str): fid list
        """
        if self.chejan_dqueue is not None:
            output = {'gubun': gubun}
            for fid in fid_list.split(';'):
                data = self.GetChejanData(fid)
                output[fid]=data

            self.chejan_dqueue.put(output)

    def OnReceiveRealData(self, code, rtype, data):
        """실시간 데이터를 받는 시점에 콜백되는 메소드입니다.
        Args:
            code (str): 종목코드
            rtype (str): 리얼타입 (주식시세, 주식체결, ...)
            data (str): 실시간 데이터 전문
        """
        # get real data
        real_data = {"code": code}
        for fid in self.real_fid[code]:
            val = self.GetCommRealData(code, fid)
            real_data[fid] = val

        # put real data to the queue
        self.real_dqueues.put(real_data)

    def _set_signals_slots(self):
        self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)
        self.ocx.OnReceiveRealData.connect(self.OnReceiveRealData)
        self.ocx.OnReceiveMsg.connect(self.OnReceiveMsg)
        self.ocx.OnReceiveChejanData.connect(self.OnReceiveChejanData)
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.ocx.OnReceiveRealCondition.connect(self.OnReceiveRealCondition)
        self.ocx.OnReceiveTrCondition.connect(self.OnReceiveTrCondition)
        self.ocx.OnReceiveConditionVer.connect(self.OnReceiveConditionVer)

    #-------------------------------------------------------------------------------------------------------------------
    # OpenAPI+ 메서드
    #-------------------------------------------------------------------------------------------------------------------
    def CommConnect(self, block=True):
        """
        로그인 윈도우를 실행합니다.
        :param block: True: 로그인완료까지 블록킹 됨, False: 블록킹 하지 않음
        :return: None
        """
        self.ocx.dynamicCall("CommConnect()")
        if block:
            while not self.connected:
                pythoncom.PumpWaitingMessages()

    def CommRqData(self, rqname, trcode, next, screen):
        """
        TR을 서버로 송신합니다.
        :param rqname: 사용자가 임의로 지정할 수 있는 요청 이름
        :param trcode: 요청하는 TR의 코드
        :param next: 0: 처음 조회, 2: 연속 조회
        :param screen: 화면번호 ('0000' 또는 '0' 제외한 숫자값으로 200개로 한정된 값
        :return: None
        """
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen)

    def GetLoginInfo(self, tag):
        """
        로그인한 사용자 정보를 반환하는 메서드
        :param tag: ("ACCOUNT_CNT, "ACCNO", "USER_ID", "USER_NAME", "KEY_BSECGB", "FIREW_SECGB")
        :return: tag에 대한 데이터 값
        """
        data = self.ocx.dynamicCall("GetLoginInfo(QString)", tag)

        if tag == "ACCNO":
            return data.split(';')[:-1]
        else:
            return data

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

    def SetInputValue(self, id, value):
        """
        TR 입력값을 설정하는 메서드
        :param id: TR INPUT의 아이템명
        :param value: 입력 값
        :return: None
        """
        self.ocx.dynamicCall("SetInputValue(QString, QString)", id, value)

    def DisconnectRealData(self, screen):
        """
        화면번호에 대한 리얼 데이터 요청을 해제하는 메서드
        :param screen: 화면번호
        :return: None
        """
        self.ocx.dynamicCall("DisconnectRealData(QString)", screen)

    def GetRepeatCnt(self, trcode, rqname):
        """
        멀티데이터의 행(row)의 개수를 얻는 메서드
        :param trcode: TR코드
        :param rqname: 사용자가 설정한 요청이름
        :return: 멀티데이터의 행의 개수
        """
        count = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return count

    def CommKwRqData(self, arr_code, next, code_count, type, rqname, screen):
        """
        여러 종목 (한 번에 100종목)에 대한 TR을 서버로 송신하는 메서드
        :param arr_code: 여러 종목코드 예: '000020:000040'
        :param next: 0: 처음조회
        :param code_count: 종목코드의 개수
        :param type: 0: 주식종목 3: 선물종목
        :param rqname: 사용자가 설정하는 요청이름
        :param screen: 화면번호
        :return:
        """
        ret = self.ocx.dynamicCall("CommKwRqData(QString, bool, int, int, QString, QString)", arr_code, next, code_count, type, rqname, screen);
        return ret

    def GetAPIModulePath(self):
        """
        OpenAPI 모듈의 경로를 반환하는 메서드
        :return: 모듈의 경로
        """
        ret = self.ocx.dynamicCall("GetAPIModulePath()")
        return ret

    def GetCodeListByMarket(self, market):
        """
        시장별 상장된 종목코드를 반환하는 메서드
        :param market: 0: 코스피, 3: ELW, 4: 뮤추얼펀드 5: 신주인수권 6: 리츠
                       8: ETF, 9: 하이일드펀드, 10: 코스닥, 30: K-OTC, 50: 코넥스(KONEX)
        :return: 종목코드 리스트 예: ["000020", "000040", ...]
        """
        data = self.ocx.dynamicCall("GetCodeListByMarket(QString)", market)
        tokens = data.split(';')[:-1]
        return tokens

    def GetConnectState(self):
        """
        현재접속 상태를 반환하는 메서드
        :return: 0:미연결, 1: 연결완료
        """
        ret = self.ocx.dynamicCall("GetConnectState()")
        return ret

    def GetMasterCodeName(self, code):
        """
        종목코드에 대한 종목명을 얻는 메서드
        :param code: 종목코드
        :return: 종목명
        """
        data = self.ocx.dynamicCall("GetMasterCodeName(QString)", code)
        return data

    def GetMasterListedStockCnt(self, code):
        """
        종목에 대한 상장주식수를 리턴하는 메서드
        :param code: 종목코드
        :return: 상장주식수
        """
        data = self.ocx.dynamicCall("GetMasterListedStockCnt(QString)", code)
        return data

    def GetMasterConstruction(self, code):
        """
        종목코드에 대한 감리구분을 리턴
        :param code: 종목코드
        :return: 감리구분 (정상, 투자주의 투자경고, 투자위험, 투자주의환기종목)
        """
        data = self.ocx.dynamicCall("GetMasterConstruction(QString)", code)
        return data

    def GetMasterListedStockDate(self, code):
        """
        종목코드에 대한 상장일을 반환
        :param code: 종목코드
        :return: 상장일 예: "20100504"
        """
        data = self.ocx.dynamicCall("GetMasterListedStockDate(QString)", code)
        return datetime.datetime.strptime(data, "%Y%m%d")

    def GetMasterLastPrice(self, code):
        """
        종목코드의 전일가를 반환하는 메서드
        :param code: 종목코드
        :return: 전일가
        """
        data = self.ocx.dynamicCall("GetMasterLastPrice(QString)", code)
        return int(data)

    def GetMasterStockState(self, code):
        """
        종목의 종목상태를 반환하는 메서드
        :param code: 종목코드
        :return: 종목상태
        """
        data = self.ocx.dynamicCall("GetMasterStockState(QString)", code)
        return data.split("|")

    def GetDataCount(self, record):
        count = self.ocx.dynamicCall("GetDataCount(QString)", record)
        return count

    def GetOutputValue(self, record, repeat_index, item_index):
        count = self.ocx.dynamicCall("GetOutputValue(QString, int, int)", record, repeat_index, item_index)
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

    def GetCommRealData(self, code, fid):
        data = self.ocx.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return data

    def GetChejanData(self, fid):
        data = self.ocx.dynamicCall("GetChejanData(int)", fid)
        return data

    def GetThemeGroupList(self, type=1):
        data = self.ocx.dynamicCall("GetThemeGroupList(int)", type)
        tokens = data.split(';')
        if type == 0:
            grp = {x.split('|')[0]:x.split('|')[1] for x in tokens}
        else:
            grp = {x.split('|')[1]: x.split('|')[0] for x in tokens}
        return grp

    def GetThemeGroupCode(self, theme_code):
        data = self.ocx.dynamicCall("GetThemeGroupCode(QString)", theme_code)
        data = data.split(';')
        return [x[1:] for x in data]

    def GetFutureList(self):
        data = self.ocx.dynamicCall("GetFutureList()")
        return data

    def block_request(self, *args, **kwargs):
        trcode = args[0].lower()
        lines = parser.read_enc(trcode)
        self.tr_items = parser.parse_dat(trcode, lines)
        self.tr_record = kwargs["output"]
        next = kwargs["next"]

        # set input
        for id in kwargs:
            if id.lower() != "output" and id.lower() != "next":
                self.SetInputValue(id, kwargs[id])

        # initialize
        self.received = False
        self.tr_remained = False

        # request
        self.CommRqData(trcode, trcode, next, "0101")
        while not self.received:
            pythoncom.PumpWaitingMessages()

        return self.tr_data

    def SetRealReg(self, screen, code_list, fid_list, opt_type):
        ret = self.ocx.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen, code_list, fid_list, opt_type)
        return ret

    def SetRealRemove(self, screen, del_code):
        ret = self.ocx.dynamicCall("SetRealRemove(QString, QString)", screen, del_code)
        return ret

    def GetConditionLoad(self, block=True):
        self.condition_loaded = False

        self.ocx.dynamicCall("GetConditionLoad()")
        if block:
            while not self.condition_loaded:
                pythoncom.PumpWaitingMessages()

    def GetConditionNameList(self):
        data = self.ocx.dynamicCall("GetConditionNameList()")
        conditions = data.split(";")[:-1]

        # [('000', 'perpbr'), ('001', 'macd'), ...]
        result = []
        for condition in conditions:
            cond_index, cond_name = condition.split('^')
            result.append((cond_index, cond_name))

        return result

    def SendCondition(self, screen, cond_name, cond_index, search, block=True):
        """조건검색 종목조회 TR을 송신
        Args:
            screen (str): 화면번호
            cond_name (str): 조건명
            cond_index (int): 조건명 인덱스
            search (int): 0: 일반조회, 1: 실시간조회, 2: 연속조회
            block (bool): True: blocking request, False: Non-blocking request
        Returns:
            None: _description_
        """
        if block is True:
            self.tr_condition_loaded = False

        self.ocx.dynamicCall("SendCondition(QString, QString, int, int)", screen, cond_name, cond_index, search)

        if block is True:
            while not self.tr_condition_loaded:
                pythoncom.PumpWaitingMessages()

        if block is True:
            return self.tr_condition_data


    def SendConditionStop(self, screen, cond_name, index):
        self.ocx.dynamicCall("SendConditionStop(QString, QString, int)", screen, cond_name, index)

    def GetCommDataEx(self, trcode, rqname):
        data = self.ocx.dynamicCall("GetCommDataEx(QString, QString)", trcode, rqname)
        return data

if not QApplication.instance():
    app = QApplication(sys.argv)

if __name__ == "__main__":
    pass
    ## 로그인
    #kiwoom = Kiwoom()
    #kiwoom.CommConnect(block=True)

    ## 조건식 load
    #kiwoom.GetConditionLoad()

    #conditions = kiwoom.GetConditionNameList()

    ## 0번 조건식에 해당하는 종목 리스트 출력
    #condition_index = conditions[0][0]
    #condition_name = conditions[0][1]
    #codes = kiwoom.SendCondition("0101", condition_name, condition_index, 0)

    #print(codes)

#-------------일봉 데이터 머지(merge)-----------
import pandas as pd
import os

flist = os.listdir()
xlsx_list = [x for x in flist if x.endswith('.xlsx')]
close_data = []

for xls in xlsx_list:
    code = xls.split('.')[0]
    df = pd.read_excel(xls)
    df2 = df[['일자', '현재가']].copy()
    df2.rename(columns={'현재가': code}, inplace=True)
    df2 = df2.set_index('일자')
    df2 = df2[::-1]
    close_data.append(df2)

# concat
df = pd.concat(close_data, axis=1)
df.to_excel("merge.xlsx")

#---------------모멘텀 전략 종목선정 ------------
import pandas as pd

df = pd.read_excel("merge.xlsx")
df['일자'] = pd.to_datetime(df['일자'], format="%Y%m%d")
df = df.set_index('일자')

#60 영업일 수익률
return_df = df.pct_change(60)
return_df.tail() #출력

# 데이터 프레임으로 만들기
s = return_df.loc["2020-06-22"]
momentum_df = pd.DataFrame(s)
momentum_df.columns = ["모멘텀"]

momentum_df.head(n=10) #출력

#순위 저장
momentum_df['순위'] = momentum_df['모멘텀'].rank(ascending=False)
momentum_df.head(n=10)
#정렬
momentum_df = momentum_df.sort_values(by='순위')
momentum_df[:30] #상위 30개 출력
#30종목만 저장
momentum_df[:30].to_excel("momentum_list.xlsx")

#-----------종목 매수----------
import pandas as pd
from pykiwoom.kiwoom import *
import time

df = pd.read_excel("momentum_list.xlsx")
df.columns = ["종목코드", "모멘텀", "순위"]

# 종목명 추가하기
kiwoom = Kiwoom()
kiwoom.CommConnect(block=True)
codes = df["종목코드"]
names = [kiwoom.GetMasterCodeName(code) for code in codes]
df['종목명'] = pd.Series(data=names)


# 매수하기
accounts = kiwoom.GetLoginInfo('ACCNO')
account = accounts[0]

for code in codes:
    ret = kiwoom.SendOrder("시장가매수", "0101", account, 1, code, 100, 0, "03", "")
    time.sleep(0.2)
    print(code, "종목 시장가 주문 완료")