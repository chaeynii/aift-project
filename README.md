## AIFT 
- 8팀

## 역할분담
이채연 - 데이터 수집, DB 연결, 오류 수정, PPT 제작

송예진 - 데이터 수집, 파일 결합, 키움 API 연동, PPT 제작, 발표

## 참고교재
https://wikidocs.net/6235

## 브랜치 전략

  - GIT-FLOW 전략이란?
  
   (feature, develop, release, hotfix, master) : 5가지 브랜치 사용
   1. Main : 배포용( 그 누구도 삭제할 수 없고 유지됨)
   2. Hotfix : master배포 후 발생되는 문제점들을 모아 개선하는 브런치이면 개선이 완료되면 develop, release, master에 머지된다.
   3. Release : 개발 후 수정, 버그 테스트를 거치기 전까지를 뜻하고, 이를 통과하면 master로 머지한다
   4. Develop : 개발 브런치, feature의 기능들이 하나씩 더해지며, 관리 되고 배포하게 될 수준에 도달할 경우 release로 머지한다.
   5. Feature : 기능 단위 브런치
  
  기존의 git flow전략에서 3개의 브런치(main develop feature)만을 사용한 feature-branch사용
  
  # Feature-브랜치 전략
  
    1. Main branch : 배포 브랜치로, 직접적인 push 절대불가
    2. Develop branch : 개인들이 브랜치를 만들어서 브랜치로 merge시키고 합쳐서 release해야할 때 main으로 이동
    3. Feature branch : 한 기능을 만들 때마다 새 브랜치 만들것이고 이를 develop으로 merge시키고 삭제시킴
    
    위의 Feature 브랜치 전략을 사용함.


## 협업내용

### 1. 키움 로그인 연동
- 계좌개설, 32bit 가상환경 설정(~22.11.4)
### 2. 환경변수 오류
- 새로운 가상환경 만들어 해결(~22.11.7)
### 3. 일봉데이터 오류
- 모든 종목이 다운로드 됨(22.11.12)
- 조회횟수 제한
### 4. 일봉데이터 수집
- 오류해결(~22.11.20)
### 5. sqlite3 설치 오류
- 계속해서 설치 오류
- 해당 github 클론 파일에 sqlite3.dll 설치 후 실행 - 해결(~22.11.21)
### 6. Time_stamp.py 파일 수정
- Sqlite timestamp의 시간의 type차이 발생
- 문자열-> 시간 / 시간 -> 문자열 변환
- 실시간 구동을 위한 장 시작 시간과 종료시간과 관련된 코드
### 7. DB 연동 오류
- sqlite 서버 저장오류
### 8. DB 저장경로 수정 및 오류해결
- config.xml 저장경로 수정
- (kospi/kospi200/kodex_200/kodex_inverse/kodex_kospi) 5개 csv저장, DB 연결 및 저장 성공 (~22.11.23)
### 9. 모델작성
- A. 이동평균선, rsi, a/d선 지표로만 모델 작성
- 이격도라는 지표 추가 및 ADX 지표 추가
### 10. Grpc환경 설치오류
### 11. flaml패키지 설치
- 설치 오류발생
- 32비트 환경 새로 구축 후 시행, 해결(~22.)
### 12. config 관련 경로오류
- config파일의 경로 새로작성
### 13. 매수 및 매도 코드 구현

- def try_to_buy() : 매수
- def try_to_sell() : 매도
### 14. 서버연동 관련 오류
- 시행 시 아무런 오류 및 문구 없이 종료
### 15. 서버 띄운 후 해결됨
