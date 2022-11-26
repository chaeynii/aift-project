import sys
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import time
import pandas as pd
import pymysql
import manage_db
import MySQLdb



form_class=uic.loadUiType("main_window.ui")[0]



class tradesystem(QMainWindow,form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)##GUI켜기
        self.setWindowTitle("주식 프로그램")##프로그램화면이름설정

        self.kiwoom=QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")##OpenAPI시작
        self.kiwoom.dynamicCall("CommConnect()")##로그인요청
        
        #데이터 요청구간
        #self.pushButton.clicked.connect(self.request_opt10016)
        self.pushButton.clicked.connect(self.request_opt10080)

        #이벤트 처리구간
        self.kiwoom.OnReceiveTrData.connect(self.receive_trdata)#데이터 조회 요청 처리함수
    #데이터 수신 구간
    def receive_trdata(self,ScrNo,RqName,TrCode,RecordName,PreNext):
        print(f"RQNAME:{RqName},TRCODE:{TrCode},RECORDNAME:{RecordName},PRENEXT:{PreNext}")
        if PreNext=="2":
            self.remained_data=True
        elif PreNext !="2":
            self.remained_data=False

        if RqName=="신고저가요청":
            self.OPT10016(TrCode,RecordName)
        if RqName=="분봉차트조회요청":
            self.opt10080(TrCode,RecordName)

        self.event_loop.exit()

    def OPT10016(self,TrCode,RecordName):
        data_len=self.__getrepeatcnt(TrCode,RecordName)
        for index in range(data_len):
            item_code=self.__getcommdata(TrCode,RecordName,index,"종목코드").strip("")
            item_name=self.__getcommdata(TrCode,RecordName,index,"종목명").strip("")
            now=self.__getcommdata(TrCode,RecordName,index,"현재가").strip("")

            print(f"[{item_code}]:{item_name}.현재가:{now}")
    #데이터 처리 구간
    def opt10080(self,TrCode,RecordName):
        data_len=self.__getrepeatcnt(TrCode,RecordName)

        for index in range(data_len):
            #item_code=self.GetCommData(TrCode,RecordName,0,"종목초드").strip()
            #close=self.GetCommData(TrCode,RecordName,index,"현재가").strip()
            #volume=int(self.GetCommData(TrCode,RecordName,index,"거래량").strip().replace("-",""))
            time=self.__getcommdata(TrCode,RecordName,index,"체결시간").strip("")
            now=self.__getcommdata(TrCode,RecordName,index,"현재가").strip("")
            open=self.__getcommdata(TrCode,RecordName,index,"시가").strip("")
            high=self.__getcommdata(TrCode,RecordName,index,"고가").strip("")
            low=self.__getcommdata(TrCode,RecordName,index,"저가").strip("")
            yclose=self.__getcommdata(TrCode,RecordName,index,"전일종가").strip("")
            print(f"[{time}] NOW:{now},OPEN:{open}, HIGH:{high}, LOW:{low}, YCLOSE:{yclose}")

            self.chart_data['time'].append(time)
            self.chart_data['now'].append(now)
            self.chart_data['open'].append(open)
            self.chart_data['high'].append(high)
            self.chart_data['low'].append(low)
    
    #opt10080 : 분봉차트조회요청
    def request_opt10080(self):
        self.chart_data={'time':[],'now':[],'open':[],'high':[],'low':[]}
        self.__setinputvalue("종목코드","069500")
        self.__setinputvalue("틱범위","3")
        self.__setinputvalue("수정주가구분","1")
        self.__commrqdata("분봉차트조회요청","opt10080",0,"0600")#069500
        self.event_loop=QEventLoop()
        self.event_loop.exec_()
        time.sleep(0.5)

        while self.remained_data==True:
            self.__setinputvalue("종목코드","069500")
            self.__setinputvalue("틱범위","3")
            self.__setinputvalue("수정주가구분","1")
            self.__commrqdata("분봉차트조회요청","opt10080",2,"0600")
            self.event_loop=QEventLoop()
            self.event_loop.exec_()
            time.sleep(0.5)

        chart_data=pd.DataFrame(self.chart_data,columns=['time','now','open','high','low'])
        print(chart_data)
        chart_data.to_sql(name="s069500",con=manage_db.engine_3min,index=False, if_exists='replace')
        print("차트데이터 저장이 완료되었습니다.")

    def request_opt10016(self):
        self.__setinputvalue("시장구분","000")
        self.__setinputvalue("신고저구분","1")
        self.__setinputvalue("고저종구분","1")
        self.__setinputvalue("종목조건","0")
        self.__setinputvalue("거개량구분","000000")
        self.__setinputvalue("신용조건","0")
        self.__setinputvalue("상하한포함","1")
        self.__setinputvalue("기간","60")
        self.__setinputvalue("신고저가요청","OPT10016",0,"0161")

    #데이터 입력구간
    def __setinputvalue(self,item,value):
        self.kiwoom.dynamicCall("SetInputValue(QString,QString)",[item,value])
    #데이터 요청구간
    def __commrqdata(self,rqname,trcode,pre,scrno):
        self.kiwoom.dynamicCall("CommRqData(QString,QString,int,QString)",[rqname,trcode,pre,scrno])
    #데이터 수신구간
    def __getcommdata(self,trcode,recordname,index,itemname):
        return self.kiwoom.dynamicCall("GetCommData(QString,QString,int,QSting)",[trcode,recordname,index,itemname])
    #데이터 개수반환
    def __getrepeatcnt(self,trcode,recordname):
        return self.kiwoom.dynamicCall("GetRepeatCnt(QStrinf,QString)",[trcode,recordname])

if __name__=="__main__":
    app=QApplication(sys.argv)
    myWindow=tradesystem()
    myWindow.show()
    app.exec_()
